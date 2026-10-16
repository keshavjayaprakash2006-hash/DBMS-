"""
Tests for PYQ management endpoints.
"""
import io
import pytest


def _create_subject(client):
    resp = client.post("/api/subjects", json={"name": "Test Subject"})
    return resp.json()["subject_id"]


def test_create_pyq(client):
    subject_id = _create_subject(client)
    resp = client.post("/api/pyqs", json={
        "subject_id": subject_id,
        "exam_year": 2023,
        "marks": 10,
        "question": "Explain deadlock prevention in operating systems.",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["exam_year"] == 2023
    assert data["marks"] == 10
    assert "pyq_id" in data


def test_list_pyqs(client):
    subject_id = _create_subject(client)
    for i in range(3):
        client.post("/api/pyqs", json={
            "subject_id": subject_id,
            "exam_year": 2020 + i,
            "marks": 5,
            "question": f"Question number {i} about the subject.",
        })
    resp = client.get(f"/api/pyqs?subject_id={subject_id}")
    assert resp.status_code == 200
    assert len(resp.json()) == 3


def test_filter_pyqs_by_year(client):
    subject_id = _create_subject(client)
    client.post("/api/pyqs", json={"subject_id": subject_id, "exam_year": 2021, "marks": 5, "question": "Year 2021 question about processes."})
    client.post("/api/pyqs", json={"subject_id": subject_id, "exam_year": 2022, "marks": 5, "question": "Year 2022 question about memory."})
    resp = client.get(f"/api/pyqs?subject_id={subject_id}&exam_year=2021")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["exam_year"] == 2021


def test_delete_pyq(client):
    subject_id = _create_subject(client)
    create_resp = client.post("/api/pyqs", json={
        "subject_id": subject_id, "exam_year": 2023, "marks": 5,
        "question": "Question to be deleted about something."
    })
    pyq_id = create_resp.json()["pyq_id"]
    delete_resp = client.delete(f"/api/pyqs/{pyq_id}")
    assert delete_resp.status_code == 204
    get_resp = client.get(f"/api/pyqs/{pyq_id}")
    assert get_resp.status_code == 404


def test_pyq_invalid_year(client):
    subject_id = _create_subject(client)
    resp = client.post("/api/pyqs", json={
        "subject_id": subject_id, "exam_year": 1800, "marks": 5,
        "question": "Invalid year question."
    })
    assert resp.status_code == 422


def test_pyq_invalid_marks(client):
    subject_id = _create_subject(client)
    resp = client.post("/api/pyqs", json={
        "subject_id": subject_id, "exam_year": 2023, "marks": 0,
        "question": "Zero marks question."
    })
    assert resp.status_code == 422


def test_csv_import(client):
    subject_id = _create_subject(client)
    csv_content = "question,exam_year,marks\nWhat is deadlock?,2023,10\nExplain paging in OS,2022,5\n"
    resp = client.post(
        f"/api/pyqs/import-csv?subject_id={subject_id}",
        files={"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["imported"] == 2
    assert data["failed"] == 0


def test_csv_import_invalid_rows(client):
    subject_id = _create_subject(client)
    csv_content = "question,exam_year,marks\nValid question about OS,2023,10\n,not_a_year,5\n"
    resp = client.post(
        f"/api/pyqs/import-csv?subject_id={subject_id}",
        files={"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["imported"] == 1
    assert data["failed"] == 1
    assert len(data["errors"]) == 1


def test_csv_import_missing_columns(client):
    subject_id = _create_subject(client)
    csv_content = "question,year\nSome question,2023\n"
    resp = client.post(
        f"/api/pyqs/import-csv?subject_id={subject_id}",
        files={"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    assert resp.status_code == 422


def test_csv_import_not_csv(client):
    subject_id = _create_subject(client)
    resp = client.post(
        f"/api/pyqs/import-csv?subject_id={subject_id}",
        files={"file": ("test.txt", io.BytesIO(b"not a csv"), "text/plain")},
    )
    assert resp.status_code == 422
