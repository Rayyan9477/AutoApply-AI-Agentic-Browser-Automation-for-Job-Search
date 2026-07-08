"""Local FileStorage + tenant-scoped StorageService + key builders + factory.

Covers the security-relevant paths: per-tenant key confinement (anti-IDOR), path-traversal
rejection, and HMAC-signed URLs. No real cloud — local FS via tmp_path only.
"""

from unittest.mock import patch

import pytest

from app.core.storage import keys
from app.core.storage.base import FileStorage, StoredObject
from app.core.storage.local import LocalFileStorage
from app.core.storage.service import StorageService

SECRET = "url-signing-secret-for-tests"


def _storage(tmp_path) -> LocalFileStorage:
    return LocalFileStorage(str(tmp_path), SECRET)


class TestLocalFileStorage:
    async def test_put_get_roundtrip(self, tmp_path):
        store = _storage(tmp_path)
        meta = await store.put("users/u1/a.txt", b"hello", content_type="text/plain")
        assert isinstance(meta, StoredObject)
        assert meta.key == "users/u1/a.txt" and meta.size == 5
        assert meta.content_type == "text/plain"
        assert await store.get("users/u1/a.txt") == b"hello"

    async def test_put_creates_nested_dirs(self, tmp_path):
        store = _storage(tmp_path)
        await store.put("users/u1/resumes/deep/r.pdf", b"x", content_type="application/pdf")
        assert (tmp_path / "users" / "u1" / "resumes" / "deep" / "r.pdf").exists()

    async def test_exists_and_delete(self, tmp_path):
        store = _storage(tmp_path)
        assert await store.exists("users/u1/a.txt") is False
        await store.put("users/u1/a.txt", b"x", content_type="text/plain")
        assert await store.exists("users/u1/a.txt") is True
        await store.delete("users/u1/a.txt")
        assert await store.exists("users/u1/a.txt") is False
        await store.delete("users/u1/a.txt")  # deleting a missing key is a no-op

    async def test_delete_prefix_counts_files(self, tmp_path):
        store = _storage(tmp_path)
        for i in range(3):
            await store.put(f"users/u1/r/{i}.txt", b"x", content_type="text/plain")
        await store.put("users/u1/keep.txt", b"x", content_type="text/plain")
        assert await store.delete_prefix("users/u1/r") == 3
        assert await store.exists("users/u1/keep.txt") is True

    async def test_delete_prefix_missing_returns_zero(self, tmp_path):
        assert await _storage(tmp_path).delete_prefix("users/u1/nope") == 0

    async def test_path_traversal_is_rejected(self, tmp_path):
        store = _storage(tmp_path)
        with pytest.raises(ValueError, match="path traversal"):
            await store.put("../escape.txt", b"x", content_type="text/plain")
        with pytest.raises(ValueError, match="path traversal"):
            await store.get("users/../../etc/passwd")

    async def test_materialize_to_temp(self, tmp_path):
        store = _storage(tmp_path)
        await store.put("users/u1/r.pdf", b"PDFDATA", content_type="application/pdf")
        tmp = await store.materialize_to_temp("users/u1/r.pdf", suffix=".pdf")
        assert tmp.endswith(".pdf")
        from pathlib import Path

        assert Path(tmp).read_bytes() == b"PDFDATA"

    async def test_url_for_is_signed_and_deterministic(self, tmp_path):
        store = _storage(tmp_path)
        with patch("app.core.storage.local.time.time", return_value=1000):
            url = await store.url_for("users/u1/a.txt", expires_in=300)
        assert url.startswith("/api/v1/files/users/u1/a.txt?expires=1300&sig=")
        # the signature is an HMAC over key:expiry with the configured secret
        import hashlib
        import hmac

        expected = hmac.new(SECRET.encode(), b"users/u1/a.txt:1300", hashlib.sha256).hexdigest()
        assert url.endswith(expected)

    async def test_url_signature_changes_with_key(self, tmp_path):
        store = _storage(tmp_path)
        with patch("app.core.storage.local.time.time", return_value=1000):
            u1 = await store.url_for("users/u1/a.txt")
            u2 = await store.url_for("users/u1/b.txt")
        assert u1.split("sig=")[1] != u2.split("sig=")[1]

    def test_satisfies_filestorage_protocol(self, tmp_path):
        assert isinstance(_storage(tmp_path), FileStorage)


class TestStorageServiceTenantScoping:
    async def test_allows_own_prefix(self, tmp_path):
        svc = StorageService(_storage(tmp_path), "u1")
        meta = await svc.put("users/u1/resumes/r.pdf", b"x", content_type="application/pdf")
        assert meta.key == "users/u1/resumes/r.pdf"
        assert await svc.get("users/u1/resumes/r.pdf") == b"x"

    async def test_rejects_other_tenant_key_on_every_op(self, tmp_path):
        svc = StorageService(_storage(tmp_path), "u1")
        other = "users/u2/resumes/r.pdf"
        with pytest.raises(PermissionError):
            await svc.put(other, b"x", content_type="application/pdf")
        with pytest.raises(PermissionError):
            await svc.get(other)
        with pytest.raises(PermissionError):
            await svc.delete(other)
        with pytest.raises(PermissionError):
            await svc.url_for(other)
        with pytest.raises(PermissionError):
            await svc.materialize_to_temp(other)

    async def test_rejects_prefix_confusion_attack(self, tmp_path):
        # "users/u12..." must NOT be accepted by a service scoped to "users/u1".
        svc = StorageService(_storage(tmp_path), "u1")
        with pytest.raises(PermissionError):
            await svc.get("users/u12/secret.pdf")

    async def test_allows_exact_prefix_itself(self, tmp_path):
        svc = StorageService(_storage(tmp_path), "u1")
        # the bare prefix is permitted (e.g. delete_prefix-style ops route through _check)
        with pytest.raises(FileNotFoundError):  # passes _check, then misses on disk
            await svc.get("users/u1")


class TestKeyBuilders:
    def test_all_keys_are_under_user_prefix(self):
        uid = "abc"
        assert keys.user_prefix(uid) == "users/abc"
        assert keys.resume_key(uid, "r1", "pdf") == "users/abc/resumes/r1.pdf"
        assert keys.upload_key(uid, "up1", "docx") == "users/abc/uploads/up1.docx"
        assert keys.cover_letter_key(uid, "app1", "pdf") == "users/abc/cover_letters/app1.pdf"
        assert keys.screenshot_key(uid, "app1", "s.png") == "users/abc/screenshots/app1/s.png"
        assert keys.trajectory_key(uid, "run1") == "users/abc/trajectories/run1.json"
        for builder in (keys.resume_key, keys.upload_key, keys.cover_letter_key):
            assert builder(uid, "x", "y").startswith(keys.user_prefix(uid) + "/")


class TestStorageFactory:
    def test_selects_local_provider(self, tmp_path):
        from app.core.storage import factory

        factory.get_storage.cache_clear()
        with patch("app.core.storage.factory.get_settings") as gs:
            cfg = gs.return_value.storage
            cfg.provider = "local"
            cfg.local_root = str(tmp_path)
            cfg.url_signing_secret.get_secret_value.return_value = SECRET
            store = factory.get_storage()
        assert isinstance(store, LocalFileStorage)
        factory.get_storage.cache_clear()

    def test_unknown_provider_raises(self, tmp_path):
        from app.core.storage import factory

        factory.get_storage.cache_clear()
        with patch("app.core.storage.factory.get_settings") as gs:
            gs.return_value.storage.provider = "azure"
            with pytest.raises(ValueError, match="Unknown storage provider"):
                factory.get_storage()
        factory.get_storage.cache_clear()
