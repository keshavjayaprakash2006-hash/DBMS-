"""
Analysis service: PYQ-to-notes matching and importance score calculation.
All results are persisted to the database for instant heatmap retrieval.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.models import (
    AnalysisRun, AnalysisStatus, ChunkScore, NoteChunk, PYQ
)
from app.core.config import settings

logger = logging.getLogger(__name__)


def run_analysis(db: Session, subject_id: UUID, analysis_id: Optional[UUID] = None) -> AnalysisRun:
    """
    Main analysis pipeline:
    1. Get all PYQs and note chunks for the subject (with embeddings).
    2. For each PYQ, find top-k most similar chunks using pgvector.
    3. Aggregate hit counts and weighted marks per chunk.
    4. Normalize scores and persist results.
    """
    if analysis_id:
        analysis = db.query(AnalysisRun).filter(AnalysisRun.analysis_id == analysis_id).first()
    else:
        analysis = None

    if analysis:
        analysis.status = AnalysisStatus.RUNNING
        analysis.started_at = datetime.now(timezone.utc)
        analysis.configuration = {
            "top_k": settings.TOP_K_MATCHES,
            "embedding_model": settings.EMBEDDING_MODEL_NAME,
            "embedding_dimension": settings.EMBEDDING_DIMENSION,
        }
    else:
        analysis = AnalysisRun(
            subject_id=subject_id,
            status=AnalysisStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            configuration={
                "top_k": settings.TOP_K_MATCHES,
                "embedding_model": settings.EMBEDDING_MODEL_NAME,
                "embedding_dimension": settings.EMBEDDING_DIMENSION,
            },
        )
        db.add(analysis)
    db.flush()

    try:
        # Count resources
        total_chunks = db.query(NoteChunk).filter(
            NoteChunk.subject_id == subject_id,
            NoteChunk.embedding.isnot(None),
        ).count()
        total_questions = db.query(PYQ).filter(
            PYQ.subject_id == subject_id,
            PYQ.embedding.isnot(None),
        ).count()

        analysis.total_chunks = total_chunks
        analysis.total_questions = total_questions

        if total_chunks == 0:
            raise ValueError("No note chunks with embeddings found. Upload and process notes first.")
        if total_questions == 0:
            raise ValueError("No PYQs with embeddings found. Add and embed PYQs first.")

        # Aggregate: chunk_id -> {hit_count, weighted_marks, matched_pyqs}
        chunk_aggregates = {}

        # Process each PYQ
        pyqs = db.query(PYQ).filter(
            PYQ.subject_id == subject_id,
            PYQ.embedding.isnot(None),
        ).all()

        for pyq in pyqs:
            # Use pgvector cosine distance for nearest chunks
            # cosine_distance = 1 - cosine_similarity
            results = db.execute(
                text("""
                    SELECT chunk_id, content,
                           (embedding <=> CAST(:embedding AS vector)) AS cosine_distance
                    FROM note_chunks
                    WHERE subject_id = :subject_id
                      AND embedding IS NOT NULL
                    ORDER BY embedding <=> CAST(:embedding AS vector)
                    LIMIT :top_k
                """),
                {
                    "embedding": str(pyq.embedding.tolist()) if hasattr(pyq.embedding, "tolist") else str(list(pyq.embedding)),
                    "subject_id": str(subject_id),
                    "top_k": settings.TOP_K_MATCHES,
                },
            ).fetchall()

            for rank, row in enumerate(results):
                chunk_id = str(row.chunk_id)
                cosine_distance = float(row.cosine_distance)

                if chunk_id not in chunk_aggregates:
                    chunk_aggregates[chunk_id] = {
                        "hit_count": 0,
                        "weighted_marks": 0.0,
                        "matched_pyqs": [],
                    }

                chunk_aggregates[chunk_id]["hit_count"] += 1
                chunk_aggregates[chunk_id]["weighted_marks"] += pyq.marks
                chunk_aggregates[chunk_id]["matched_pyqs"].append({
                    "pyq_id": str(pyq.pyq_id),
                    "question": pyq.question,
                    "exam_year": pyq.exam_year,
                    "marks": pyq.marks,
                    "rank": rank + 1,
                    "cosine_distance": round(cosine_distance, 4),
                    "similarity": round(1 - cosine_distance, 4),
                })

        # Normalize importance scores
        max_hit_count = max(
            (v["hit_count"] for v in chunk_aggregates.values()), default=1
        )
        if max_hit_count == 0:
            max_hit_count = 1

        # Store chunk scores
        matched_chunk_count = 0
        for chunk_id_str, agg in chunk_aggregates.items():
            importance_score = agg["hit_count"] / max_hit_count
            score = ChunkScore(
                analysis_id=analysis.analysis_id,
                chunk_id=UUID(chunk_id_str),
                hit_count=agg["hit_count"],
                weighted_marks=agg["weighted_marks"],
                importance_score=round(importance_score, 4),
                score_metadata={
                    "matched_pyqs": agg["matched_pyqs"],
                    "max_hit_count": max_hit_count,
                },
            )
            db.add(score)
            matched_chunk_count += 1

        analysis.matched_chunks = matched_chunk_count
        analysis.status = AnalysisStatus.COMPLETED
        analysis.completed_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(analysis)
        return analysis

    except Exception as e:
        db.rollback()
        # Re-fetch analysis in a new transaction to update status
        try:
            analysis_obj = db.query(AnalysisRun).filter(
                AnalysisRun.analysis_id == analysis.analysis_id
            ).first()
            if analysis_obj:
                analysis_obj.status = AnalysisStatus.FAILED
                analysis_obj.error_message = str(e)
                analysis_obj.completed_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            pass
        raise


def get_latest_analysis(db: Session, subject_id: UUID) -> Optional[AnalysisRun]:
    """Get the most recent completed analysis for a subject."""
    return (
        db.query(AnalysisRun)
        .filter(
            AnalysisRun.subject_id == subject_id,
            AnalysisRun.status == AnalysisStatus.COMPLETED,
        )
        .order_by(AnalysisRun.completed_at.desc())
        .first()
    )


def get_heatmap_data(db: Session, analysis_id: UUID) -> Tuple[List[dict], List[dict]]:
    """
    Retrieve heatmap data: chunk scores joined with chunk content.
    Returns (scored_chunks, unmatched_chunks).
    """
    analysis = db.query(AnalysisRun).filter(
        AnalysisRun.analysis_id == analysis_id
    ).first()
    if not analysis:
        return [], []

    # Get all scored chunks with content
    scores = (
        db.query(ChunkScore, NoteChunk)
        .join(NoteChunk, ChunkScore.chunk_id == NoteChunk.chunk_id)
        .filter(ChunkScore.analysis_id == analysis_id)
        .order_by(ChunkScore.importance_score.desc())
        .all()
    )

    # Get all chunks for the subject that have no score
    scored_chunk_ids = {str(s.ChunkScore.chunk_id) for s in scores}
    all_chunks = db.query(NoteChunk).filter(
        NoteChunk.subject_id == analysis.subject_id,
        NoteChunk.embedding.isnot(None),
    ).all()
    unmatched = [c for c in all_chunks if str(c.chunk_id) not in scored_chunk_ids]

    return scores, unmatched
