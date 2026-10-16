// Type definitions for all API entities

export interface Subject {
  subject_id: string;
  name: string;
  description?: string;
  course_code?: string;
  created_at: string;
  updated_at: string;
  document_count: number;
  pyq_count: number;
  chunk_count: number;
}

export interface Document {
  document_id: string;
  subject_id: string;
  filename: string;
  file_type: string;
  processing_status: 'pending' | 'processing' | 'completed' | 'failed' | 'needs_reprocess';
  processing_error?: string;
  extracted_text_length?: number;
  chunk_count: number;
  embeddings_generated: boolean;
  created_at: string;
  updated_at: string;
  subject_name?: string;
}

export interface NoteChunk {
  chunk_id: string;
  subject_id: string;
  document_id: string;
  position: number;
  content: string;
  word_count: number;
  has_embedding: boolean;
  created_at: string;
  document_filename?: string;
  subject_name?: string;
}

export interface PYQ {
  pyq_id: string;
  subject_id: string;
  exam_year: number;
  marks: number;
  question: string;
  semester?: string;
  course_code?: string;
  unit_name?: string;
  question_number?: string;
  source_document?: string;
  has_embedding: boolean;
  created_at: string;
  updated_at: string;
  subject_name?: string;
}

export interface AnalysisRun {
  analysis_id: string;
  subject_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  started_at?: string;
  completed_at?: string;
  total_chunks: number;
  total_questions: number;
  matched_chunks: number;
  configuration?: Record<string, unknown>;
  error_message?: string;
  created_at: string;
  subject_name?: string;
}

export interface MatchedPYQ {
  pyq_id: string;
  question: string;
  exam_year: number;
  marks: number;
  rank: number;
  cosine_distance: number;
  similarity: number;
}

export interface ChunkScore {
  score_id: string;
  analysis_id: string;
  chunk_id: string;
  hit_count: number;
  weighted_marks: number;
  importance_score: number;
  score_metadata?: {
    matched_pyqs?: MatchedPYQ[];
    max_hit_count?: number;
  };
  chunk_content?: string;
  chunk_position?: number;
  document_filename?: string;
  matched_pyqs?: MatchedPYQ[];
}

export interface HeatmapChunk {
  chunk_id: string;
  content: string;
  position: number;
  word_count?: number;
  document_filename: string;
  importance_score: number;
  hit_count: number;
  matched_pyqs?: MatchedPYQ[];
}

export interface HeatmapData {
  analysis: {
    analysis_id: string;
    subject_id: string;
    subject_name?: string;
    status: string;
    total_chunks: number;
    total_questions: number;
    matched_chunks: number;
    configuration?: Record<string, unknown>;
    completed_at?: string;
  };
  scored_chunks: ChunkScore[];
  unmatched_chunks: {
    chunk_id: string;
    content: string;
    position: number;
    word_count: number;
    document_filename?: string;
    importance_score: number;
    hit_count: number;
  }[];
  score_thresholds: {
    high: number;
    medium: number;
    low: number;
  };
  chunks?: HeatmapChunk[];
  max_hit_count?: number;
}

export interface SemanticSearchResult {
  chunk_id: string;
  content: string;
  similarity: number;
  subject_name: string;
  document_filename: string;
  position: number;
  word_count: number;
}

export interface ChatMessage {
  message_id: string;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: {
    chunks?: Array<{
      chunk_id: string;
      document: string;
      similarity: number;
      excerpt: string;
    }>;
    error?: string;
  };
  created_at: string;
}

export interface ChatSession {
  session_id: string;
  subject_id?: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ChatResponse {
  answer: string;
  session_id: string;
  sources: Array<{
    type: string;
    chunk_id: string;
    document: string;
    similarity: number;
    excerpt: string;
  }>;
  model_used?: string;
  error?: string;
}

export interface DashboardStats {
  total_subjects: number;
  total_documents: number;
  total_chunks: number;
  total_pyqs: number;
  analyzed_subjects: number;
  matched_chunks: number;
  chunks_with_embeddings: number;
  pyqs_with_embeddings: number;
}

export interface SystemHealth {
  overall: string;
  database: { status: string; details?: Record<string, unknown> };
  pgvector: { status: string; details?: Record<string, unknown> };
  embedding: { status: string; details?: Record<string, unknown> };
  ollama: { status: string; details?: Record<string, unknown> };
}

export interface CSVImportResult {
  total_rows: number;
  imported: number;
  failed: number;
  duplicate_skipped: number;
  errors: Array<{ row: number; error: string; data: Record<string, string> }>;
}
