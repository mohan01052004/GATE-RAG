from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
import shutil
import os

from app.database import get_db
from app.models import Document, DocumentTopic
from app.services.pdf_loader import extract_text_from_pdf, extract_pages_from_pdf
from app.services.chunker import chunk_with_metadata, get_chunking_stats
from app.services.pinecone_service import upload_chunks

router = APIRouter()

@router.post("/upload")
async def upload_pdf(
    subject: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    path = f"temp_{file.filename}"

    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        pages = extract_pages_from_pdf(path)
        text = extract_text_from_pdf(path)
    finally:
        if os.path.exists(path):
            os.remove(path)
    if not text:
        raise HTTPException(status_code=400, detail="No text found in the uploaded document.")

    doc = Document(
        filename=file.filename,
        subject=subject
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Phase 4: Use semantic chunking with metadata extraction (page-aware)
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
    
    # Print chunking statistics
    plain_chunks = [chunk for chunk, meta in chunks_with_meta]
    stats = get_chunking_stats(plain_chunks)
    print(f"📝 Chunking stats for '{file.filename}': {stats}")
    
    try:
        # Prepare chunks with enriched metadata
        enriched_chunks = []
        topic_records = set()
        for chunk_text, chunk_meta in chunks_with_meta:
            section = chunk_meta.get("section") or chunk_meta.get("heading")
            topic = chunk_meta.get("topic")
            subtopic = chunk_meta.get("subtopic")
            page = chunk_meta.get("page")
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

    return {
        "message": "uploaded",
        "document_id": doc.id,
        "chunks_created": len(enriched_chunks),
        "chunking_stats": stats
    }
