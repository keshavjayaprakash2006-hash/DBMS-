"""
Tests for chat endpoints and session management.
"""
import pytest


def _create_subject(client):
    resp = client.post("/api/subjects", json={"name": "Database Systems", "course_code": "CS301"})
    return resp.json()["subject_id"]


def test_chat_creates_session_and_message(client):
    subject_id = _create_subject(client)
    
    # Send a chat message (creates session automatically)
    resp = client.post("/api/chat", json={
        "subject_id": subject_id,
        "question": "What is the difference between B-trees and B+ trees?"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
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


def test_delete_chat_session(client):
    subject_id = _create_subject(client)
    resp = client.post("/api/chat", json={
        "subject_id": subject_id,
        "question": "Temporary session query"
    })
    session_id = resp.json()["session_id"]
    
    del_resp = client.delete(f"/api/chat/sessions/{session_id}")
    assert del_resp.status_code == 204
    
    # Verify gone
    get_resp = client.get(f"/api/chat/sessions/{session_id}")
    assert get_resp.status_code == 404


def test_send_chat_message_graceful_offline(client, monkeypatch):
    """When Ollama is offline, system should return honest guidance, not 500 crash."""
    subject_id = _create_subject(client)
    
    # Force check_ollama to return unavailable
    from app.services import chat_service
    monkeypatch.setattr(chat_service, "check_ollama", lambda: {"status": "unavailable", "error": "Offline"})
    
    resp = client.post("/api/chat", json={
        "subject_id": subject_id,
        "question": "Explain deadlock prevention"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "session_id" in data
