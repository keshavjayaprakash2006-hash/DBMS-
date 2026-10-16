"""
Document processing service: text extraction, chunking, and storage.
Supports PDF, DOCX, TXT, Markdown.
"""
import os
import re
import uuid
import logging
from pathlib import Path
from typing import List, Tuple, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


# ─── Text Extraction ──────────────────────────────────────────────────────────

def extract_text_from_pdf(file_path: str) -> Tuple[str, Optional[str]]:
    """Extract text from PDF. Returns (text, error)."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(file_path)
        pages_text = []
        for page in doc:
            text = page.get_text("text")
            if text.strip():
                pages_text.append(text)
        doc.close()
        full_text = "\n\n".join(pages_text)
        if not full_text.strip():
            return "", "PDF appears to contain no extractable text (may be image-based/scanned). OCR is required for such documents."
        return full_text, None
    except Exception as e:
        return "", f"PDF extraction failed: {e}"


def extract_text_from_docx(file_path: str) -> Tuple[str, Optional[str]]:
    """Extract text from DOCX."""
    try:
        from docx import Document
        doc = Document(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs), None
    except Exception as e:
        return "", f"DOCX extraction failed: {e}"


def extract_text_from_txt(file_path: str) -> Tuple[str, Optional[str]]:
    """Extract text from plain text or Markdown file."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read(), None
    except Exception as e:
        return "", f"Text file reading failed: {e}"


def extract_text(file_path: str, file_type: str) -> Tuple[str, Optional[str]]:
    """Route to the correct extractor based on file type."""
    ft = file_type.lower()
    if ft == "pdf":
        return extract_text_from_pdf(file_path)
    elif ft in ("docx", "doc"):
        return extract_text_from_docx(file_path)
    elif ft in ("txt", "md", "markdown", "text"):
        return extract_text_from_txt(file_path)
    else:
        return "", f"Unsupported file type: {file_type}"


# ─── Text Normalization ───────────────────────────────────────────────────────

def normalize_text(text: str) -> str:
    """Normalize whitespace while preserving paragraph boundaries."""
    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse multiple blank lines to a single blank line
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Collapse multiple spaces/tabs into a single space within a line
    lines = []
    for line in text.split("\n"):
        lines.append(re.sub(r"[ \t]+", " ", line).strip())
    return "\n".join(lines).strip()


# ─── Text Chunking ────────────────────────────────────────────────────────────

def chunk_text(
    text: str,
    chunk_size: int = None,
    chunk_overlap: int = None,
) -> List[str]:
    """
    Split text into meaningful chunks. Tries to preserve paragraph boundaries.
    Falls back to word-count-based splitting when paragraphs are too large.
    """
    if chunk_size is None:
        chunk_size = settings.CHUNK_SIZE
    if chunk_overlap is None:
        chunk_overlap = settings.CHUNK_OVERLAP

    # Split into paragraphs first
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks = []
    current_chunk_words = []
    current_word_count = 0

    for para in paragraphs:
        para_words = para.split()
        para_word_count = len(para_words)

        # If a single paragraph is huge, split it into sub-chunks
        if para_word_count > chunk_size * 1.5:
            # Flush current buffer first
            if current_chunk_words:
                chunks.append(" ".join(current_chunk_words))
                current_chunk_words = []
                current_word_count = 0
            # Split the large paragraph into word-based chunks
            for i in range(0, para_word_count, chunk_size - chunk_overlap):
                sub = para_words[i: i + chunk_size]
                if sub:
                    chunks.append(" ".join(sub))
            continue

        # If adding this paragraph would exceed chunk_size, flush and start new chunk
        if current_word_count + para_word_count > chunk_size and current_chunk_words:
            chunks.append(" ".join(current_chunk_words))
            # Apply overlap: carry forward last chunk_overlap words
            if chunk_overlap > 0:
                overlap_words = current_chunk_words[-chunk_overlap:]
                current_chunk_words = overlap_words + para_words
                current_word_count = len(current_chunk_words)
            else:
                current_chunk_words = para_words
                current_word_count = para_word_count
        else:
            current_chunk_words.extend(para_words)
            current_word_count += para_word_count

    # Flush remaining
    if current_chunk_words:
        chunks.append(" ".join(current_chunk_words))

    # Filter empty chunks
    return [c for c in chunks if len(c.split()) >= 5]


# ─── File Handling ────────────────────────────────────────────────────────────

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "md", "markdown"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/markdown",
}


def get_file_extension(filename: str) -> str:
    return Path(filename).suffix.lstrip(".").lower()


def validate_file(filename: str, file_size: int) -> Optional[str]:
    """Return error message if file is invalid, else None."""
    ext = get_file_extension(filename)
    if ext not in ALLOWED_EXTENSIONS:
        return f"Unsupported file type '.{ext}'. Supported: {', '.join(ALLOWED_EXTENSIONS)}"
    if file_size > settings.max_upload_bytes:
        return f"File too large ({file_size // (1024*1024)} MB). Max: {settings.MAX_UPLOAD_SIZE_MB} MB"
    return None


def generate_stored_filename(original_filename: str) -> str:
    """Generate a safe, unique internal filename."""
    ext = get_file_extension(original_filename)
    return f"{uuid.uuid4().hex}.{ext}"


def save_uploaded_file(content: bytes, stored_filename: str) -> str:
    """Save file to the uploads directory. Returns full path."""
    upload_dir = Path(settings.UPLOAD_DIRECTORY)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / stored_filename
    with open(file_path, "wb") as f:
        f.write(content)
    return str(file_path)
