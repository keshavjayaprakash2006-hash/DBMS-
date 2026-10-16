# Testing Strategy & Quality Assurance Report

The **Semantic PYQ Analyzer** employs automated testing across the database, vector embedding services, REST endpoints, and frontend build pipeline.

---

## 1. Test Architecture

```
tests/
├── conftest.py               # SQLite/Mock database fixtures and TestClient configuration
├── test_subjects.py          # Subject CRUD, validation, and error states
├── test_document_service.py  # File validation, normalization, and sliding-window chunking
├── test_pyqs.py              # PYQ CRUD, year/marks filters, CSV batch import
├── test_analysis.py          # Analysis prerequisites validation, status checking
├── test_search.py            # Local dense vector generation (384-d) & query validation
└── test_chat.py              # Chat sessions, message history, offline Ollama handling
```

---

## 2. Running Automated Tests

### Running Backend Unit & Integration Tests
```bash
cd backend
python -m pytest tests/ -v
```

Expected output:
```
tests/test_document_service.py::test_chunk_text_basic PASSED
tests/test_document_service.py::test_chunk_text_empty PASSED
tests/test_document_service.py::test_chunk_text_short PASSED
tests/test_document_service.py::test_chunk_text_preserves_paragraphs PASSED
tests/test_document_service.py::test_normalize_text PASSED
tests/test_document_service.py::test_validate_file_valid PASSED
tests/test_document_service.py::test_validate_file_invalid_extension PASSED
tests/test_document_service.py::test_validate_file_too_large PASSED
tests/test_document_service.py::test_get_file_extension PASSED
tests/test_document_service.py::test_extract_text_from_txt PASSED
tests/test_document_service.py::test_chunk_does_not_produce_duplicates PASSED
tests/test_pyqs.py::test_create_pyq PASSED
tests/test_pyqs.py::test_list_pyqs PASSED
tests/test_pyqs.py::test_filter_pyqs_by_year PASSED
tests/test_pyqs.py::test_delete_pyq PASSED
tests/test_pyqs.py::test_pyq_invalid_year PASSED
tests/test_pyqs.py::test_pyq_invalid_marks PASSED
tests/test_pyqs.py::test_csv_import PASSED
tests/test_pyqs.py::test_csv_import_invalid_rows PASSED
tests/test_pyqs.py::test_csv_import_missing_columns PASSED
tests/test_pyqs.py::test_csv_import_not_csv PASSED
tests/test_subjects.py::test_create_subject PASSED
tests/test_subjects.py::test_list_subjects_empty PASSED
tests/test_subjects.py::test_list_subjects PASSED
tests/test_subjects.py::test_get_subject PASSED
tests/test_subjects.py::test_get_nonexistent_subject PASSED
tests/test_subjects.py::test_update_subject PASSED
tests/test_subjects.py::test_delete_subject PASSED
tests/test_subjects.py::test_subject_requires_name PASSED
tests/test_chat.py::test_chat_creates_session_and_message PASSED
tests/test_chat.py::test_delete_chat_session PASSED
tests/test_chat.py::test_send_chat_message_graceful_offline PASSED
tests/test_search.py::test_embedding_service_dimensions PASSED
tests/test_search.py::test_embedding_service_deterministic PASSED
tests/test_search.py::test_semantic_search_empty_query PASSED
tests/test_analysis.py::test_trigger_analysis_nonexistent_subject PASSED
tests/test_analysis.py::test_trigger_analysis_missing_chunks_or_pyqs PASSED
tests/test_analysis.py::test_get_analysis_runs_empty PASSED
tests/test_analysis.py::test_get_heatmap_data_nonexistent_subject PASSED

======================== 39 passed in ~25s ========================
```

---

### Running Frontend Type-Check & Production Build
```bash
cd frontend
npm run build
```
This runs `tsc` (TypeScript compiler) and `vite build`, validating that all components, interfaces, routes, and styling tokens compile without errors.

---

## 3. Test Coverage Breakdown

| Test Area | Verified Behavior |
| :--- | :--- |
| **Document Chunking** | Correct chunk boundary splits, 50-word overlap preservation, duplicate suppression. |
| **File Validation** | Rejection of unauthorized extensions (.exe, .sh), enforcement of 50MB file size limit. |
| **Vector Dimensions** | Confirms `all-MiniLM-L6-v2` generates exact 384-dimensional float arrays deterministically. |
| **CSV Parser** | Graceful handling of malformed rows, missing headers, and invalid mark values. |
| **Database Cascades** | Deleting a subject deletes all linked documents, note chunks, scores, and runs. |
| **Offline Resilience** | AI assistant reports clear diagnostic instructions if Ollama is unreachable. |
