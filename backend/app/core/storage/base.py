"""File storage interface (local FS now; S3 deferred to Phase 4)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class StoredObject(BaseModel):
    """Metadata for a stored object."""

    key: str
    size: int
    content_type: str


@runtime_checkable
class FileStorage(Protocol):
    """A content-addressed blob store. Keys are opaque, ``/``-delimited paths."""

    async def put(self, key: str, data: bytes, *, content_type: str) -> StoredObject: ...
    async def get(self, key: str) -> bytes: ...
    async def exists(self, key: str) -> bool: ...
    async def delete(self, key: str) -> None: ...
    async def delete_prefix(self, prefix: str) -> int: ...
    async def url_for(
        self, key: str, *, expires_in: int = 300, download_name: str | None = None
    ) -> str: ...
    async def materialize_to_temp(self, key: str, *, suffix: str = "") -> str: ...
