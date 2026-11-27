"""Storage module export."""
from app.storage.base import StorageAdapter
from app.storage.local import LocalStorageAdapter, get_storage

__all__ = ["StorageAdapter", "LocalStorageAdapter", "get_storage"]
