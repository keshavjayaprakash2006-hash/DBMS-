from datetime import datetime
from typing import Optional, List, Any
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


# ─── Subject Schemas ───────────────────────────────────────────────────────────

class SubjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    course_code: Optional[str] = Field(None, max_length=50)


class SubjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    course_code: Optional[str] = Field(None, max_length=50)


class SubjectOut(BaseModel):
    subject_id: UUID
    name: str
    description: Optional[str]
    course_code: Optional[str]
    created_at: datetime
    updated_at: datetime
    document_count: Optional[int] = 0
    pyq_count: Optional[int] = 0
    chunk_count: Optional[int] = 0

    model_config = {"from_attributes": True}


# ─── Document Schemas ──────────────────────────────────────────────────────────

class DocumentOut(BaseModel):
    document_id: UUID
    subject_id: UUID
    filename: str
    file_type: str
    processing_status: str
    processing_error: Optional[str]
    extracted_text_length: Optional[int]
    chunk_count: int
    embeddings_generated: bool
    created_at: datetime
    updated_at: datetime
    subject_name: Optional[str] = None

    model_config = {"from_attributes": True}


# ─── Note Chunk Schemas ────────────────────────────────────────────────────────

class NoteChunkOut(BaseModel):
    chunk_id: UUID
    subject_id: UUID
    document_id: UUID
    position: int
    content: str
    word_count: int
    has_embedding: bool = False
    created_at: datetime
    document_filename: Optional[str] = None
    subject_name: Optional[str] = None

    model_config = {"from_attributes": True}


# ─── PYQ Schemas ──────────────────────────────────────────────────────────────

class PYQCreate(BaseModel):
    subject_id: UUID
    exam_year: int = Field(..., ge=1990, le=2100)
    marks: int = Field(..., ge=1, le=100)
    question: str = Field(..., min_length=5)
    semester: Optional[str] = None
    course_code: Optional[str] = None
    unit_name: Optional[str] = None
    question_number: Optional[str] = None
    source_document: Optional[str] = None


class PYQUpdate(BaseModel):
    exam_year: Optional[int] = Field(None, ge=1990, le=2100)
    marks: Optional[int] = Field(None, ge=1, le=100)
    question: Optional[str] = Field(None, min_length=5)
    semester: Optional[str] = None
    course_code: Optional[str] = None
    unit_name: Optional[str] = None
    question_number: Optional[str] = None


class PYQOut(BaseModel):
    pyq_id: UUID
    subject_id: UUID
    exam_year: int
    marks: int
    question: str
    semester: Optional[str]
    course_code: Optional[str]
    unit_name: Optional[str]
    question_number: Optional[str]
    source_document: Optional[str]
    has_embedding: bool = False
    created_at: datetime
    updated_at: datetime
    subject_name: Optional[str] = None

    model_config = {"from_attributes": True}


class CSVImportResult(BaseModel):
    total_rows: int
    imported: int
    failed: int
    errors: List[dict]
    duplicate_skipped: int = 0


# ─── Analysis Schemas ─────────────────────────────────────────────────────────

class AnalysisRunOut(BaseModel):
    analysis_id: UUID
    subject_id: UUID
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    total_chunks: int
    total_questions: int
    matched_chunks: int
    configuration: Optional[dict]
    error_message: Optional[str]
    created_at: datetime
    subject_name: Optional[str] = None

    model_config = {"from_attributes": True}


class ChunkScoreOut(BaseModel):
    score_id: UUID
    analysis_id: UUID
    chunk_id: UUID
    hit_count: int
    weighted_marks: float
    importance_score: float
    score_metadata: Optional[dict]
    chunk_content: Optional[str] = None
    chunk_position: Optional[int] = None
    document_filename: Optional[str] = None
    matched_pyqs: Optional[List[dict]] = None

    model_config = {"from_attributes": True}


class HeatmapData(BaseModel):
    analysis: AnalysisRunOut
    scores: List[ChunkScoreOut]
    unmatched_chunks: List[NoteChunkOut]
    score_thresholds: dict


# ─── Search Schemas ───────────────────────────────────────────────────────────

class SemanticSearchRequest(BaseModel):
    query: str = Field(..., min_length=2)
    subject_id: Optional[UUID] = None
    top_k: int = Field(default=10, ge=1, le=50)


class SemanticSearchResult(BaseModel):
    chunk_id: UUID
    content: str
    similarity: float
    subject_name: str
    document_filename: str
    position: int
    word_count: int


# ─── Chat Schemas ─────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    question: str = Field(..., min_length=2)
    session_id: Optional[UUID] = None
    subject_id: Optional[UUID] = None


class ChatMessageOut(BaseModel):
    message_id: UUID
    session_id: UUID
    role: str
    content: str
    sources: Optional[dict]
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionOut(BaseModel):
    session_id: UUID
    subject_id: Optional[UUID]
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: Optional[int] = 0

    model_config = {"from_attributes": True}


class ChatResponse(BaseModel):
    answer: str
    session_id: UUID
    sources: List[dict]
    model_used: Optional[str]
    error: Optional[str] = None


# ─── Dashboard Schemas ────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_subjects: int
    total_documents: int
    total_chunks: int
    total_pyqs: int
    analyzed_subjects: int
    matched_chunks: int
    chunks_with_embeddings: int
    pyqs_with_embeddings: int


class RecentActivity(BaseModel):
    type: str
    description: str
    timestamp: datetime
    subject_name: Optional[str] = None


# ─── Health Schemas ───────────────────────────────────────────────────────────

class HealthStatus(BaseModel):
    status: str
    details: Optional[dict] = None


class SystemHealth(BaseModel):
    overall: str
    database: HealthStatus
    pgvector: HealthStatus
    embedding: HealthStatus
    ollama: HealthStatus
