from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import shutil
import os
import threading

from app.database import get_db, SessionLocal
from app.models import Document, DocumentTopic
from app.services.pdf_loader import extract_text_from_pdf, extract_pages_from_pdf
from app.services.chunker import chunk_with_metadata, get_chunking_stats
from app.services.advanced_pdf_parser import extract_structured_content
from app.services.semantic_chunker import hierarchical_chunk
from app.services.pinecone_service import upload_chunks
from app.services.table_extractor import extract_tables_from_pdf, tables_to_chunks
from app.services.image_extractor import (
    extract_images_from_pdf,
    caption_images_with_gemini,
    images_to_chunks,
)
from app.config import GEMINI_API_KEY, GEMINI_MODEL

router = APIRouter()

# Enable advanced parsing - set to True to use new semantic chunking with structure preservation
USE_ADVANCED_PARSING = True

# Enable multimodal extraction (images + tables)
EXTRACT_TABLES = True
EXTRACT_IMAGES = True

# Max images to caption per upload (keeps upload fast; set None for unlimited)
MAX_IMAGES_PER_UPLOAD = 30


def process_pdf_document_bg(
    pdf_bytes: bytes,
    document_id: int,
    subject: str,
    filename: str,
):
    """
    Background task to parse the PDF, extract tables, generate embeddings,
    upload to Pinecone, populate document topics, and extract images.
    Runs asynchronously after the HTTP response is returned.
    """
    import tempfile
    import os

    db = SessionLocal()
    tmp_path = None
    try:
        # Write bytes to a temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        print(f"[BG-PARSE] Starting document processing for '{filename}' (ID: {document_id})...")

        # 1. Text Parsing & Chunking
        if USE_ADVANCED_PARSING:
            print(f"[BG-PARSE] Using advanced PDF parsing for '{filename}'")
            sections = extract_structured_content(tmp_path)
            print(f"[BG-PARSE] Extracted {len(sections)} sections from PDF")
            
            # Find page count
            total_pages = max([s.page_number for s in sections]) if sections else 0
            print(f"[BG-PARSE] PDF has {total_pages} pages")

            chunks_with_meta = hierarchical_chunk(
                sections,
                max_chunk_size=800,
                min_chunk_size=200,
                overlap=100
            )
            print(f"[BG-PARSE] Created {len(chunks_with_meta)} semantic chunks")
        else:
            pages = extract_pages_from_pdf(tmp_path)
            text = extract_text_from_pdf(tmp_path)
            chunks_with_meta = []
            if pages:
                for page_num, page_text in pages:
                    if not page_text.strip():
                        continue
                    page_chunks = chunk_with_metadata(page_text)
                    for chunk_text, chunk_meta in page_chunks:
                        chunk_meta["page"] = page_num
                        chunks_with_meta.append((chunk_text, chunk_meta))
            else:
                chunks_with_meta = chunk_with_metadata(text)

        # 2. Table Extraction
        table_chunks = []
        if EXTRACT_TABLES:
            print(f"[BG-PARSE] Extracting tables from '{filename}'...")
            tables = extract_tables_from_pdf(tmp_path)
            table_chunks = tables_to_chunks(tables, subject=subject, filename=filename)
            print(f"[BG-PARSE] {len(table_chunks)} table chunks created")

        # Print chunking statistics
        plain_chunks = [chunk for chunk, meta in chunks_with_meta]
        stats = get_chunking_stats(plain_chunks)
        print(f"[BG-PARSE] Chunking stats for '{filename}': {stats}")

        # 3. Prepare text and table chunks with enriched metadata
        enriched_chunks = []
        topic_records = set()
        for chunk_text, chunk_meta in chunks_with_meta:
            section = chunk_meta.get("section") or chunk_meta.get("heading") or chunk_meta.get("title")
            topic = chunk_meta.get("topic")
            subtopic = chunk_meta.get("subtopic")
            page = chunk_meta.get("page") or chunk_meta.get("page_number")

            record_key = (
                document_id,
                subject,
                filename,
                section or "",
                topic or "",
                subtopic or "",
                page or 0
            )
            topic_records.add(record_key)

            enriched_chunks.append((chunk_text, {
                **chunk_meta,
                "document_id": document_id,
                "subject": subject,
                "filename": filename,
                "content_type": chunk_meta.get("content_type", "text"),
            }))

        for chunk_text, chunk_meta in table_chunks:
            enriched_chunks.append((chunk_text, {
                **chunk_meta,
                "document_id": document_id,
            }))

        # 4. Upload text/table chunks to Pinecone
        if enriched_chunks:
            print(f"[BG-PARSE] Uploading {len(enriched_chunks)} text/table chunks to Pinecone...")
            upload_chunks(enriched_chunks)
            print(f"[BG-PARSE] Main upload complete.")

        # 5. Populate DB topic records
        if topic_records:
            print(f"[BG-PARSE] Saving document topics to DB...")
            for record in topic_records:
                doc_id, subj, fname, sec, top, subtop, pg = record
                db.add(DocumentTopic(
                    document_id=doc_id,
                    subject=subj,
                    filename=fname,
                    section=sec or None,
                    topic=top or None,
                    subtopic=subtop or None,
                    page=pg or None,
                ))
            db.commit()
            print(f"[BG-PARSE] Saved topics to DB successfully.")

        # 6. Extract Images & Caption using Gemini (Multimodal)
        if EXTRACT_IMAGES and GEMINI_API_KEY:
            print(f"[BG-PARSE] Extracting and captioning images from '{filename}'...")
            raw_images = extract_images_from_pdf(tmp_path)
            if raw_images:
                if MAX_IMAGES_PER_UPLOAD and len(raw_images) > MAX_IMAGES_PER_UPLOAD:
                    print(f"[BG-PARSE] Capping images: {len(raw_images)} -> {MAX_IMAGES_PER_UPLOAD}")
                    raw_images = raw_images[:MAX_IMAGES_PER_UPLOAD]

                captioned = caption_images_with_gemini(
                    raw_images,
                    gemini_api_key=GEMINI_API_KEY,
                    gemini_model=GEMINI_MODEL,
                )
                image_chunks = images_to_chunks(captioned, subject=subject, filename=filename)
                if image_chunks:
                    enriched_images = [
                        (text, {**meta, "document_id": document_id})
                        for text, meta in image_chunks
                    ]
                    upload_chunks(enriched_images)
                    print(f"[BG-PARSE] Uploaded {len(enriched_images)} image chunks.")

        print(f"[BG-PARSE] Document '{filename}' (ID: {document_id}) fully indexed successfully!")

    except Exception as e:
        print(f"[BG-PARSE] Document processing failed: {e}")
        try:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                db.delete(doc)
                db.commit()
                print(f"[BG-PARSE] Cleaned up failed document record ID {document_id}")
        except Exception as db_err:
            print(f"[BG-PARSE] Failed to delete document record: {db_err}")
    finally:
        db.close()
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.post("/upload")
async def upload_pdf(
    background_tasks: BackgroundTasks,
    subject: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Read file bytes
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        # Create document record in database immediately
        doc = Document(filename=file.filename, subject=subject)
        db.add(doc)
        db.commit()
        db.refresh(doc)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database initialization failed: {str(exc)}")

    # Schedule complete processing in background
    background_tasks.add_task(
        process_pdf_document_bg,
        pdf_bytes=file_bytes,
        document_id=doc.id,
        subject=subject,
        filename=file.filename,
    )

    return {
        "message": "uploaded",
        "document_id": doc.id,
        "filename": file.filename,
        "status": "processing in background",
        "multimodal": {
            "tables_enabled": EXTRACT_TABLES,
            "images_enabled": EXTRACT_IMAGES,
        }
    }
