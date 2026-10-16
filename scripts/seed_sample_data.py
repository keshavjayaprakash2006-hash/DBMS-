#!/usr/bin/env python3
"""
Seed sample study notes and Previous Year Questions (PYQs) into the database via API.
Loads sample data for Operating Systems (CS204) and Database Management Systems (CS301),
uploads documents, imports PYQs, and triggers the semantic heatmap analysis.
"""
import os
import sys
import time
import requests

API_URL = os.getenv("API_URL", "http://localhost:8000")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data", "sample")


def check_api_health():
    print(f"Connecting to Semantic PYQ Analyzer API at {API_URL}...")
    try:
        resp = requests.get(f"{API_URL}/health", timeout=5)
        if resp.status_code == 200:
            print("Backend API is online and healthy.\n")
            return True
        print(f"Backend returned status {resp.status_code}")
        return False
    except Exception as e:
        print(f"Cannot connect to API at {API_URL}: {e}")
        print("Please ensure the FastAPI backend is running (uvicorn app.main:app --reload)")
        return False


def create_or_get_subject(name, course_code, description):
    print(f"Creating subject: {name} ({course_code})...")
    resp = requests.get(f"{API_URL}/api/subjects")
    if resp.status_code == 200:
        existing = [s for s in resp.json() if s["name"].lower() == name.lower()]
        if existing:
            print(f"Subject '{name}' already exists with ID: {existing[0]['subject_id']}")
            return existing[0]["subject_id"]

    resp = requests.post(f"{API_URL}/api/subjects", json={
        "name": name,
        "course_code": course_code,
        "description": description,
    })
    resp.raise_for_status()
    subject_id = resp.json()["subject_id"]
    print(f"Subject '{name}' created with ID: {subject_id}")
    return subject_id


def upload_document(subject_id, file_path):
    filename = os.path.basename(file_path)
    print(f"Uploading study notes: '{filename}'...")
    with open(file_path, "rb") as f:
        resp = requests.post(
            f"{API_URL}/api/documents/upload",
            data={"subject_id": subject_id},
            files={"file": (filename, f, "text/plain")},
        )
    resp.raise_for_status()
    doc_id = resp.json()["document_id"]
    print(f"Document uploaded (ID: {doc_id}). Background chunking & embedding started.")
    return doc_id


def import_pyqs(subject_id, csv_path):
    filename = os.path.basename(csv_path)
    print(f"Importing PYQs from '{filename}'...")
    with open(csv_path, "rb") as f:
        resp = requests.post(
            f"{API_URL}/api/pyqs/import-csv?subject_id={subject_id}",
            files={"file": (filename, f, "text/csv")},
        )
    resp.raise_for_status()
    data = resp.json()
    print(f"Imported {data.get('imported_count', 0)} questions from CSV.")


def wait_for_embeddings(subject_id, timeout=60):
    print("Waiting for paragraph chunks and PYQs to complete vector embeddings...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        resp = requests.get(f"{API_URL}/api/dashboard/subjects-overview")
        if resp.status_code == 200:
            subjects = resp.json().get("subjects", [])
            subj = next((s for s in subjects if s["subject_id"] == subject_id), None)
            if subj and subj.get("ready_for_analysis"):
                print(f"All embeddings ready! Chunks: {subj['embedded_chunks']}, PYQs: {subj['embedded_pyqs']}")
                return True
        time.sleep(2)
    print("Timeout waiting for background embeddings. Proceeding anyway.")
    return False


def trigger_analysis(subject_id):
    print("Triggering semantic heatmap analysis...")
    try:
        resp = requests.post(f"{API_URL}/api/subjects/{subject_id}/analyze")
        if resp.status_code == 200:
            analysis_id = resp.json()["analysis_id"]
            print(f"Heatmap analysis triggered successfully! (ID: {analysis_id})\n")
            return analysis_id
        else:
            print(f"Notice: Analysis trigger returned {resp.status_code}: {resp.text}\n")
    except Exception as e:
        print(f"Could not trigger analysis: {e}\n")
    return None


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
        os_id = create_or_get_subject(
            name="Operating Systems",
            course_code="CS204",
            description="Core concepts in OS: Process management, CPU scheduling, synchronization, deadlock, and memory management.",
        )
        upload_document(os_id, os_notes_path)
        import_pyqs(os_id, os_pyqs_path)
        wait_for_embeddings(os_id, timeout=30)
        trigger_analysis(os_id)

    # 2. Database Management Systems
    dbms_notes_path = os.path.join(DATA_DIR, "dbms_notes.txt")
    dbms_pyqs_path = os.path.join(DATA_DIR, "dbms_pyqs.csv")

    if os.path.exists(dbms_notes_path) and os.path.exists(dbms_pyqs_path):
        dbms_id = create_or_get_subject(
            name="Database Management Systems",
            course_code="CS301",
            description="Relational data model, SQL, functional dependencies, normalization, ACID transaction management, and indexing.",
        )
        upload_document(dbms_id, dbms_notes_path)
        import_pyqs(dbms_id, dbms_pyqs_path)
        wait_for_embeddings(dbms_id, timeout=30)
        trigger_analysis(dbms_id)

    print("=" * 65)
    print("  SAMPLE DATA SEEDED SUCCESSFULLY!")
    print("  Visit http://localhost:5173 to explore the Study Heatmap & AI Assistant.")
    print("=" * 65)


if __name__ == "__main__":
    main()
