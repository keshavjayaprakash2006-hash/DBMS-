"""
Tests for cloud service integrations:
- Gemini AI service & RAG prompt generation
- Gemini & local embedding service
- Storage service (Supabase & local fallback)
- Health endpoints (system, database, ai, embedding, storage)
- Document download endpoint
"""
import pytest
from app.services import chat_service, embedding_service, storage_service


def test_build_rag_prompt_structure():
    chunks = [
        {"document_filename": "os_unit1.pdf", "content": "Virtual memory uses paging and segmentation."}
    ]
    pyqs = [
        {"exam_year": 2023, "marks": 10, "question": "Explain paging with a neat diagram."}
    ]
    prompt = chat_service.build_rag_prompt("How does paging work?", chunks, pyqs)
    assert "STUDY MATERIAL:" in prompt
    assert "os_unit1.pdf" in prompt
    assert "Virtual memory uses paging" in prompt
    assert "Related Previous Year Questions" in prompt
    assert "Explain paging with a neat diagram" in prompt
    assert "STUDENT QUESTION:" in prompt


def test_storage_service_local_save_retrieve_delete():
    content = b"Sample test syllabus file content."
    filename = "test_note.txt"
    stored_path, local_path = storage_service.save_file(content, filename, "text/plain")
    assert stored_path is not None
    assert local_path is not None

    # Retrieve
    retrieved = storage_service.get_file_bytes(stored_path)
    assert retrieved == content

    # Delete
    storage_service.delete_file(stored_path)
    # Ensure cleaned up
    assert storage_service.get_file_bytes(stored_path) is None


def test_document_download_endpoint(client):
    # 1. Create subject
    subj_resp = client.post("/api/subjects", json={"name": "Cloud Storage Test Subject"})
    assert subj_resp.status_code == 201
    subj_id = subj_resp.json()["subject_id"]

    # 2. Upload document
    file_bytes = b"Course Syllabus: Module 1 Introduction to Cloud Architecture."
    upload_resp = client.post(
        "/api/documents/upload",
        data={"subject_id": subj_id},
        files={"file": ("syllabus.txt", file_bytes, "text/plain")},
    )
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["document_id"]

    # 3. Test download endpoint
    dl_resp = client.get(f"/api/documents/{doc_id}/download")
    assert dl_resp.status_code == 200
    assert dl_resp.content == file_bytes
    assert "attachment" in dl_resp.headers.get("content-disposition", "")
    assert "syllabus.txt" in dl_resp.headers.get("content-disposition", "")

    # 4. Test view endpoint
    view_resp = client.get(f"/api/documents/{doc_id}/view")
    assert view_resp.status_code == 200
    assert view_resp.content == file_bytes
    assert "inline" in view_resp.headers.get("content-disposition", "")


def test_health_endpoints(client):
    # Root health
    r0 = client.get("/health")
    assert r0.status_code == 200
    assert r0.json()["status"] == "ok"

    # API health
    r1 = client.get("/api/health")
    assert r1.status_code == 200

    # Database health
    r_db = client.get("/api/health/database")
    assert r_db.status_code == 200
    assert "status" in r_db.json()

    # Embedding health
    r_emb = client.get("/api/health/embedding")
    assert r_emb.status_code == 200
    assert "status" in r_emb.json()

    # AI health
    r_ai = client.get("/api/health/ai")
    assert r_ai.status_code == 200
    assert "status" in r_ai.json()

    # Storage health
    r_st = client.get("/api/health/storage")
    assert r_st.status_code == 200
    assert "status" in r_st.json()

    # System aggregated health
    r_sys = client.get("/api/health/system")
    assert r_sys.status_code == 200
    sys_data = r_sys.json()
    assert "overall" in sys_data
    assert "database" in sys_data
    assert "embedding" in sys_data
    assert "ai" in sys_data
    assert "storage" in sys_data
