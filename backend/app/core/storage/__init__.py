"""File storage abstraction: local FS or S3-compatible (``STORAGE__PROVIDER=s3``) behind one
interface."""

from app.core.storage.base import FileStorage, StoredObject
from app.core.storage.factory import get_storage
from app.core.storage.service import StorageService

__all__ = ["FileStorage", "StorageService", "StoredObject", "get_storage"]
