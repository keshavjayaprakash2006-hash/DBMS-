# REST API Specification

The Semantic PYQ Analyzer exposes a RESTful API built with **FastAPI**. Interactive Swagger UI documentation is available at `http://localhost:8000/docs`.

---

## 1. Subjects (`/api/subjects`)

### `GET /api/subjects`
List all academic subjects.
- **Response**: `200 OK`
```json
[
  {
    "subject_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "name": "Operating Systems",
    "course_code": "CS204",
    "description": "Core systems topics",
    "created_at": "2026-10-16T12:00:00Z",
    "updated_at": "2026-10-16T12:00:00Z"
  }
]
```

### `POST /api/subjects`
Create a new academic subject.
- **Request Body**:
```json
{
  "name": "Database Management Systems",
  "course_code": "CS301",
  "description": "Relational algebra, SQL, normalization, and ACID transactions"
}
```
- **Response**: `201 Created`

### `GET /api/subjects/{subject_id}`
Retrieve subject details by UUID.

### `PATCH /api/subjects/{subject_id}`
Update subject metadata.

### `DELETE /api/subjects/{subject_id}`
Delete a subject and all associated documents, note chunks, and analysis runs (`CASCADE`).

---

## 2. Documents (`/api/documents`)

### `POST /api/documents/upload`
Upload a notes file (multipart form data).
- **Form Data**:
  - `subject_id` (UUID, required)
  - `file` (Binary, supported: `.pdf`, `.docx`, `.txt`)
- **Response**: `200 OK`
```json
{
  "document_id": "e6a48d88-b223-455c-b196-857e31464973",
  "subject_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "filename": "os_notes.txt",
  "file_type": "txt",
  "processing_status": "pending",
  "chunk_count": 0,
  "embeddings_generated": false
}
```

### `GET /api/documents`
List documents. Optional query parameter: `?subject_id={uuid}`.

### `GET /api/documents/{document_id}/chunks`
Retrieve all paragraph chunks created for a specific document.

### `POST /api/documents/{document_id}/reprocess`
Trigger background re-extraction, re-chunking, and vector re-embedding.

### `DELETE /api/documents/{document_id}`
Delete document and cascade delete its chunks.

---

## 3. PYQ Library (`/api/pyqs`)

### `GET /api/pyqs`
Filter questions.
- **Query Parameters**:
  - `subject_id` (UUID, optional)
  - `exam_year` (Integer, optional)
  - `marks` (Integer, optional)
  - `skip` (Integer, default 0)
  - `limit` (Integer, default 50)

### `POST /api/pyqs`
Add an individual question.
- **Request Body**:
```json
{
  "subject_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "exam_year": 2024,
  "marks": 10,
  "question": "Explain Deadlock detection using wait-for graphs.",
  "semester": "Semester 5",
  "unit_name": "Unit 4"
}
```

### `POST /api/pyqs/import-csv?subject_id={uuid}`
Bulk import questions from CSV file.
- **Form Data**: `file` (CSV file)
- **Response**:
```json
{
  "status": "success",
  "imported_count": 12,
  "subject_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"
}
```

### `DELETE /api/pyqs/{pyq_id}`
Delete a question from the library.

---

## 4. Heatmap & Analysis (`/api`)

### `POST /api/subjects/{subject_id}/analyze`
Trigger semantic importance calculation between note chunks and PYQs.
- **Response**: `200 OK` (AnalysisRun record with status `pending` or `running`).

### `GET /api/subjects/{subject_id}/analysis`
List historical analysis runs for a subject.

### `GET /api/analysis/{analysis_id}/heatmap`
Retrieve color-coded heatmap data with calculated scores and match evidence.
- **Response**:
```json
{
  "analysis": {
    "analysis_id": "c1f71df9-780c-4fa2-bc40-eef41131758c",
    "subject_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "status": "completed",
    "total_chunks": 42,
    "matched_chunks": 28
  },
  "scored_chunks": [
    {
      "chunk_id": "a5e8c459-7b3b-4899-b13c-7be1a80c5cb2",
      "importance_score": 0.85,
      "hit_count": 4,
      "chunk_content": "A deadlock occurs when...",
      "document_filename": "os_notes.txt",
      "matched_pyqs": [
        {
          "pyq_id": "783f98c4-...",
          "question": "Explain deadlock handling...",
          "similarity": 0.88,
          "exam_year": 2023,
          "marks": 10
        }
      ]
    }
  ],
  "unmatched_chunks": [],
  "score_thresholds": { "high": 0.75, "medium": 0.40, "low": 0.01 }
}
```

---

## 5. Semantic Search (`/api/search`)

### `POST /api/search/semantic`
Query notes using 384-dimensional dense vectors and pgvector cosine distance `<=>`.
- **Request Body**:
```json
{
  "query": "What is two-phase locking in DBMS?",
  "subject_id": "optional-uuid",
  "top_k": 5
}
```
- **Response**: Ranked array of chunks with `similarity` (0.0 to 1.0).

---

## 6. RAG Chat Assistant (`/api/chat`)

### `POST /api/chat`
Ask study questions grounded in notes and exam trends.
- **Request Body**:
```json
{
  "question": "Can you explain B+ tree node splitting with an example?",
  "subject_id": "optional-uuid",
  "session_id": "optional-uuid"
}
```
- **Response**:
```json
{
  "answer": "In a B+ Tree, when a node exceeds its maximum order p...",
  "session_id": "f8a70c89-...",
  "sources": [
    {
      "chunk_id": "...",
      "content": "...",
      "document_filename": "dbms_notes.txt",
      "similarity": 0.86
    }
  ],
  "model_used": "mistral"
}
```

### `GET /api/chat/sessions`
List recent chat conversation sessions.

### `GET /api/chat/sessions/{session_id}`
Retrieve full message history for a conversation.

### `DELETE /api/chat/sessions/{session_id}`
Delete a conversation session and all its messages.

---

## 7. Dashboard & Health (`/api/dashboard`, `/api/health`)

- `GET /api/dashboard/stats`: Global totals (subjects, documents, chunks, pyqs, embeddings, matches).
- `GET /api/dashboard/activity`: Recent activity log across all entities.
- `GET /api/dashboard/subjects-overview`: Subject readiness status for analysis.
- `GET /api/dashboard/analytics`: Aggregated year distribution, marks distribution, top-10 chunks.
- `GET /api/health/system`: Overall system health and uptime.
- `GET /api/health/database`: PostgreSQL connection and pgvector extension status.
- `GET /api/health/ollama`: Local Ollama LLM connectivity and available models.
