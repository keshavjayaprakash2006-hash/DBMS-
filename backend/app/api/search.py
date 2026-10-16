import logging
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.database import get_db
from app.models.models import NoteChunk, Subject, Document
from app.schemas.schemas import SemanticSearchRequest, SemanticSearchResult
from app.services import embedding_service
from typing import List

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/search", tags=["Search"])


@router.post("/semantic", response_model=List[SemanticSearchResult])
def semantic_search(request: SemanticSearchRequest, db: Session = Depends(get_db)):
    """
    Perform cosine similarity search using pgvector.
    Embeds the query locally and finds nearest note chunks.
    """
    if not request.query.strip():
        raise HTTPException(status_code=422, detail="Query cannot be empty")

    # Generate embedding for the query
    try:
        query_embedding = embedding_service.generate_embedding(request.query)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=f"Embedding service unavailable: {e}")

    # Build parameterized query
    subject_filter = ""
    params = {
        "embedding": str(query_embedding),
        "top_k": request.top_k,
    }
    if request.subject_id:
        subject_filter = "AND nc.subject_id = :subject_id"
        params["subject_id"] = str(request.subject_id)

    query_sql = text(f"""
        SELECT
            nc.chunk_id,
            nc.content,
            nc.position,
            nc.word_count,
            nc.subject_id,
            nc.document_id,
            (1 - (nc.embedding <=> CAST(:embedding AS vector))) AS similarity,
            s.name AS subject_name,
            d.filename AS document_filename
        FROM note_chunks nc
        JOIN subjects s ON nc.subject_id = s.subject_id
        JOIN documents d ON nc.document_id = d.document_id
        WHERE nc.embedding IS NOT NULL
        {subject_filter}
        ORDER BY nc.embedding <=> CAST(:embedding AS vector)
        LIMIT :top_k
    """)

    try:
        rows = db.execute(query_sql, params).fetchall()
    except Exception as e:
        logger.error(f"Semantic search query failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="Semantic search requires pgvector. Ensure the extension is installed."
        )

    if not rows:
        return []

    return [
        SemanticSearchResult(
            chunk_id=row.chunk_id,
            content=row.content,
            similarity=round(float(row.similarity), 4),
            subject_name=row.subject_name,
            document_filename=row.document_filename,
            position=row.position,
            word_count=row.word_count,
        )
        for row in rows
    ]
