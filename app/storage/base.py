"""Reusable Storage Adapter Protocol.

Defines the contract for storing and retrieving files outside of PostgreSQL.
"""
from __future__ import annotations

from typing import Protocol


class StorageAdapter(Protocol):
    """Storage abstraction protocol matching Second Hour architecture."""

    def put_object(self, storage_key: str, data: bytes, mime_type: str = "application/octet-stream") -> str:
        """Persist file bytes to private storage and return storage key."""
        ...

    def get_object(self, storage_key: str) -> bytes:
        """Retrieve raw file bytes from private storage."""
        ...

    def get_object_path(self, storage_key: str) -> str:
        """Return absolute local filesystem path for internal streaming/serving."""
        ...

    def get_presigned_download_url(self, storage_key: str, expires_in_seconds: int = 900) -> str:
        """Generate a short-lived download URL or internal signed token."""
        ...

    def delete_object(self, storage_key: str) -> bool:
        """Permanently remove an object from storage."""
        ...

    def exists(self, storage_key: str) -> bool:
        """Check whether object exists in storage."""
        ...
