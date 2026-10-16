"""Initial database schema with pgvector and HNSW indexes

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-16 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import pgvector

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Table: subjects
    op.create_table(
        'subjects',
        sa.Column('subject_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('course_code', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # Table: documents
    op.create_table(
        'documents',
        sa.Column('document_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('subject_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('subjects.subject_id', ondelete='CASCADE'), nullable=False),
        sa.Column('filename', sa.String(500), nullable=False),
        sa.Column('stored_path', sa.String(1000), nullable=False),
        sa.Column('file_type', sa.String(50), nullable=False),
        sa.Column('processing_status', sa.String(50), nullable=False),
        sa.Column('processing_error', sa.Text(), nullable=True),
        sa.Column('extracted_text_length', sa.Integer(), nullable=True),
        sa.Column('chunk_count', sa.Integer(), default=0),
        sa.Column('embeddings_generated', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # Table: note_chunks
    op.create_table(
        'note_chunks',
        sa.Column('chunk_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('subject_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('subjects.subject_id', ondelete='CASCADE'), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.document_id', ondelete='CASCADE'), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('word_count', sa.Integer(), default=0),
        sa.Column('embedding', pgvector.sqlalchemy.Vector(384), nullable=True),
        sa.Column('embedding_model', sa.String(200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    # Table: pyqs
    op.create_table(
        'pyqs',
        sa.Column('pyq_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('subject_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('subjects.subject_id', ondelete='CASCADE'), nullable=False),
        sa.Column('exam_year', sa.Integer(), nullable=False),
        sa.Column('marks', sa.Integer(), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('semester', sa.String(50), nullable=True),
        sa.Column('course_code', sa.String(50), nullable=True),
        sa.Column('unit_name', sa.String(255), nullable=True),
        sa.Column('question_number', sa.String(20), nullable=True),
        sa.Column('source_document', sa.String(500), nullable=True),
        sa.Column('embedding', pgvector.sqlalchemy.Vector(384), nullable=True),
        sa.Column('embedding_model', sa.String(200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    # Table: analysis_runs
    op.create_table(
        'analysis_runs',
        sa.Column('analysis_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('subject_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('subjects.subject_id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_chunks', sa.Integer(), default=0),
        sa.Column('total_questions', sa.Integer(), default=0),
        sa.Column('matched_chunks', sa.Integer(), default=0),
        sa.Column('configuration', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    # Table: chunk_scores
    op.create_table(
        'chunk_scores',
        sa.Column('score_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('analysis_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('analysis_runs.analysis_id', ondelete='CASCADE'), nullable=False),
        sa.Column('chunk_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('note_chunks.chunk_id', ondelete='CASCADE'), nullable=False),
        sa.Column('hit_count', sa.Integer(), default=0),
        sa.Column('weighted_marks', sa.Float(), default=0.0),
        sa.Column('importance_score', sa.Float(), default=0.0),
        sa.Column('score_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('analysis_id', 'chunk_id', name='uq_analysis_chunk'),
    )

    # Table: chat_sessions
    op.create_table(
        'chat_sessions',
        sa.Column('session_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('subject_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('subjects.subject_id', ondelete='SET NULL'), nullable=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # Table: chat_messages
    op.create_table(
        'chat_messages',
        sa.Column('message_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('chat_sessions.session_id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('sources', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    # Create HNSW index for high-speed vector similarity searches
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_note_chunks_embedding_hnsw "
        "ON note_chunks USING hnsw (embedding vector_cosine_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_pyqs_embedding_hnsw "
        "ON pyqs USING hnsw (embedding vector_cosine_ops)"
    )

    # B-Tree relational indexes
    op.create_index('idx_note_chunks_subject', 'note_chunks', ['subject_id'])
    op.create_index('idx_note_chunks_document', 'note_chunks', ['document_id'])
    op.create_index('idx_pyqs_subject', 'pyqs', ['subject_id'])
    op.create_index('idx_pyqs_year', 'pyqs', ['exam_year'])
    op.create_index('idx_pyqs_marks', 'pyqs', ['marks'])
    op.create_index('idx_chunk_scores_analysis', 'chunk_scores', ['analysis_id'])
    op.create_index('idx_chunk_scores_importance', 'chunk_scores', ['importance_score'])


def downgrade() -> None:
    op.drop_table('chat_messages')
    op.drop_table('chat_sessions')
    op.drop_table('chunk_scores')
    op.drop_table('analysis_runs')
    op.drop_table('pyqs')
    op.drop_table('note_chunks')
    op.drop_table('documents')
    op.drop_table('subjects')
    op.execute("DROP EXTENSION IF EXISTS vector")
