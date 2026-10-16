from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.database import get_db
from app.models.models import Subject, Document, NoteChunk, PYQ, AnalysisRun, AnalysisStatus
from app.schemas.schemas import SubjectCreate, SubjectUpdate, SubjectOut

router = APIRouter(prefix="/api/subjects", tags=["Subjects"])


def _subject_out(subject: Subject, db: Session) -> SubjectOut:
    doc_count = db.query(func.count(Document.document_id)).filter(
        Document.subject_id == subject.subject_id
    ).scalar() or 0
    pyq_count = db.query(func.count(PYQ.pyq_id)).filter(
        PYQ.subject_id == subject.subject_id
    ).scalar() or 0
    chunk_count = db.query(func.count(NoteChunk.chunk_id)).filter(
        NoteChunk.subject_id == subject.subject_id
    ).scalar() or 0
    return SubjectOut(
        subject_id=subject.subject_id,
        name=subject.name,
        description=subject.description,
        course_code=subject.course_code,
        created_at=subject.created_at,
        updated_at=subject.updated_at,
        document_count=doc_count,
        pyq_count=pyq_count,
        chunk_count=chunk_count,
    )


@router.get("", response_model=List[SubjectOut])
def list_subjects(db: Session = Depends(get_db)):
    subjects = db.query(Subject).order_by(Subject.created_at.desc()).all()
    return [_subject_out(s, db) for s in subjects]


@router.post("", response_model=SubjectOut, status_code=201)
def create_subject(data: SubjectCreate, db: Session = Depends(get_db)):
    subject = Subject(
        name=data.name,
        description=data.description,
        course_code=data.course_code,
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return _subject_out(subject, db)


@router.get("/{subject_id}", response_model=SubjectOut)
def get_subject(subject_id: UUID, db: Session = Depends(get_db)):
    subject = db.query(Subject).filter(Subject.subject_id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    return _subject_out(subject, db)


@router.patch("/{subject_id}", response_model=SubjectOut)
def update_subject(subject_id: UUID, data: SubjectUpdate, db: Session = Depends(get_db)):
    subject = db.query(Subject).filter(Subject.subject_id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    if data.name is not None:
        subject.name = data.name
    if data.description is not None:
        subject.description = data.description
    if data.course_code is not None:
        subject.course_code = data.course_code
    db.commit()
    db.refresh(subject)
    return _subject_out(subject, db)


@router.delete("/{subject_id}", status_code=204)
def delete_subject(subject_id: UUID, db: Session = Depends(get_db)):
    subject = db.query(Subject).filter(Subject.subject_id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    db.delete(subject)
    db.commit()
