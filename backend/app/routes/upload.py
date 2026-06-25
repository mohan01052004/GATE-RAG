from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import shutil
import os
import threading

from app.database import get_db
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


def _caption_and_upload_images_bg(
    pdf_bytes: bytes,
    document_id: int,
    subject: str,
    filename: str,
):
    """
    Background task: saves PDF bytes to a temp file, extracts + captions images,
    and uploads image chunks to Pinecone. Runs after the HTTP response is sent.
    """
    import tempfile

    tmp_path = None
    try:
        # Write bytes to a temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        print(f"[BG] Starting image captioning for doc_id={document_id} ({filename})")
        raw_images = extract_images_from_pdf(tmp_path)

        if not raw_images:
            print(f"[BG] No images found in {filename}")
            return

        # Cap to MAX_IMAGES_PER_UPLOAD
        if MAX_IMAGES_PER_UPLOAD and len(raw_images) > MAX_IMAGES_PER_UPLOAD:
            print(f"[BG] Capping images: {len(raw_images)} -> {MAX_IMAGES_PER_UPLOAD}")
            raw_images = raw_images[:MAX_IMAGES_PER_UPLOAD]

        captioned = caption_images_with_gemini(
            raw_images,
            gemini_api_key=GEMINI_API_KEY,
            gemini_model=GEMINI_MODEL,
        )
        image_chunks = images_to_chunks(captioned, subject=subject, filename=filename)

        if image_chunks:
            enriched = [
                (text, {**meta, "document_id": document_id})
                for text, meta in image_chunks
            ]
            upload_chunks(enriched)
            print(f"[BG] Uploaded {len(enriched)} image chunks for doc_id={document_id}")
        else:
            print(f"[BG] No captionable images for doc_id={document_id}")

    except Exception as e:
        print(f"[BG] Image captioning failed for doc_id={document_id}: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.post("/upload")
async def upload_pdf(
    background_tasks: BackgroundTasks,
    subject: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    path = f"temp_{file.filename}"

    # Read file bytes once (needed for both text parsing and background image task)
    file_bytes = await file.read()
    with open(path, "wb") as f:
        f.write(file_bytes)

    try:
        if USE_ADVANCED_PARSING:
            print(f"[INFO] Using advanced PDF parsing for '{file.filename}'")
            sections = extract_structured_content(path)

            if not sections:
                raise HTTPException(status_code=400, detail="No content extracted from document.")

            print(f"[INFO] Extracted {len(sections)} sections from PDF")
            print(f"   - Pages: {max([s.page_number for s in sections]) if sections else 0}")
            print(f"   - Headings: {len([s for s in sections if s.section_type == 'heading'])}")
            print(f"   - Paragraphs: {len([s for s in sections if s.section_type == 'paragraph'])}")
            print(f"   - Lists: {len([s for s in sections if s.section_type == 'list'])}")

            # Create document record
            doc = Document(filename=file.filename, subject=subject)
            db.add(doc)
            db.commit()
            db.refresh(doc)

            # Hierarchical semantic chunking
            chunks_with_meta = hierarchical_chunk(
                sections,
                max_chunk_size=800,
                min_chunk_size=200,
                overlap=100
            )
            print(f"[INFO] Created {len(chunks_with_meta)} semantic chunks")

        else:
            pages = extract_pages_from_pdf(path)
            text = extract_text_from_pdf(path)

            if not text:
                raise HTTPException(status_code=400, detail="No text found in the uploaded document.")

            doc = Document(filename=file.filename, subject=subject)
            db.add(doc)
            db.commit()
            db.refresh(doc)

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

        # ── Tables (fast — no API calls, extract synchronously) ─────────────
        table_chunks: list = []
        if EXTRACT_TABLES:
            print(f"[INFO] Extracting tables from '{file.filename}'...")
            tables = extract_tables_from_pdf(path)
            table_chunks = tables_to_chunks(tables, subject=subject, filename=file.filename)
            print(f"[INFO] {len(table_chunks)} table chunks created")

    finally:
        if os.path.exists(path):
            os.remove(path)

    # Print chunking statistics
    plain_chunks = [chunk for chunk, meta in chunks_with_meta]
    stats = get_chunking_stats(plain_chunks)
    print(f"[INFO] Chunking stats for '{file.filename}': {stats}")

    try:
        # Prepare text chunks with enriched metadata
        enriched_chunks = []
        topic_records = set()
        for chunk_text, chunk_meta in chunks_with_meta:
            section = chunk_meta.get("section") or chunk_meta.get("heading") or chunk_meta.get("title")
            topic = chunk_meta.get("topic")
            subtopic = chunk_meta.get("subtopic")
            page = chunk_meta.get("page") or chunk_meta.get("page_number")

            record_key = (
                doc.id,
                subject,
                file.filename,
                section or "",
                topic or "",
                subtopic or "",
                page or 0
            )
            topic_records.add(record_key)

            enriched_chunks.append((chunk_text, {
                **chunk_meta,
                "document_id": doc.id,
                "subject": subject,
                "filename": file.filename,
                "content_type": chunk_meta.get("content_type", "text"),
            }))

        # Add table chunks
        for chunk_text, chunk_meta in table_chunks:
            enriched_chunks.append((chunk_text, {
                **chunk_meta,
                "document_id": doc.id,
            }))

        upload_chunks(enriched_chunks)

        if topic_records:
            for record in topic_records:
                doc_id, subj, filename, section, topic, subtopic, page = record
                db.add(DocumentTopic(
                    document_id=doc_id,
                    subject=subj,
                    filename=filename,
                    section=section or None,
                    topic=topic or None,
                    subtopic=subtopic or None,
                    page=page or None,
                ))
            db.commit()

    except Exception as exc:
        db.delete(doc)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(exc)}") from exc

    # ── Schedule image captioning as a background task ───────────────────────
    # This runs AFTER the HTTP response is sent — upload feels instant to the user
    if EXTRACT_IMAGES and GEMINI_API_KEY:
        background_tasks.add_task(
            _caption_and_upload_images_bg,
            pdf_bytes=file_bytes,
            document_id=doc.id,
            subject=subject,
            filename=file.filename,
        )
        images_status = f"queued (up to {MAX_IMAGES_PER_UPLOAD} images)"
    else:
        images_status = "skipped (no GEMINI_API_KEY)"

    return {
        "message": "uploaded",
        "document_id": doc.id,
        "chunks_created": len(enriched_chunks),
        "text_chunks": len(chunks_with_meta),
        "table_chunks": len(table_chunks),
        "image_chunks": "processing in background",
        "chunking_stats": stats,
        "parsing_mode": "advanced" if USE_ADVANCED_PARSING else "basic",
        "multimodal": {
            "tables_extracted": len(table_chunks),
            "images_status": images_status,
        }
    }
