"""
Tests for analysis endpoints and prerequisites validation.
"""
import pytest
from uuid import uuid4


def _create_subject(client):
    resp = client.post("/api/subjects", json={"name": "Analysis Subject", "course_code": "CS204"})
    return resp.json()["subject_id"]


def test_trigger_analysis_nonexistent_subject(client):
    random_id = uuid4()
    resp = client.post(f"/api/subjects/{random_id}/analyze")
    assert resp.status_code == 404


def test_trigger_analysis_missing_chunks_or_pyqs(client):
    """Analysis requires at least one embedded chunk and one embedded PYQ."""
    subject_id = _create_subject(client)
    resp = client.post(f"/api/subjects/{subject_id}/analyze")
    assert resp.status_code == 422
    assert "Upload and process documents first" in resp.json()["detail"]


def test_get_analysis_runs_empty(client):
    subject_id = _create_subject(client)
    resp = client.get(f"/api/subjects/{subject_id}/analysis")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_heatmap_data_nonexistent_subject(client):
    random_id = uuid4()
    resp = client.get(f"/api/subjects/{random_id}/heatmap")
    assert resp.status_code == 404
