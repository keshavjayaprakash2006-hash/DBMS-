"""
Cloud and local object storage service.
Supports Supabase Storage for persistent cloud hosting with seamless local disk fallback.
"""
import os
import uuid
import logging
from pathlib import Path
from typing import Optional, Tuple
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def is_supabase_configured() -> bool:
    return bool(settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY)


def _supabase_headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
    }


def _ensure_supabase_bucket():
    """Ensure the target bucket exists in Supabase Storage."""
    if not is_supabase_configured():
        return
    base_url = settings.SUPABASE_URL.rstrip("/")
    bucket = settings.SUPABASE_STORAGE_BUCKET
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                f"{base_url}/storage/v1/bucket/{bucket}",
                headers=_supabase_headers(),
            )
            if resp.status_code == 404:
                create_resp = client.post(
                    f"{base_url}/storage/v1/bucket",
                    headers=_supabase_headers(),
                    json={"id": bucket, "name": bucket, "public": False},
                )
                if create_resp.status_code in (200, 201):
                    logger.info(f"Supabase Storage bucket '{bucket}' created successfully")
                else:
                    logger.warning(f"Could not auto-create bucket '{bucket}': {create_resp.text}")
    except Exception as e:
        logger.warning(f"Could not verify Supabase bucket '{bucket}': {e}")


def save_file(content: bytes, original_filename: str, content_type: Optional[str] = None) -> Tuple[str, str]:
    """
    Save file content to persistent cloud storage (Supabase) or local directory.
    Returns (stored_identifier, local_cached_path).
    """
    ext = Path(original_filename).suffix.lstrip(".").lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"

    # Always write to a local temporary / cached path for immediate text extraction
    upload_dir = Path(settings.UPLOAD_DIRECTORY)
    upload_dir.mkdir(parents=True, exist_ok=True)
    local_path = upload_dir / unique_name
    with open(local_path, "wb") as f:
        f.write(content)

    if is_supabase_configured():
        try:
            _ensure_supabase_bucket()
            base_url = settings.SUPABASE_URL.rstrip("/")
            bucket = settings.SUPABASE_STORAGE_BUCKET
            url = f"{base_url}/storage/v1/object/{bucket}/{unique_name}"
            headers = _supabase_headers()
            if content_type:
                headers["Content-Type"] = content_type

            with httpx.Client(timeout=30.0) as client:
                resp = client.post(url, headers=headers, content=content)
                if resp.status_code in (200, 201):
                    logger.info(f"Uploaded {unique_name} to Supabase bucket '{bucket}'")
                    stored_identifier = f"supabase://{bucket}/{unique_name}"
                    return stored_identifier, str(local_path)
                else:
                    logger.warning(
                        f"Supabase upload failed ({resp.status_code}: {resp.text}). Falling back to local."
                    )
        except Exception as e:
            logger.warning(f"Failed to upload to Supabase: {e}. Falling back to local.")

    return str(local_path), str(local_path)


def get_file_bytes(stored_path: str) -> Optional[bytes]:
    """
    Retrieve file content bytes from cloud storage or local disk.
    Ensures documents are accessible even after Render ephemeral disk restarts.
    """
    # 1. Check if file is stored in Supabase
    if stored_path.startswith("supabase://") and is_supabase_configured():
        parts = stored_path.replace("supabase://", "").split("/", 1)
        if len(parts) == 2:
            bucket, object_name = parts
            base_url = settings.SUPABASE_URL.rstrip("/")
            url = f"{base_url}/storage/v1/object/authenticated/{bucket}/{object_name}"
            try:
                with httpx.Client(timeout=30.0) as client:
                    resp = client.get(url, headers=_supabase_headers())
                    if resp.status_code == 200:
                        return resp.content
                    # Try public endpoint if authenticated failed
                    pub_url = f"{base_url}/storage/v1/object/public/{bucket}/{object_name}"
                    resp2 = client.get(pub_url)
                    if resp2.status_code == 200:
                        return resp2.content
            except Exception as e:
                logger.error(f"Error fetching {stored_path} from Supabase: {e}")

    # 2. Check local filesystem
    local_candidate = Path(stored_path)
    if local_candidate.exists():
        try:
            with open(local_candidate, "rb") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading local file {stored_path}: {e}")

    # 3. Check within UPLOAD_DIRECTORY if stored_path is a basename
    basename = Path(stored_path).name
    alt_local = Path(settings.UPLOAD_DIRECTORY) / basename
    if alt_local.exists():
        try:
            with open(alt_local, "rb") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading alternate local file {alt_local}: {e}")

    return None


def ensure_local_copy(stored_path: str) -> Optional[str]:
    """
    Ensure a local file copy exists for text extractors (PyMuPDF, docx).
    Downloads from Supabase if the ephemeral local file was lost after restart.
    """
    if os.path.exists(stored_path):
        return stored_path

    # If it was stored in Supabase, fetch and cache locally
    content = get_file_bytes(stored_path)
    if content:
        basename = Path(stored_path).name
        upload_dir = Path(settings.UPLOAD_DIRECTORY)
        upload_dir.mkdir(parents=True, exist_ok=True)
        local_path = upload_dir / basename
        with open(local_path, "wb") as f:
            f.write(content)
        return str(local_path)

    return None


def delete_file(stored_path: str):
    """Delete file from cloud storage and local disk."""
    if stored_path.startswith("supabase://") and is_supabase_configured():
        parts = stored_path.replace("supabase://", "").split("/", 1)
        if len(parts) == 2:
            bucket, object_name = parts
            base_url = settings.SUPABASE_URL.rstrip("/")
            url = f"{base_url}/storage/v1/object/{bucket}/{object_name}"
            try:
                with httpx.Client(timeout=15.0) as client:
                    client.delete(url, headers=_supabase_headers())
                    logger.info(f"Deleted {object_name} from Supabase bucket '{bucket}'")
            except Exception as e:
                logger.warning(f"Failed to delete {object_name} from Supabase: {e}")

    # Also remove local cached file
    try:
        if os.path.exists(stored_path):
            os.remove(stored_path)
    except Exception as e:
        logger.warning(f"Could not remove local file {stored_path}: {e}")

    basename = Path(stored_path).name
    alt_local = Path(settings.UPLOAD_DIRECTORY) / basename
    try:
        if alt_local.exists():
            os.remove(alt_local)
    except Exception:
        pass


def check_storage_service() -> dict:
    """Health check for storage provider."""
    if is_supabase_configured():
        base_url = settings.SUPABASE_URL.rstrip("/")
        bucket = settings.SUPABASE_STORAGE_BUCKET
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(
                    f"{base_url}/storage/v1/bucket/{bucket}",
                    headers=_supabase_headers(),
                )
                if resp.status_code in (200, 404):
                    return {
                        "status": "ok",
                        "provider": "supabase",
                        "bucket": bucket,
                        "bucket_exists": resp.status_code == 200,
                    }
                return {
                    "status": "warning",
                    "provider": "supabase",
                    "error": f"Supabase responded with HTTP {resp.status_code}",
                }
        except Exception as e:
            return {
                "status": "error",
                "provider": "supabase",
                "error": str(e),
            }

    # Fallback to local
    upload_dir = Path(settings.UPLOAD_DIRECTORY)
    writable = os.access(upload_dir, os.W_OK) if upload_dir.exists() else True
    return {
        "status": "ok",
        "provider": "local",
        "directory": str(upload_dir),
        "writable": writable,
    }
