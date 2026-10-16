import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, text

from app.db.database import get_db
from app.models.models import (
    Subject, Document, NoteChunk, PYQ, AnalysisRun, AnalysisStatus, ChunkScore
)
from app.schemas.schemas import DashboardStats

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    total_subjects = db.query(func.count(Subject.subject_id)).scalar() or 0
    total_documents = db.query(func.count(Document.document_id)).scalar() or 0
    total_chunks = db.query(func.count(NoteChunk.chunk_id)).scalar() or 0
    total_pyqs = db.query(func.count(PYQ.pyq_id)).scalar() or 0
    chunks_with_embeddings = db.query(func.count(NoteChunk.chunk_id)).filter(
        NoteChunk.embedding.isnot(None)
    ).scalar() or 0
    pyqs_with_embeddings = db.query(func.count(PYQ.pyq_id)).filter(
        PYQ.embedding.isnot(None)
    ).scalar() or 0

    # Subjects with at least one completed analysis
    analyzed_subjects = (
        db.query(func.count(func.distinct(AnalysisRun.subject_id)))
        .filter(AnalysisRun.status == AnalysisStatus.COMPLETED)
        .scalar() or 0
    )

    # Chunks that have at least one score (matched to PYQs)
    matched_chunks = db.query(func.count(func.distinct(ChunkScore.chunk_id))).scalar() or 0

    return DashboardStats(
        total_subjects=total_subjects,
        total_documents=total_documents,
        total_chunks=total_chunks,
        total_pyqs=total_pyqs,
        analyzed_subjects=analyzed_subjects,
        matched_chunks=matched_chunks,
        chunks_with_embeddings=chunks_with_embeddings,
        pyqs_with_embeddings=pyqs_with_embeddings,
    )


@router.get("/activity")
def get_activity(db: Session = Depends(get_db)):
    """Get recent activity across all entities."""
    activities = []

    # Recent documents
    recent_docs = (
        db.query(Document, Subject)
        .join(Subject, Document.subject_id == Subject.subject_id)
        .order_by(desc(Document.created_at))
        .limit(5)
        .all()
    )
    for doc, subj in recent_docs:
        activities.append({
            "type": "document_uploaded",
            "description": f"Uploaded '{doc.filename}' to {subj.name}",
            "timestamp": doc.created_at.isoformat(),
            "subject_name": subj.name,
            "status": doc.processing_status,
        })

    # Recent PYQs
    recent_pyqs = (
        db.query(PYQ, Subject)
        .join(Subject, PYQ.subject_id == Subject.subject_id)
        .order_by(desc(PYQ.created_at))
        .limit(5)
        .all()
    )
    for pyq, subj in recent_pyqs:
        activities.append({
            "type": "pyq_added",
            "description": f"Added PYQ ({pyq.exam_year}, {pyq.marks} marks) to {subj.name}",
            "timestamp": pyq.created_at.isoformat(),
            "subject_name": subj.name,
        })

    # Recent analyses
    recent_analyses = (
        db.query(AnalysisRun, Subject)
        .join(Subject, AnalysisRun.subject_id == Subject.subject_id)
        .filter(AnalysisRun.status == AnalysisStatus.COMPLETED)
        .order_by(desc(AnalysisRun.completed_at))
        .limit(3)
        .all()
    )
    for run, subj in recent_analyses:
        activities.append({
            "type": "analysis_completed",
            "description": f"Analysis completed for {subj.name}: {run.matched_chunks} chunks matched",
            "timestamp": run.completed_at.isoformat() if run.completed_at else run.created_at.isoformat(),
            "subject_name": subj.name,
        })

    # Sort by timestamp descending
    activities.sort(key=lambda x: x["timestamp"], reverse=True)
    return {"activities": activities[:15]}


@router.get("/subjects-overview")
def get_subjects_overview(db: Session = Depends(get_db)):
    """Summary per subject with stats."""
    subjects = db.query(Subject).all()
    result = []
    for s in subjects:
        doc_count = db.query(func.count(Document.document_id)).filter(
            Document.subject_id == s.subject_id
        ).scalar() or 0
        chunk_count = db.query(func.count(NoteChunk.chunk_id)).filter(
            NoteChunk.subject_id == s.subject_id
        ).scalar() or 0
        pyq_count = db.query(func.count(PYQ.pyq_id)).filter(
            PYQ.subject_id == s.subject_id
        ).scalar() or 0
        embedded_chunks = db.query(func.count(NoteChunk.chunk_id)).filter(
            NoteChunk.subject_id == s.subject_id,
            NoteChunk.embedding.isnot(None),
        ).scalar() or 0
        embedded_pyqs = db.query(func.count(PYQ.pyq_id)).filter(
            PYQ.subject_id == s.subject_id,
            PYQ.embedding.isnot(None),
        ).scalar() or 0
        latest_analysis = (
            db.query(AnalysisRun)
            .filter(
                AnalysisRun.subject_id == s.subject_id,
                AnalysisRun.status == AnalysisStatus.COMPLETED,
            )
            .order_by(desc(AnalysisRun.completed_at))
            .first()
        )

        result.append({
            "subject_id": str(s.subject_id),
            "name": s.name,
            "course_code": s.course_code,
            "doc_count": doc_count,
            "chunk_count": chunk_count,
            "pyq_count": pyq_count,
            "embedded_chunks": embedded_chunks,
            "embedded_pyqs": embedded_pyqs,
            "has_analysis": latest_analysis is not None,
            "latest_analysis_id": str(latest_analysis.analysis_id) if latest_analysis else None,
            "ready_for_analysis": embedded_chunks > 0 and embedded_pyqs > 0,
        })
    return {"subjects": result}


@router.get("/analytics")
def get_analytics(db: Session = Depends(get_db)):
    """Aggregated analytics for the analytics page."""
    # PYQ distribution by year
    year_dist = db.execute(
        text("SELECT exam_year, COUNT(*) as count FROM pyqs GROUP BY exam_year ORDER BY exam_year DESC")
    ).fetchall() if db.query(func.count(PYQ.pyq_id)).scalar() > 0 else []

    # PYQ distribution by subject
    subj_dist = (
        db.query(Subject.name, func.count(PYQ.pyq_id).label("count"))
        .join(PYQ, PYQ.subject_id == Subject.subject_id, isouter=True)
        .group_by(Subject.subject_id, Subject.name)
        .all()
    )

    # Marks distribution
    marks_dist = db.execute(
        text("SELECT marks, COUNT(*) as count FROM pyqs GROUP BY marks ORDER BY marks")
    ).fetchall() if db.query(func.count(PYQ.pyq_id)).scalar() > 0 else []

    # Top matched chunks
    top_chunks = (
        db.query(
            ChunkScore.chunk_id,
            ChunkScore.hit_count,
            ChunkScore.importance_score,
            NoteChunk.content,
            Document.filename,
            Subject.name,
        )
        .join(NoteChunk, ChunkScore.chunk_id == NoteChunk.chunk_id)
        .join(Document, NoteChunk.document_id == Document.document_id)
        .join(Subject, NoteChunk.subject_id == Subject.subject_id)
        .order_by(desc(ChunkScore.importance_score))
        .limit(10)
        .all()
    )

    return {
        "pyq_by_year": [{"year": r[0], "count": r[1]} for r in year_dist],
        "pyq_by_subject": [{"subject": r[0], "count": r[1]} for r in subj_dist],
        "marks_distribution": [{"marks": r[0], "count": r[1]} for r in marks_dist],
        "top_matched_chunks": [
            {
                "chunk_id": str(r[0]),
                "hit_count": r[1],
                "importance_score": r[2],
                "excerpt": r[3][:150] + "..." if len(r[3]) > 150 else r[3],
                "document": r[4],
                "subject": r[5],
            }
            for r in top_chunks
        ],
    }
