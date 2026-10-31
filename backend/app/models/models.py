from datetime import datetime, timezone
from typing import Optional, List
import uuid

from sqlalchemy import (
    String, Text, Integer, Float, DateTime, Boolean,
    ForeignKey, UniqueConstraint, JSON, Enum as SAEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector

from app.db.database import Base
from app.core.config import settings
import enum


def utcnow():
    return datetime.now(timezone.utc)


class ProcessingStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_REPROCESS = "needs_reprocess"


class AnalysisStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Subject(Base):
    __tablename__ = "subjects"

    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    course_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    documents: Mapped[List["Document"]] = relationship(
        "Document", back_populates="subject", cascade="all, delete-orphan"
    )
    note_chunks: Mapped[List["NoteChunk"]] = relationship(
        "NoteChunk", back_populates="subject", cascade="all, delete-orphan"
    )
    pyqs: Mapped[List["PYQ"]] = relationship(
        "PYQ", back_populates="subject", cascade="all, delete-orphan"
    )
    analysis_runs: Mapped[List["AnalysisRun"]] = relationship(
        "AnalysisRun", back_populates="subject", cascade="all, delete-orphan"
    )


class Document(Base):
    __tablename__ = "documents"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.subject_id", ondelete="CASCADE"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    processing_status: Mapped[str] = mapped_column(
        String(50), default=ProcessingStatus.PENDING, nullable=False
    )
    processing_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extracted_text_length: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    embeddings_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    subject: Mapped["Subject"] = relationship("Subject", back_populates="documents")
    note_chunks: Mapped[List["NoteChunk"]] = relationship(
        "NoteChunk", back_populates="document", cascade="all, delete-orphan"
    )


class NoteChunk(Base):
    __tablename__ = "note_chunks"

    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.subject_id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.document_id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    embedding: Mapped[Optional[List[float]]] = mapped_column(
        Vector(settings.EMBEDDING_DIMENSION), nullable=True
    )
    embedding_model: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    subject: Mapped["Subject"] = relationship("Subject", back_populates="note_chunks")
    document: Mapped["Document"] = relationship("Document", back_populates="note_chunks")
    chunk_scores: Mapped[List["ChunkScore"]] = relationship(
        "ChunkScore", back_populates="chunk", cascade="all, delete-orphan"
    )


class PYQ(Base):
    __tablename__ = "pyqs"

    pyq_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.subject_id", ondelete="CASCADE"), nullable=False
    )
    exam_year: Mapped[int] = mapped_column(Integer, nullable=False)
    marks: Mapped[int] = mapped_column(Integer, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    semester: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    course_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    unit_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    question_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    source_document: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    embedding: Mapped[Optional[List[float]]] = mapped_column(
        Vector(settings.EMBEDDING_DIMENSION), nullable=True
    )
    embedding_model: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    subject: Mapped["Subject"] = relationship("Subject", back_populates="pyqs")


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.subject_id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), default=AnalysisStatus.PENDING, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    total_chunks: Mapped[int] = mapped_column(Integer, default=0)
    total_questions: Mapped[int] = mapped_column(Integer, default=0)
    matched_chunks: Mapped[int] = mapped_column(Integer, default=0)
    configuration: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    subject: Mapped["Subject"] = relationship("Subject", back_populates="analysis_runs")
    chunk_scores: Mapped[List["ChunkScore"]] = relationship(
        "ChunkScore", back_populates="analysis_run", cascade="all, delete-orphan"
    )


class ChunkScore(Base):
    __tablename__ = "chunk_scores"

    score_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_runs.analysis_id", ondelete="CASCADE"), nullable=False
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("note_chunks.chunk_id", ondelete="CASCADE"), nullable=False
    )
    hit_count: Mapped[int] = mapped_column(Integer, default=0)
    weighted_marks: Mapped[float] = mapped_column(Float, default=0.0)
    importance_score: Mapped[float] = mapped_column(Float, default=0.0)
    score_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        UniqueConstraint("analysis_id", "chunk_id", name="uq_analysis_chunk"),
    )

    analysis_run: Mapped["AnalysisRun"] = relationship("AnalysisRun", back_populates="chunk_scores")
    chunk: Mapped["NoteChunk"] = relationship("NoteChunk", back_populates="chunk_scores")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    subject_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.subject_id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(500), default="New Chat")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chat_sessions.session_id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user / assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")
