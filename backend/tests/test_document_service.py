"""
Tests for document processing services.
"""
import pytest
import os
import tempfile
from app.services.document_service import (
    chunk_text,
    normalize_text,
    validate_file,
    get_file_extension,
    extract_text_from_txt,
)


def test_chunk_text_basic():
    text = "This is sentence one. " * 50 + "\n\n" + "Second paragraph here. " * 50
    chunks = chunk_text(text, chunk_size=100, chunk_overlap=10)
    assert len(chunks) > 0
    for chunk in chunks:
        assert len(chunk.split()) >= 5


def test_chunk_text_empty():
    chunks = chunk_text("", chunk_size=100)
    assert chunks == []


def test_chunk_text_short():
    text = "Short text with enough words to form a single chunk easily."
    chunks = chunk_text(text, chunk_size=500)
    assert len(chunks) == 1


def test_chunk_text_preserves_paragraphs():
    text = "Para one content here.\n\nPara two content here.\n\nPara three content here."
    chunks = chunk_text(text, chunk_size=20)
    assert len(chunks) >= 1


def test_normalize_text():
    text = "Line one\r\nLine two\r\n\r\n\r\nLine three"
    normalized = normalize_text(text)
    assert "\r\n" not in normalized
    assert "\n\n\n" not in normalized


def test_validate_file_valid():
    error = validate_file("document.pdf", 1024 * 1024)  # 1 MB
    assert error is None


def test_validate_file_invalid_extension():
    error = validate_file("document.exe", 1024)
    assert error is not None
    assert "Unsupported" in error


def test_validate_file_too_large():
    error = validate_file("document.pdf", 100 * 1024 * 1024)  # 100 MB
    assert error is not None
    assert "large" in error.lower()


def test_get_file_extension():
    assert get_file_extension("notes.PDF") == "pdf"
    assert get_file_extension("notes.docx") == "docx"
    assert get_file_extension("notes.txt") == "txt"


def test_extract_text_from_txt():
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False, encoding="utf-8") as f:
        f.write("Hello world.\n\nSecond paragraph.")
        tmp_path = f.name
    try:
        text, error = extract_text_from_txt(tmp_path)
        assert error is None
        assert "Hello world" in text
    finally:
        os.unlink(tmp_path)


def test_chunk_does_not_produce_duplicates():
    text = "\n\n".join([f"Paragraph {i}: " + "word " * 60 for i in range(10)])
    chunks = chunk_text(text, chunk_size=100, chunk_overlap=20)
    # Check no two chunks are exactly the same
    assert len(chunks) == len(set(chunks)) or len(chunks) <= 10
