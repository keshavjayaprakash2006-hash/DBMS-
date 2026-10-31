import csv
import io
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.database import get_db
from app.models.models import PYQ, Subject
from app.schemas.schemas import PYQCreate, PYQUpdate, PYQOut, CSVImportResult
from app.services import embedding_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/pyqs", tags=["PYQs"])


def _embed_pyq_background(pyq_id: str, db_url: str):
    """Generate and store embedding for a single PYQ."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        from app.core.config import settings
        pyq = db.query(PYQ).filter(PYQ.pyq_id == UUID(pyq_id)).first()
        if pyq and pyq.embedding is None:
            emb = embedding_service.generate_embedding(pyq.question)
            pyq.embedding = emb
            pyq.embedding_model = embedding_service.get_model_name()
            db.commit()
    except Exception as e:
        logger.error(f"Failed to embed PYQ {pyq_id}: {e}")
    finally:
        db.close()


def _pyq_out(pyq: PYQ, db: Session) -> PYQOut:
    subject = db.query(Subject).filter(Subject.subject_id == pyq.subject_id).first()
    return PYQOut(
        pyq_id=pyq.pyq_id,
        subject_id=pyq.subject_id,
        exam_year=pyq.exam_year,
        marks=pyq.marks,
        question=pyq.question,
        semester=pyq.semester,
        course_code=pyq.course_code,
        unit_name=pyq.unit_name,
        question_number=pyq.question_number,
        source_document=pyq.source_document,
        has_embedding=pyq.embedding is not None,
        created_at=pyq.created_at,
        updated_at=pyq.updated_at,
        subject_name=subject.name if subject else None,
    )


@router.get("", response_model=List[PYQOut])
def list_pyqs(
    subject_id: Optional[UUID] = Query(None),
    exam_year: Optional[int] = Query(None),
    marks: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(PYQ)
    if subject_id:
        query = query.filter(PYQ.subject_id == subject_id)
    if exam_year:
        query = query.filter(PYQ.exam_year == exam_year)
    if marks:
        query = query.filter(PYQ.marks == marks)
    pyqs = query.order_by(PYQ.exam_year.desc(), PYQ.created_at.desc()).offset(skip).limit(limit).all()
    return [_pyq_out(p, db) for p in pyqs]


@router.post("", response_model=PYQOut, status_code=201)
def create_pyq(
    data: PYQCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    from app.core.config import settings
    subject = db.query(Subject).filter(Subject.subject_id == data.subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    pyq = PYQ(
        subject_id=data.subject_id,
        exam_year=data.exam_year,
        marks=data.marks,
        question=data.question,
        semester=data.semester,
        course_code=data.course_code,
        unit_name=data.unit_name,
        question_number=data.question_number,
        source_document=data.source_document,
    )
    db.add(pyq)
    db.commit()
    db.refresh(pyq)

    # Embed in background
    background_tasks.add_task(_embed_pyq_background, str(pyq.pyq_id), settings.normalized_database_url)
    return _pyq_out(pyq, db)


@router.get("/{pyq_id}", response_model=PYQOut)
def get_pyq(pyq_id: UUID, db: Session = Depends(get_db)):
    pyq = db.query(PYQ).filter(PYQ.pyq_id == pyq_id).first()
    if not pyq:
        raise HTTPException(status_code=404, detail="PYQ not found")
    return _pyq_out(pyq, db)


@router.patch("/{pyq_id}", response_model=PYQOut)
def update_pyq(
    pyq_id: UUID,
    data: PYQUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    from app.core.config import settings
    pyq = db.query(PYQ).filter(PYQ.pyq_id == pyq_id).first()
    if not pyq:
        raise HTTPException(status_code=404, detail="PYQ not found")

    question_changed = False
    for field, value in data.model_dump(exclude_unset=True).items():
        if field == "question" and value != pyq.question:
            question_changed = True
        setattr(pyq, field, value)

    if question_changed:
        pyq.embedding = None  # Mark for re-embedding

    db.commit()
    db.refresh(pyq)

    if question_changed:
        background_tasks.add_task(_embed_pyq_background, str(pyq.pyq_id), settings.normalized_database_url)

    return _pyq_out(pyq, db)


@router.delete("/{pyq_id}", status_code=204)
def delete_pyq(pyq_id: UUID, db: Session = Depends(get_db)):
    pyq = db.query(PYQ).filter(PYQ.pyq_id == pyq_id).first()
    if not pyq:
        raise HTTPException(status_code=404, detail="PYQ not found")
    db.delete(pyq)
    db.commit()


@router.post("/import-csv", response_model=CSVImportResult)
async def import_pyqs_from_csv(
    background_tasks: BackgroundTasks,
    subject_id: UUID = Query(..., description="Target subject ID"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    from app.core.config import settings

    subject = db.query(Subject).filter(Subject.subject_id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=422, detail="Only CSV files are accepted")

    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1", errors="replace")

    reader = csv.DictReader(io.StringIO(text))
    required_columns = {"question", "exam_year", "marks"}

    if not reader.fieldnames:
        raise HTTPException(status_code=422, detail="CSV file is empty or has no headers")

    actual_columns = {f.strip().lower() for f in reader.fieldnames}
    missing = required_columns - actual_columns
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"CSV missing required columns: {missing}. Required: question, exam_year, marks"
        )

    imported = 0
    failed = 0
    duplicate_skipped = 0
    errors = []
    pyq_ids_to_embed = []

    for row_num, row in enumerate(reader, start=2):
        # Normalize column names
        normalized_row = {k.strip().lower(): v.strip() for k, v in row.items() if k}
        try:
            question_text = normalized_row.get("question", "").strip()
            if not question_text or len(question_text) < 5:
                raise ValueError("Question text is empty or too short")

            exam_year = int(normalized_row.get("exam_year", 0))
            if exam_year < 1990 or exam_year > 2100:
                raise ValueError(f"Invalid exam_year: {exam_year}")

            marks = int(normalized_row.get("marks", 0))
            if marks < 1 or marks > 100:
                raise ValueError(f"Invalid marks: {marks}")

            # Check for duplicates within this subject
            existing = db.query(PYQ).filter(
                PYQ.subject_id == subject_id,
                PYQ.question == question_text,
                PYQ.exam_year == exam_year,
            ).first()
            if existing:
                duplicate_skipped += 1
                continue

            pyq = PYQ(
                subject_id=subject_id,
                exam_year=exam_year,
                marks=marks,
                question=question_text,
                semester=normalized_row.get("semester") or None,
                course_code=normalized_row.get("course_code") or None,
                unit_name=normalized_row.get("unit_name") or normalized_row.get("unit") or None,
                question_number=normalized_row.get("question_number") or normalized_row.get("q_no") or None,
                source_document=normalized_row.get("source_document") or None,
            )
            db.add(pyq)
            db.flush()
            pyq_ids_to_embed.append(str(pyq.pyq_id))
            imported += 1

        except (ValueError, TypeError) as e:
            failed += 1
            errors.append({"row": row_num, "error": str(e), "data": dict(row)})

    db.commit()

    # Embed in background
    for pyq_id in pyq_ids_to_embed:
        background_tasks.add_task(_embed_pyq_background, pyq_id, settings.normalized_database_url)

    return CSVImportResult(
        total_rows=imported + failed + duplicate_skipped,
        imported=imported,
        failed=failed,
        duplicate_skipped=duplicate_skipped,
        errors=errors,
    )
