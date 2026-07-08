"""Phase 4 W1: S3-compatible storage (S3FileStorage) round-trip against a moto S3 server.

Skips when the [aws] extra (aioboto3) or moto aren't installed, so the base test env stays
dependency-light; CI installs them and runs these.
"""

from pathlib import Path

import pytest

pytest.importorskip("aioboto3")
pytest.importorskip("moto")

import boto3  # noqa: E402
from moto.server import ThreadedMotoServer  # noqa: E402

from app.core.storage.s3 import S3FileStorage  # noqa: E402
from app.core.storage.service import StorageService  # noqa: E402

_BUCKET = "test-bucket"


@pytest.fixture(scope="module")
def moto_s3():
    server = ThreadedMotoServer(ip_address="127.0.0.1", port=0)
    server.start()
    _, port = server.get_host_and_port()
    endpoint = f"http://127.0.0.1:{port}"
    boto3.client(
        "s3", endpoint_url=endpoint, region_name="us-east-1",
        aws_access_key_id="test", aws_secret_access_key="test",
    ).create_bucket(Bucket=_BUCKET)
    yield endpoint
    server.stop()


def _store(endpoint: str) -> S3FileStorage:
    return S3FileStorage(
        bucket=_BUCKET, region="us-east-1", endpoint_url=endpoint,
        access_key_id="test", secret_access_key="test",
    )


class TestS3FileStorage:
    async def test_put_get_exists_delete_roundtrip(self, moto_s3):
        s = _store(moto_s3)
        meta = await s.put("users/u1/a.txt", b"hello", content_type="text/plain")
        assert meta.key == "users/u1/a.txt" and meta.size == 5
        assert await s.exists("users/u1/a.txt") is True
        assert await s.get("users/u1/a.txt") == b"hello"
        await s.delete("users/u1/a.txt")
        assert await s.exists("users/u1/a.txt") is False

    async def test_delete_prefix_purges_tree(self, moto_s3):
        s = _store(moto_s3)
        for i in range(3):
            await s.put(f"users/u2/resumes/{i}.txt", b"x", content_type="text/plain")
        await s.put("users/u2/keep.txt", b"x", content_type="text/plain")
        assert await s.delete_prefix("users/u2/resumes") == 3
        assert await s.exists("users/u2/keep.txt") is True

    async def test_presigned_url_for_download(self, moto_s3):
        s = _store(moto_s3)
        await s.put("users/u3/a.pdf", b"PDF", content_type="application/pdf")
        url = await s.url_for("users/u3/a.pdf", expires_in=60, download_name="resume.pdf")
        assert "users/u3/a.pdf" in url
        assert "X-Amz-Signature" in url or "Signature" in url

    async def test_materialize_to_temp(self, moto_s3):
        s = _store(moto_s3)
        await s.put("users/u4/r.pdf", b"DATA", content_type="application/pdf")
        tmp = await s.materialize_to_temp("users/u4/r.pdf", suffix=".pdf")
        assert tmp.endswith(".pdf") and Path(tmp).read_bytes() == b"DATA"

    async def test_storage_service_enforces_tenant_prefix(self, moto_s3):
        svc = StorageService(_store(moto_s3), "u5")
        await svc.put("users/u5/ok.txt", b"x", content_type="text/plain")  # own prefix OK
        with pytest.raises(PermissionError):
            await svc.put("users/other/x.txt", b"x", content_type="text/plain")
