#!/usr/bin/env python3
"""
Seed sample study notes and Previous Year Questions (PYQs) into the database via API.
Loads sample data for Operating Systems (CS204) and Database Management Systems (CS301),
uploads documents, imports PYQs, waits for vector embeddings, and triggers heatmap analysis.
"""
import os
import sys
import time
import requests

API_URL = os.getenv("API_URL", "http://localhost:8000")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data", "sample")


def log_api_error(action: str, resp: requests.Response):
    """Log formatted API error with endpoint, status code, and response content."""
    print(f"\n[ERROR] Failed to {action}:")
    print(f"  Endpoint:    {resp.request.method} {resp.url}")
    print(f"  Status Code: {resp.status_code}")
    print(f"  Response:    {resp.text}\n")


def check_api_health() -> bool:
    print(f"Connecting to Semantic PYQ Analyzer API at {API_URL}...")
    # Try /api/health first, then /health
    for path in ["/api/health", "/health"]:
        try:
            url = f"{API_URL}{path}"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                print(f"Backend API is online and healthy ({url} -> {data}).\n")
                return True
            else:
                log_api_error("check health", resp)
        except requests.RequestException as e:
            print(f"Connection attempt to {API_URL}{path} failed: {e}")

    print("Please ensure the FastAPI backend is running via Docker (docker compose up -d)")
    return False


def create_or_get_subject(name: str, course_code: str, description: str) -> str:
    print(f"Checking subject: {name} ({course_code})...")
    url = f"{API_URL}/api/subjects"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            existing = [s for s in resp.json() if s["name"].lower() == name.lower()]
            if existing:
                subject_id = existing[0]["subject_id"]
                print(f"Subject '{name}' already exists (ID: {subject_id})")
                return subject_id
        else:
            log_api_error("list subjects", resp)
    except requests.RequestException as e:
        print(f"Error checking existing subjects: {e}")

    print(f"Creating subject: {name} ({course_code})...")
    resp = requests.post(url, json={
        "name": name,
        "course_code": course_code,
        "description": description,
    }, timeout=10)

    if resp.status_code not in (200, 201):
        log_api_error(f"create subject '{name}'", resp)
        resp.raise_for_status()

    subject_id = resp.json()["subject_id"]
    print(f"Subject '{name}' created with ID: {subject_id}")
    return subject_id


def upload_document(subject_id: str, file_path: str) -> str:
    filename = os.path.basename(file_path)
    # Check if document already exists for this subject
    docs_url = f"{API_URL}/api/documents"
    try:
        resp = requests.get(docs_url, params={"subject_id": subject_id}, timeout=10)
        if resp.status_code == 200:
            existing = [d for d in resp.json() if d["filename"] == filename]
            if existing:
                doc = existing[0]
                doc_id = doc["document_id"]
                status = doc.get("processing_status")
                chunk_count = doc.get("chunk_count", 0)
                if status == "completed" and chunk_count > 0:
                    print(f"Document '{filename}' already exists and processed ({chunk_count} chunks, ID: {doc_id}).")
                    return doc_id
                elif status == "failed":
                    print(f"Document '{filename}' previously failed. Requesting reprocess...")
                    reprocess_resp = requests.post(f"{API_URL}/api/documents/{doc_id}/reprocess", timeout=10)
                    if reprocess_resp.status_code == 200:
                        return doc_id
    except requests.RequestException as e:
        print(f"Notice: Checking existing documents failed: {e}")

    print(f"Uploading study notes: '{filename}'...")
    upload_url = f"{API_URL}/api/documents/upload"
    with open(file_path, "rb") as f:
        resp = requests.post(
            upload_url,
            data={"subject_id": subject_id},
            files={"file": (filename, f, "text/plain")},
            timeout=30,
        )

    if resp.status_code not in (200, 201):
        log_api_error(f"upload document '{filename}'", resp)
        resp.raise_for_status()

    doc_id = resp.json()["document_id"]
    print(f"Document uploaded (ID: {doc_id}). Background chunking & embedding started.")
    return doc_id


def import_pyqs(subject_id: str, csv_path: str):
    filename = os.path.basename(csv_path)
    print(f"Importing PYQs from '{filename}'...")
    import_url = f"{API_URL}/api/pyqs/import-csv"
    with open(csv_path, "rb") as f:
        resp = requests.post(
            import_url,
            params={"subject_id": subject_id},
            files={"file": (filename, f, "text/csv")},
            timeout=30,
        )

    if resp.status_code != 200:
        log_api_error(f"import PYQs from '{filename}'", resp)
        resp.raise_for_status()

    data = resp.json()
    imported = data.get("imported", 0)
    skipped = data.get("duplicate_skipped", 0)
    failed = data.get("failed", 0)
    print(f"PYQ Import Result: {imported} imported, {skipped} duplicate skipped, {failed} failed.")
    if data.get("errors"):
        print(f"  Import errors encountered: {data['errors']}")


def wait_for_embeddings(subject_id: str, timeout: int = 60) -> bool:
    print("Waiting for paragraph chunks and PYQs to complete vector embeddings...")
    start_time = time.time()
    last_status = ""
    while time.time() - start_time < timeout:
        try:
            resp = requests.get(f"{API_URL}/api/dashboard/subjects-overview", timeout=10)
            if resp.status_code == 200:
                subjects = resp.json().get("subjects", [])
                subj = next((s for s in subjects if s["subject_id"] == subject_id), None)
                if subj:
                    chunks = subj.get("chunk_count", 0)
                    emb_chunks = subj.get("embedded_chunks", 0)
                    pyqs = subj.get("pyq_count", 0)
                    emb_pyqs = subj.get("embedded_pyqs", 0)
                    status_line = f"Chunks: {emb_chunks}/{chunks}, PYQs: {emb_pyqs}/{pyqs}"
                    if status_line != last_status:
                        print(f"  Progress: {status_line}")
                        last_status = status_line
                    if subj.get("ready_for_analysis") and emb_chunks >= chunks and emb_pyqs >= pyqs:
                        print(f"All embeddings ready! Chunks: {emb_chunks}, PYQs: {emb_pyqs}")
                        return True
        except requests.RequestException:
            pass
        time.sleep(2)

    print("Timeout waiting for background embeddings. Checking if ready for analysis...")
    try:
        resp = requests.get(f"{API_URL}/api/dashboard/subjects-overview", timeout=10)
        if resp.status_code == 200:
            subjects = resp.json().get("subjects", [])
            subj = next((s for s in subjects if s["subject_id"] == subject_id), None)
            if subj and subj.get("ready_for_analysis"):
                print("Subject has embeddings ready for analysis.")
                return True
    except Exception:
        pass
    return False


def trigger_and_wait_analysis(subject_id: str, timeout: int = 60) -> str:
    print("Triggering semantic heatmap analysis...")
    analyze_url = f"{API_URL}/api/subjects/{subject_id}/analyze"
    try:
        resp = requests.post(analyze_url, timeout=15)
        if resp.status_code in (200, 201):
            analysis_id = resp.json()["analysis_id"]
            print(f"Heatmap analysis triggered! (ID: {analysis_id})")
        else:
            log_api_error("trigger analysis", resp)
            return None
    except Exception as e:
        print(f"Could not trigger analysis: {e}")
        return None

    # Wait for analysis completion
    print("Waiting for analysis to complete...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            status_resp = requests.get(f"{API_URL}/api/analysis/{analysis_id}", timeout=10)
            if status_resp.status_code == 200:
                status_data = status_resp.json()
                status = status_data.get("status")
                if status == "completed":
                    matched = status_data.get("matched_chunks", 0)
                    print(f"Heatmap analysis completed successfully! ({matched} chunks matched)")
                    return analysis_id
                elif status == "failed":
                    err = status_data.get("error_message", "Unknown error")
                    print(f"[ERROR] Analysis failed: {err}")
                    return None
        except requests.RequestException:
            pass
        time.sleep(2)

    print("Timed out waiting for analysis run to complete.")
    return analysis_id


def verify_subject_data(subject_id: str):
    """Verify that notes, PYQs, and heatmap are accessible via API."""
    try:
        subj_resp = requests.get(f"{API_URL}/api/subjects/{subject_id}", timeout=10)
        if subj_resp.status_code == 200:
            s = subj_resp.json()
            print(f"  Subject '{s['name']}': {s['document_count']} docs, {s['chunk_count']} chunks, {s['pyq_count']} PYQs")

        # Check analysis runs
        runs_resp = requests.get(f"{API_URL}/api/subjects/{subject_id}/analysis", timeout=10)
        if runs_resp.status_code == 200 and runs_resp.json():
            latest = runs_resp.json()[0]
            print(f"  Latest Analysis: status={latest['status']}, matched_chunks={latest['matched_chunks']}")
            heatmap_resp = requests.get(f"{API_URL}/api/analysis/{latest['analysis_id']}/heatmap", timeout=10)
            if heatmap_resp.status_code == 200:
                hm = heatmap_resp.json()
                scored = len(hm.get("scored_chunks", []))
                unmatched = len(hm.get("unmatched_chunks", []))
                print(f"  Heatmap Data: {scored} scored chunks, {unmatched} unmatched chunks")
    except Exception as e:
        print(f"Verification notice: {e}")


def main():
    print("=" * 65)
    print("  SEMANTIC PYQ ANALYZER - SAMPLE DATA SEED SCRIPT")
    print("=" * 65)

    if not check_api_health():
        sys.exit(1)

    # 1. Operating Systems
    os_notes_path = os.path.join(DATA_DIR, "os_notes.txt")
    os_pyqs_path = os.path.join(DATA_DIR, "os_pyqs.csv")

    if os.path.exists(os_notes_path) and os.path.exists(os_pyqs_path):
        print("\n--- [1/2] Seeding Operating Systems (CS204) ---")
        os_id = create_or_get_subject(
            name="Operating Systems",
            course_code="CS204",
            description="Core concepts in OS: Process management, CPU scheduling, synchronization, deadlock, and memory management.",
        )
        upload_document(os_id, os_notes_path)
        import_pyqs(os_id, os_pyqs_path)
        if wait_for_embeddings(os_id, timeout=45):
            trigger_and_wait_analysis(os_id, timeout=45)
        verify_subject_data(os_id)
    else:
        print(f"Missing OS sample files in {DATA_DIR}")

    # 2. Database Management Systems
    dbms_notes_path = os.path.join(DATA_DIR, "dbms_notes.txt")
    dbms_pyqs_path = os.path.join(DATA_DIR, "dbms_pyqs.csv")

    if os.path.exists(dbms_notes_path) and os.path.exists(dbms_pyqs_path):
        print("\n--- [2/2] Seeding Database Management Systems (CS301) ---")
        dbms_id = create_or_get_subject(
            name="Database Management Systems",
            course_code="CS301",
            description="Relational data model, SQL, functional dependencies, normalization, ACID transaction management, and indexing.",
        )
        upload_document(dbms_id, dbms_notes_path)
        import_pyqs(dbms_id, dbms_pyqs_path)
        if wait_for_embeddings(dbms_id, timeout=45):
            trigger_and_wait_analysis(dbms_id, timeout=45)
        verify_subject_data(dbms_id)
    else:
        print(f"Missing DBMS sample files in {DATA_DIR}")

    print("\n" + "=" * 65)
    print("  SAMPLE DATA SEEDED SUCCESSFULLY!")
    print("  Frontend UI:  http://localhost:3000")
    print("  Backend Docs: http://localhost:8000/docs")
    print("=" * 65)


if __name__ == "__main__":
    main()
