"""Phase 4 W2: CredentialStore.rotate_all re-wraps blobs under the current KEK."""

from cryptography.fernet import Fernet
from sqlalchemy import select

from app.core.secrets.credential_store import CredentialStore
from app.core.secrets.local import LocalSecretsProvider
from app.models.user import User
from app.models.user_credential import UserCredential
from tests.conftest import TEST_USER_ID


class TestRotateAll:
    async def test_rewraps_old_blobs_to_current_kek(self, db_session):
        old_key = Fernet.generate_key().decode()
        new_key = Fernet.generate_key().decode()

        db_session.add(User(id=TEST_USER_ID, email="u@x.com", hashed_password="x"))
        await db_session.commit()

        # Store a credential under the OLD KEK.
        old_store = CredentialStore(LocalSecretsProvider([old_key]))
        await old_store.put_llm_key(db_session, TEST_USER_ID, "openai", "sk-secret")
        row = (await db_session.execute(select(UserCredential))).scalar_one()
        old_kek_id = row.kek_id

        # Rotate: new KEK prepended (MultiFernet still decrypts the old blob).
        rotating = CredentialStore(LocalSecretsProvider([new_key, old_key]))
        rotated = await rotating.rotate_all(db_session)

        assert rotated == 1
        await db_session.refresh(row)
        assert row.kek_id != old_kek_id  # re-wrapped under the new current KEK
        # And it still decrypts to the original secret.
        assert await rotating.get_llm_key(db_session, TEST_USER_ID, "openai") == "sk-secret"

    async def test_skips_rows_already_on_current_kek(self, db_session):
        key = Fernet.generate_key().decode()
        db_session.add(User(id=TEST_USER_ID, email="u@x.com", hashed_password="x"))
        await db_session.commit()
        store = CredentialStore(LocalSecretsProvider([key]))
        await store.put_llm_key(db_session, TEST_USER_ID, "openai", "sk-secret")

        assert await store.rotate_all(db_session) == 0  # already current → nothing to do
