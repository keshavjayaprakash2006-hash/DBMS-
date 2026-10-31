"""
Tests for chat endpoints and session management.
"""
import pytest
from app.services import chat_service


def _create_subject(client):
    resp = client.post("/api/subjects", json={"name": "Database Systems", "course_code": "CS301"})
    return resp.json()["subject_id"]


def test_chat_creates_session_and_message(client, monkeypatch):
    subject_id = _create_subject(client)

    # Mock chat_service to return a grounded study assistant response
    monkeypatch.setattr(
        chat_service,
        "generate_chat_response",
        lambda question, chunks, pyqs: (
            "B-trees store keys and values at all levels, whereas B+ trees store data pointers only at leaf nodes.",
            None,
        ),
    )

    # Send a chat message (creates session automatically)
    resp = client.post(
        "/api/chat",
        json={
            "subject_id": subject_id,
            "question": "What is the difference between B-trees and B+ trees?",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "B+ trees" in data["answer"]
    assert "session_id" in data
    session_id = data["session_id"]

    # List sessions
    list_resp = client.get("/api/chat/sessions")
    assert list_resp.status_code == 200
    sessions = list_resp.json()
    assert any(s["session_id"] == session_id for s in sessions)

    # Get session details
    detail_resp = client.get(f"/api/chat/sessions/{session_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["session"]["session_id"] == session_id
    assert len(detail["messages"]) >= 1


def test_delete_chat_session(client, monkeypatch):
    subject_id = _create_subject(client)
    monkeypatch.setattr(
        chat_service,
        "generate_chat_response",
        lambda question, chunks, pyqs: ("Temporary response", None),
    )

    resp = client.post(
        "/api/chat",
        json={"subject_id": subject_id, "question": "Temporary session query"},
    )
    session_id = resp.json()["session_id"]

    del_resp = client.delete(f"/api/chat/sessions/{session_id}")
    assert del_resp.status_code == 204

    # Verify gone
    get_resp = client.get(f"/api/chat/sessions/{session_id}")
    assert get_resp.status_code == 404


def test_send_chat_message_unconfigured_gemini(client):
    """When Gemini API key is missing, system returns honest guidance, not a 500 crash."""
    subject_id = _create_subject(client)

    resp = client.post(
        "/api/chat",
        json={"subject_id": subject_id, "question": "Explain deadlock prevention"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "session_id" in data
    assert "Google Gemini API is not configured" in data["answer"] or "GEMINI_API_KEY" in data["answer"]
