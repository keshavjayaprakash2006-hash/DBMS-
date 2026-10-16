import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import Document, Subject, NoteChunk, ProcessingStatus
from app.schemas.schemas import DocumentOut, NoteChunkOut
from app.services import document_service
from app.services import embedding_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["Documents"])


def _process_document_background(document_id: str, db_url: str):
    """Background task to extract text, chunk, and generate embeddings."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.document_id == UUID(document_id)).first()
        if not doc:
            return
        doc.processing_status = ProcessingStatus.PROCESSING
        db.commit()

        # Extract text
        text, error = document_service.extract_text(doc.stored_path, doc.file_type)
        if error or not text.strip():
            doc.processing_status = ProcessingStatus.FAILED
            doc.processing_error = error or "No text could be extracted from the document."
            db.commit()
            return

        normalized = document_service.normalize_text(text)
        doc.extracted_text_length = len(normalized)

        # Delete existing chunks to avoid duplicates on reprocess
        db.query(NoteChunk).filter(NoteChunk.document_id == doc.document_id).delete()

        # Chunk the text
        chunks = document_service.chunk_text(normalized)
        if not chunks:
            doc.processing_status = ProcessingStatus.FAILED
            doc.processing_error = "Text was extracted but no valid chunks could be created."
            db.commit()
            return

        # Create chunk records
        chunk_objects = []
        for i, chunk_content in enumerate(chunks):
            chunk = NoteChunk(
                subject_id=doc.subject_id,
                document_id=doc.document_id,
                position=i,
                content=chunk_content,
                word_count=len(chunk_content.split()),
            )
            db.add(chunk)
            chunk_objects.append(chunk)
        db.flush()

        # Generate embeddings in batches
        try:
            from app.core.config import settings
            texts = [c.content for c in chunk_objects]
            embeddings = embedding_service.generate_embeddings_batch(texts)
            for chunk, emb in zip(chunk_objects, embeddings):
                chunk.embedding = emb
                chunk.embedding_model = settings.EMBEDDING_MODEL_NAME
            doc.embeddings_generated = True
        except Exception as emb_err:
            logger.warning(f"Embedding generation failed: {emb_err}")
            doc.embeddings_generated = False

        doc.chunk_count = len(chunk_objects)
        doc.processing_status = ProcessingStatus.COMPLETED
        db.commit()
        logger.info(f"Document {document_id} processed: {len(chunk_objects)} chunks")

    except Exception as e:
        logger.error(f"Processing failed for document {document_id}: {e}")
        try:
            doc = db.query(Document).filter(Document.document_id == UUID(document_id)).first()
            if doc:
                doc.processing_status = ProcessingStatus.FAILED
                doc.processing_error = str(e)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


@router.get("", response_model=List[DocumentOut])
def list_documents(
    subject_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Document)
    if subject_id:
        query = query.filter(Document.subject_id == subject_id)
    docs = query.order_by(Document.created_at.desc()).all()
    result = []
    for doc in docs:
        subject = db.query(Subject).filter(Subject.subject_id == doc.subject_id).first()
        out = DocumentOut(
            document_id=doc.document_id,
            subject_id=doc.subject_id,
            filename=doc.filename,
            file_type=doc.file_type,
            processing_status=doc.processing_status,
            processing_error=doc.processing_error,
            extracted_text_length=doc.extracted_text_length,
            chunk_count=doc.chunk_count,
            embeddings_generated=doc.embeddings_generated,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
            subject_name=subject.name if subject else None,
        )
        result.append(out)
    return result


@router.post("/upload", response_model=DocumentOut, status_code=201)
async def upload_document(
    background_tasks: BackgroundTasks,
    subject_id: UUID = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    from app.core.config import settings

    # Validate subject exists
    subject = db.query(Subject).filter(Subject.subject_id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    content = await file.read()
    file_size = len(content)

    # Validate file
    error = document_service.validate_file(file.filename or "", file_size)
    if error:
        raise HTTPException(status_code=422, detail=error)

    ext = document_service.get_file_extension(file.filename or "")
    stored_filename = document_service.generate_stored_filename(file.filename or "upload.txt")
    stored_path = document_service.save_uploaded_file(content, stored_filename)

    doc = Document(
        subject_id=subject_id,
        filename=file.filename,
        stored_path=stored_path,
        file_type=ext,
        processing_status=ProcessingStatus.PENDING,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Process in background
    background_tasks.add_task(
        _process_document_background,
        str(doc.document_id),
        settings.DATABASE_URL,
    )

    return DocumentOut(
        document_id=doc.document_id,
        subject_id=doc.subject_id,
        filename=doc.filename,
        file_type=doc.file_type,
        processing_status=doc.processing_status,
        processing_error=None,
        extracted_text_length=None,
        chunk_count=0,
        embeddings_generated=False,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        subject_name=subject.name,
    )


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: UUID, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    subject = db.query(Subject).filter(Subject.subject_id == doc.subject_id).first()
    return DocumentOut(
        document_id=doc.document_id,
        subject_id=doc.subject_id,
        filename=doc.filename,
        file_type=doc.file_type,
        processing_status=doc.processing_status,
        processing_error=doc.processing_error,
        extracted_text_length=doc.extracted_text_length,
        chunk_count=doc.chunk_count,
        embeddings_generated=doc.embeddings_generated,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        subject_name=subject.name if subject else None,
    )


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: UUID, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    import os
    try:
        if os.path.exists(doc.stored_path):
            os.remove(doc.stored_path)
    except Exception as e:
        logger.warning(f"Could not delete file {doc.stored_path}: {e}")
    db.delete(doc)
    db.commit()


@router.post("/{document_id}/reprocess", response_model=DocumentOut)
def reprocess_document(
    document_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    from app.core.config import settings
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    doc.processing_status = ProcessingStatus.PENDING
    doc.processing_error = None
    db.commit()

    background_tasks.add_task(
        _process_document_background,
        str(doc.document_id),
        settings.DATABASE_URL,
    )
    db.refresh(doc)
    subject = db.query(Subject).filter(Subject.subject_id == doc.subject_id).first()
    return DocumentOut(
        document_id=doc.document_id,
        subject_id=doc.subject_id,
        filename=doc.filename,
        file_type=doc.file_type,
        processing_status=doc.processing_status,
        processing_error=doc.processing_error,
        extracted_text_length=doc.extracted_text_length,
        chunk_count=doc.chunk_count,
        embeddings_generated=doc.embeddings_generated,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        subject_name=subject.name if subject else None,
    )


@router.get("/{document_id}/chunks", response_model=List[NoteChunkOut])
def get_document_chunks(document_id: UUID, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    chunks = (
        db.query(NoteChunk)
        .filter(NoteChunk.document_id == document_id)
        .order_by(NoteChunk.position)
        .all()
    )
    return [
        NoteChunkOut(
            chunk_id=c.chunk_id,
            subject_id=c.subject_id,
            document_id=c.document_id,
            position=c.position,
            content=c.content,
            word_count=c.word_count,
            has_embedding=c.embedding is not None,
            created_at=c.created_at,
            document_filename=doc.filename,
        )
        for c in chunks
    ]
