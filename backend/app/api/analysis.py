import logging
from uuid import UUID
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.database import get_db
from app.models.models import (
    AnalysisRun, AnalysisStatus, Subject, NoteChunk, PYQ, ChunkScore, Document
)
from app.schemas.schemas import AnalysisRunOut, ChunkScoreOut, HeatmapData, NoteChunkOut
from app.services import analysis_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Analysis"])


def _run_analysis_background(subject_id: str, db_url: str, analysis_id: Optional[str] = None):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        analysis_service.run_analysis(db, UUID(subject_id), UUID(analysis_id) if analysis_id else None)
    except Exception as e:
        logger.error(f"Analysis failed for subject {subject_id}: {e}")
    finally:
        db.close()


@router.post("/subjects/{subject_id}/analyze", response_model=AnalysisRunOut)
def trigger_analysis(
    subject_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    from app.core.config import settings

    subject = db.query(Subject).filter(Subject.subject_id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    # Check prerequisites
    chunk_count = db.query(NoteChunk).filter(
        NoteChunk.subject_id == subject_id,
        NoteChunk.embedding.isnot(None),
    ).count()
    pyq_count = db.query(PYQ).filter(
        PYQ.subject_id == subject_id,
        PYQ.embedding.isnot(None),
    ).count()

    if chunk_count == 0:
        raise HTTPException(
            status_code=422,
            detail="No note chunks with embeddings found for this subject. Upload and process documents first."
        )
    if pyq_count == 0:
        raise HTTPException(
            status_code=422,
            detail="No PYQs with embeddings found for this subject. Add PYQs first."
        )

    # Check for running analysis
    running = db.query(AnalysisRun).filter(
        AnalysisRun.subject_id == subject_id,
        AnalysisRun.status == AnalysisStatus.RUNNING,
    ).first()
    if running:
        raise HTTPException(status_code=409, detail="Analysis is already running for this subject")

    # Create pending analysis record
    analysis = AnalysisRun(
        subject_id=subject_id,
        status=AnalysisStatus.PENDING,
        configuration={
            "top_k": settings.TOP_K_MATCHES,
            "embedding_model": settings.EMBEDDING_MODEL_NAME,
        },
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    background_tasks.add_task(
        _run_analysis_background,
        str(subject_id),
        settings.DATABASE_URL,
        str(analysis.analysis_id),
    )

    return AnalysisRunOut(
        analysis_id=analysis.analysis_id,
        subject_id=analysis.subject_id,
        status=analysis.status,
        started_at=analysis.started_at,
        completed_at=analysis.completed_at,
        total_chunks=analysis.total_chunks,
        total_questions=analysis.total_questions,
        matched_chunks=analysis.matched_chunks,
        configuration=analysis.configuration,
        error_message=analysis.error_message,
        created_at=analysis.created_at,
        subject_name=subject.name,
    )


@router.get("/subjects/{subject_id}/analysis", response_model=List[AnalysisRunOut])
def get_subject_analysis_runs(subject_id: UUID, db: Session = Depends(get_db)):
    subject = db.query(Subject).filter(Subject.subject_id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    runs = (
        db.query(AnalysisRun)
        .filter(AnalysisRun.subject_id == subject_id)
        .order_by(AnalysisRun.created_at.desc())
        .limit(20)
        .all()
    )
    return [
        AnalysisRunOut(
            analysis_id=r.analysis_id,
            subject_id=r.subject_id,
            status=r.status,
            started_at=r.started_at,
            completed_at=r.completed_at,
            total_chunks=r.total_chunks,
            total_questions=r.total_questions,
            matched_chunks=r.matched_chunks,
            configuration=r.configuration,
            error_message=r.error_message,
            created_at=r.created_at,
            subject_name=subject.name,
        )
        for r in runs
    ]


@router.get("/analysis/{analysis_id}", response_model=AnalysisRunOut)
def get_analysis(analysis_id: UUID, db: Session = Depends(get_db)):
    analysis = db.query(AnalysisRun).filter(AnalysisRun.analysis_id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    subject = db.query(Subject).filter(Subject.subject_id == analysis.subject_id).first()
    return AnalysisRunOut(
        analysis_id=analysis.analysis_id,
        subject_id=analysis.subject_id,
        status=analysis.status,
        started_at=analysis.started_at,
        completed_at=analysis.completed_at,
        total_chunks=analysis.total_chunks,
        total_questions=analysis.total_questions,
        matched_chunks=analysis.matched_chunks,
        configuration=analysis.configuration,
        error_message=analysis.error_message,
        created_at=analysis.created_at,
        subject_name=subject.name if subject else None,
    )


@router.get("/analysis/{analysis_id}/heatmap")
def get_heatmap(analysis_id: UUID, db: Session = Depends(get_db)):
    analysis = db.query(AnalysisRun).filter(AnalysisRun.analysis_id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    if analysis.status != AnalysisStatus.COMPLETED:
        raise HTTPException(
            status_code=422,
            detail=f"Analysis is not completed (status: {analysis.status})"
        )

    subject = db.query(Subject).filter(Subject.subject_id == analysis.subject_id).first()

    # Get scored chunks
    scores = (
        db.query(ChunkScore, NoteChunk)
        .join(NoteChunk, ChunkScore.chunk_id == NoteChunk.chunk_id)
        .filter(ChunkScore.analysis_id == analysis_id)
        .order_by(ChunkScore.importance_score.desc())
        .all()
    )

    scored_chunk_ids = {str(s.ChunkScore.chunk_id) for s in scores}

    # Get unmatched chunks
    all_chunks_with_emb = db.query(NoteChunk).filter(
        NoteChunk.subject_id == analysis.subject_id,
        NoteChunk.embedding.isnot(None),
    ).all()
    unmatched = [c for c in all_chunks_with_emb if str(c.chunk_id) not in scored_chunk_ids]

    # Build scored chunks response
    scored_response = []
    for row in scores:
        cs = row.ChunkScore
        nc = row.NoteChunk
        doc = db.query(Document).filter(Document.document_id == nc.document_id).first()
        scored_response.append({
            "score_id": str(cs.score_id),
            "analysis_id": str(cs.analysis_id),
            "chunk_id": str(cs.chunk_id),
            "hit_count": cs.hit_count,
            "weighted_marks": cs.weighted_marks,
            "importance_score": cs.importance_score,
            "score_metadata": cs.score_metadata,
            "chunk_content": nc.content,
            "chunk_position": nc.position,
            "document_filename": doc.filename if doc else None,
            "matched_pyqs": (cs.score_metadata or {}).get("matched_pyqs", []),
        })

    # Build unmatched chunks response
    unmatched_response = []
    for nc in unmatched:
        doc = db.query(Document).filter(Document.document_id == nc.document_id).first()
        unmatched_response.append({
            "chunk_id": str(nc.chunk_id),
            "content": nc.content,
            "position": nc.position,
            "word_count": nc.word_count,
            "document_filename": doc.filename if doc else None,
            "importance_score": 0.0,
            "hit_count": 0,
        })

    return {
        "analysis": {
            "analysis_id": str(analysis.analysis_id),
            "subject_id": str(analysis.subject_id),
            "subject_name": subject.name if subject else None,
            "status": analysis.status,
            "total_chunks": analysis.total_chunks,
            "total_questions": analysis.total_questions,
            "matched_chunks": analysis.matched_chunks,
            "configuration": analysis.configuration,
            "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None,
        },
        "scored_chunks": scored_response,
        "unmatched_chunks": unmatched_response,
        "score_thresholds": {
            "high": 0.75,
            "medium": 0.40,
            "low": 0.01,
        },
    }


@router.get("/chunks/{chunk_id}/pyqs")
def get_chunk_pyqs(chunk_id: UUID, db: Session = Depends(get_db)):
    """Get PYQs that matched a specific chunk across all analysis runs."""
    chunk = db.query(NoteChunk).filter(NoteChunk.chunk_id == chunk_id).first()
    if not chunk:
        raise HTTPException(status_code=404, detail="Chunk not found")

    scores = (
        db.query(ChunkScore)
        .filter(ChunkScore.chunk_id == chunk_id)
        .order_by(ChunkScore.importance_score.desc())
        .all()
    )

    pyqs_data = []
    seen_pyq_ids = set()
    for score in scores:
        metadata = score.score_metadata or {}
        for pyq_info in metadata.get("matched_pyqs", []):
            pid = pyq_info.get("pyq_id")
            if pid and pid not in seen_pyq_ids:
                seen_pyq_ids.add(pid)
                pyqs_data.append(pyq_info)

    return {
        "chunk_id": str(chunk_id),
        "content": chunk.content,
        "matched_pyqs": pyqs_data,
    }
