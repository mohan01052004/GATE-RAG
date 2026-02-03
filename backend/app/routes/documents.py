from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Document, DocumentTopic
from collections import defaultdict

router = APIRouter()


@router.get("/documents")
def list_documents(db: Session = Depends(get_db)):
    docs = db.query(Document).order_by(Document.uploaded_at.desc()).all()
    return {
        "documents": [
            {
                "id": d.id,
                "filename": d.filename,
                "subject": d.subject,
                "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None,
            }
            for d in docs
        ]
    }


@router.get("/documents/hierarchy")
def get_document_hierarchy(db: Session = Depends(get_db)):
    rows = db.query(DocumentTopic).all()
    hierarchy = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))

    for row in rows:
        subject = row.subject or "General"
        doc_label = f"{row.filename} (ID: {row.document_id})"
        topic = row.topic or row.section or "General"
        subtopic = row.subtopic or "General"
        hierarchy[subject][doc_label][topic].add(subtopic)

    result = []
    for subject, docs in hierarchy.items():
        doc_items = []
        for doc_label, topics in docs.items():
            topic_items = []
            for topic, subtopics in topics.items():
                topic_items.append({
                    "topic": topic,
                    "subtopics": sorted(subtopics)
                })
            doc_items.append({
                "document": doc_label,
                "topics": sorted(topic_items, key=lambda t: t["topic"])
            })
        result.append({
            "subject": subject,
            "documents": sorted(doc_items, key=lambda d: d["document"])
        })

    return {"hierarchy": sorted(result, key=lambda r: r["subject"])}
