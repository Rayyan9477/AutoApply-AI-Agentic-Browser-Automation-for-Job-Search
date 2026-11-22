"""AWS KMS secrets provider — unimplemented interface stub.

The shipped envelope-encryption path is the Fernet provider (``local.py``); this stub
only reserves the ``provider=kms`` factory slot for a future KMS-backed implementation.
"""

from __future__ import annotations

from app.core.secrets.base import EncryptedBlob, SecretsProvider

_DEFERRED = "KMS secrets provider is not implemented; use SECRETS__PROVIDER=local (Fernet)"


class KmsSecretsProvider(SecretsProvider):
    """Placeholder so the factory can select ``provider=kms`` once a KMS backend lands."""

    @property
    def current_kek_id(self) -> str:
        raise NotImplementedError(_DEFERRED)

    async def encrypt(self, plaintext: bytes, *, context: dict[str, str]) -> EncryptedBlob:
        raise NotImplementedError(_DEFERRED)

    async def decrypt(self, blob: EncryptedBlob, *, context: dict[str, str]) -> bytes:
        raise NotImplementedError(_DEFERRED)

    async def rotate(self, blob: EncryptedBlob, *, context: dict[str, str]) -> EncryptedBlob:
        raise NotImplementedError(_DEFERRED)
