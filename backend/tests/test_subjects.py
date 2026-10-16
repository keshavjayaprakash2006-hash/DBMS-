"""
Tests for subject CRUD operations.
"""
import pytest
from fastapi.testclient import TestClient


def test_create_subject(client):
    resp = client.post("/api/subjects", json={"name": "Operating Systems", "description": "OS course"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Operating Systems"
    assert "subject_id" in data


def test_list_subjects_empty(client):
    resp = client.get("/api/subjects")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_subjects(client):
    client.post("/api/subjects", json={"name": "DBMS"})
    client.post("/api/subjects", json={"name": "Networks"})
    resp = client.get("/api/subjects")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_get_subject(client):
    create_resp = client.post("/api/subjects", json={"name": "Test Subject"})
    subject_id = create_resp.json()["subject_id"]
    resp = client.get(f"/api/subjects/{subject_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Test Subject"


def test_get_nonexistent_subject(client):
    import uuid
    resp = client.get(f"/api/subjects/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_update_subject(client):
    create_resp = client.post("/api/subjects", json={"name": "Original Name"})
    subject_id = create_resp.json()["subject_id"]
    resp = client.patch(f"/api/subjects/{subject_id}", json={"name": "Updated Name"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Name"


def test_delete_subject(client):
    create_resp = client.post("/api/subjects", json={"name": "To Delete"})
    subject_id = create_resp.json()["subject_id"]
    delete_resp = client.delete(f"/api/subjects/{subject_id}")
    assert delete_resp.status_code == 204
    get_resp = client.get(f"/api/subjects/{subject_id}")
    assert get_resp.status_code == 404


def test_subject_requires_name(client):
    resp = client.post("/api/subjects", json={"description": "No name"})
    assert resp.status_code == 422
