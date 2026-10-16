import logging
from uuid import UUID
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.database import get_db
from app.models.models import ChatSession, ChatMessage, Subject, NoteChunk, PYQ
from app.schemas.schemas import ChatRequest, ChatResponse, ChatSessionOut, ChatMessageOut
from app.services import embedding_service, chat_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["Chat"])


def _retrieve_context(
    db: Session,
    query: str,
    subject_id: Optional[UUID],
    top_k: int = 5,
) -> tuple[List[dict], List[dict]]:
    """Retrieve relevant chunks and PYQs for the query."""
    try:
        query_embedding = embedding_service.generate_embedding(query)
    except RuntimeError:
        return [], []

    subject_filter = ""
    params = {"embedding": str(query_embedding), "top_k": top_k}
    if subject_id:
        subject_filter = "AND nc.subject_id = :subject_id"
        params["subject_id"] = str(subject_id)

    try:
        rows = db.execute(
            text(f"""
                SELECT nc.chunk_id, nc.content, nc.position,
                       d.filename AS document_filename,
                       (1 - (nc.embedding <=> CAST(:embedding AS vector))) AS similarity
                FROM note_chunks nc
                JOIN documents d ON nc.document_id = d.document_id
                WHERE nc.embedding IS NOT NULL {subject_filter}
                ORDER BY nc.embedding <=> CAST(:embedding AS vector)
                LIMIT :top_k
            """),
            params,
        ).fetchall()
        chunks = [
            {
                "chunk_id": str(row.chunk_id),
                "content": row.content,
                "document_filename": row.document_filename,
                "similarity": round(float(row.similarity), 4),
            }
            for row in rows
        ]
    except Exception:
        chunks = []

    # Also retrieve relevant PYQs
    pyq_filter = ""
    pyq_params = {"embedding": str(query_embedding), "top_k": 3}
    if subject_id:
        pyq_filter = "AND subject_id = :subject_id"
        pyq_params["subject_id"] = str(subject_id)

    try:
        pyq_rows = db.execute(
            text(f"""
                SELECT pyq_id, question, exam_year, marks
                FROM pyqs
                WHERE embedding IS NOT NULL {pyq_filter}
                ORDER BY embedding <=> CAST(:embedding AS vector)
                LIMIT :top_k
            """),
            pyq_params,
        ).fetchall()
        pyqs = [
            {
                "pyq_id": str(r.pyq_id),
                "question": r.question,
                "exam_year": r.exam_year,
                "marks": r.marks,
            }
            for r in pyq_rows
        ]
    except Exception:
        pyqs = []

    return chunks, pyqs


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    from app.core.config import settings

    # Get or create session
    session = None
    if request.session_id:
        session = db.query(ChatSession).filter(
            ChatSession.session_id == request.session_id
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
    else:
        # Create new session
        title = request.question[:80] + ("..." if len(request.question) > 80 else "")
        session = ChatSession(
            subject_id=request.subject_id,
            title=title,
        )
        db.add(session)
        db.flush()

    # Store user message
    user_msg = ChatMessage(
        session_id=session.session_id,
        role="user",
        content=request.question,
    )
    db.add(user_msg)
    db.flush()

    # Retrieve context
    chunks, pyqs = _retrieve_context(db, request.question, request.subject_id)

    # Generate response via Ollama
    answer, error = chat_service.generate_chat_response(request.question, chunks, pyqs)

    # Build sources
    sources = [
        {
            "type": "note_chunk",
            "chunk_id": c["chunk_id"],
            "document": c["document_filename"],
            "similarity": c["similarity"],
            "excerpt": c["content"][:200] + "..." if len(c["content"]) > 200 else c["content"],
        }
        for c in chunks
    ]

    final_answer = answer if answer else (
        f"⚠️ AI Assistant Unavailable\n\n{error}"
    )

    # Store assistant message
    assistant_msg = ChatMessage(
        session_id=session.session_id,
        role="assistant",
        content=final_answer,
        sources={"chunks": sources, "error": error},
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(session)

    return ChatResponse(
        answer=final_answer,
        session_id=session.session_id,
        sources=sources,
        model_used=settings.OLLAMA_MODEL if answer else None,
        error=error,
    )


@router.get("/sessions", response_model=List[ChatSessionOut])
def list_sessions(db: Session = Depends(get_db)):
    sessions = (
        db.query(ChatSession)
        .order_by(ChatSession.updated_at.desc())
        .limit(50)
        .all()
    )
    result = []
    for s in sessions:
        count = db.query(ChatMessage).filter(ChatMessage.session_id == s.session_id).count()
        result.append(ChatSessionOut(
            session_id=s.session_id,
            subject_id=s.subject_id,
            title=s.title,
            created_at=s.created_at,
            updated_at=s.updated_at,
            message_count=count,
        ))
    return result


@router.get("/sessions/{session_id}")
def get_session(session_id: UUID, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    return {
        "session": ChatSessionOut(
            session_id=session.session_id,
            subject_id=session.subject_id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=len(messages),
        ),
        "messages": [
            ChatMessageOut(
                message_id=m.message_id,
                session_id=m.session_id,
                role=m.role,
                content=m.content,
                sources=m.sources,
                created_at=m.created_at,
            )
            for m in messages
        ],
    }


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(session_id: UUID, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(session)
    db.commit()
