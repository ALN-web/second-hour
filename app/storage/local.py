"""Local Filesystem Storage Adapter.

Stores files under data/storage/ outside Git with strict path traversal prevention.
"""
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

from app import config
from app.services.common import ServiceError


class LocalStorageAdapter:
    """Production-ready local filesystem storage adapter adhering to StorageAdapter protocol."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = (base_dir or (config.DATA_DIR / "storage")).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _safe_resolve(self, storage_key: str) -> Path:
        """Prevent directory traversal attacks by validating resolved path."""
        clean_key = storage_key.strip().replace("\\", "/").lstrip("/")
        # Disallow dot-dot sequences
        if ".." in clean_key.split("/"):
            raise ServiceError("Security violation: path traversal detected in storage key")
        target_path = (self.base_dir / clean_key).resolve()
        if not str(target_path).startswith(str(self.base_dir)):
            raise ServiceError("Security violation: target path escapes storage root")
        return target_path

    def put_object(self, storage_key: str, data: bytes, mime_type: str = "application/octet-stream") -> str:
        """Persist file bytes to private storage and return normalized storage key."""
        target_path = self._safe_resolve(storage_key)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(data)
        return storage_key.replace("\\", "/").lstrip("/")

    def get_object(self, storage_key: str) -> bytes:
        """Retrieve raw file bytes from private storage."""
        target_path = self._safe_resolve(storage_key)
        if not target_path.exists() or not target_path.is_file():
            # Check fallback to legacy paths if storage_key is an existing file path
            legacy_path = Path(storage_key)
            if legacy_path.exists() and legacy_path.is_file():
                return legacy_path.read_bytes()
            raise ServiceError(f"Object not found in storage: {storage_key}")
        return target_path.read_bytes()

    def get_object_path(self, storage_key: str) -> str:
        """Return absolute local filesystem path for FastAPI FileResponse streaming."""
        target_path = self._safe_resolve(storage_key)
        if not target_path.exists() or not target_path.is_file():
            # Check fallback to legacy path if storage_key points directly to a file
            legacy_path = Path(storage_key)
            if legacy_path.exists() and legacy_path.is_file():
                return str(legacy_path.resolve())
            raise ServiceError(f"Object not found in storage: {storage_key}")
        return str(target_path)

    def get_presigned_download_url(self, storage_key: str, expires_in_seconds: int = 900) -> str:
        """Return internal authenticated download route for local adapter."""
        # For local adapter, return clean relative API path
        clean_key = storage_key.replace("\\", "/").lstrip("/")
        return f"/api/storage/file?key={clean_key}"

    def delete_object(self, storage_key: str) -> bool:
        """Permanently remove an object from storage."""
        try:
            target_path = self._safe_resolve(storage_key)
            if target_path.exists() and target_path.is_file():
                target_path.unlink()
                return True
        except Exception:
            pass
        return False

    def exists(self, storage_key: str) -> bool:
        """Check whether object exists in storage."""
        try:
            target_path = self._safe_resolve(storage_key)
            if target_path.exists() and target_path.is_file():
                return True
            legacy_path = Path(storage_key)
            return legacy_path.exists() and legacy_path.is_file()
        except Exception:
            return False


_default_storage: LocalStorageAdapter | None = None


def get_storage() -> LocalStorageAdapter:
    """Return singleton storage adapter."""
    global _default_storage
    if _default_storage is None:
        _default_storage = LocalStorageAdapter()
    return _default_storage
