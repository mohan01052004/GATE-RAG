from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import asyncio

from app.schemas import QueryRequest, MCQResponse, MCQAnswerRequest, MCQAnswerResponse
from app.database import get_db
from app.models import QueryLog
from app.services.rag_pipeline import (
    generate_theory_answer,
    generate_mcqs
)
from app.services.advanced_rag import advanced_retrieval, get_retrieval_stats

router = APIRouter()

@router.post("/ask")
def ask(req: QueryRequest, db: Session = Depends(get_db)):

    q = req.question.lower()

    try:
        if "mcq" in q:
            ans = generate_mcqs(
                req.question,
                subject=req.subject,
                document_id=req.document_id,
                document_ids=req.document_ids,
            )
        else:
            ans = generate_theory_answer(
                req.question,
                subject=req.subject,
                document_id=req.document_id,
                document_ids=req.document_ids,
            )
    except Exception as exc:
        error_msg = str(exc).lower()
        if "rate" in error_msg or "limit" in error_msg:
            return {"answer": "⚠️ API rate limit reached. Please wait a moment and try again."}
        raise HTTPException(status_code=500, detail=f"Query failed: {str(exc)}") from exc

    answer_for_log = ans if isinstance(ans, str) else str(ans)

    log = QueryLog(
        question=req.question,
        answer=answer_for_log
    )

    db.add(log)
    db.commit()

    return {"answer": ans}

@router.post("/mcq", response_model=MCQResponse)
def get_mcqs(req: QueryRequest, db: Session = Depends(get_db)):
    """Generate MCQs with structured format"""
    try:
        mcqs = generate_mcqs(
            req.question,
            subject=req.subject,
            document_id=req.document_id,
        )
        
        log = QueryLog(
            question=req.question,
            answer=str(mcqs)
        )
        db.add(log)
        db.commit()
        
        return mcqs
    except Exception as exc:
        error_msg = str(exc).lower()
        if "rate" in error_msg or "limit" in error_msg:
            raise HTTPException(status_code=429, detail="API rate limit reached. Please wait a moment and try again.")
        raise HTTPException(status_code=500, detail=f"MCQ generation failed: {str(exc)}") from exc

@router.post("/check-answer", response_model=MCQAnswerResponse)
def check_answer(req: MCQAnswerRequest):
    """Check if the selected answer is correct"""
    is_correct = req.selected_answer.upper() == req.correct_answer.upper()
    
    if is_correct:
        explanation = f"Correct! The answer is {req.correct_answer}."
    else:
        explanation = f"Wrong! You selected {req.selected_answer}, but the correct answer is {req.correct_answer}."
    
    return MCQAnswerResponse(
        is_correct=is_correct,
        correct_answer=req.correct_answer,
        explanation=explanation
    )


@router.post("/advanced-retrieve")
async def advanced_retrieve(req: QueryRequest, db: Session = Depends(get_db)):
    """
    Advanced RAG retrieval with Self-Query, HyDE, and RAG Fusion.
    
    Returns retrieved documents with detailed metadata and retrieval statistics.
    """
    try:
        results = await advanced_retrieval(
            query=req.question,
            document_ids=req.document_ids,
            top_k=10,
            use_self_query=req.use_self_query,
            use_hyde=req.use_hyde,
            use_fusion=req.use_fusion,
            deduplicate=True,
            promote_diversity=False
        )
        
        stats = get_retrieval_stats(results)
        
        # Log the query
        log = QueryLog(
            question=req.question,
            answer=f"[Advanced RAG] Retrieved {len(results)} results with {stats['unique_documents']} unique documents"
        )
        db.add(log)
        db.commit()
        
        return {
            "results": results,
            "stats": stats,
            "count": len(results)
        }
    except Exception as exc:
        error_msg = str(exc).lower()
        if "rate" in error_msg or "limit" in error_msg:
            raise HTTPException(status_code=429, detail="API rate limit reached. Please wait a moment and try again.")
        raise HTTPException(status_code=500, detail=f"Advanced retrieval failed: {str(exc)}") from exc

