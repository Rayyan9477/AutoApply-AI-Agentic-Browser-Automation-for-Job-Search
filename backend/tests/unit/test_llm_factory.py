"""Phase 1.4: per-user BYO LLM client resolution."""

from cryptography.fernet import Fernet

from app.core.llm.client import LLMClient
from app.core.llm.factory import build_llm_client_for_user
from app.core.secrets import CredentialStore
from app.core.secrets.local import LocalSecretsProvider
from app.models.user import User
from app.models.user_llm_config import UserLLMConfig
from tests.conftest import TEST_USER_ID


def _store() -> CredentialStore:
    return CredentialStore(LocalSecretsProvider([Fernet.generate_key().decode()]))


class TestBuildLLMClientForUser:
    async def test_without_key_returns_global_client(self, db_session):
        client = await build_llm_client_for_user(db_session, TEST_USER_ID, _store())
        assert isinstance(client, LLMClient)
        assert client._credentials is None

    async def test_with_key_binds_user_credentials(self, db_session):
        store = _store()
        db_session.add(User(id=TEST_USER_ID, email="u@x.com", hashed_password="x"))
        db_session.add(
            UserLLMConfig(user_id=TEST_USER_ID, preferred_provider="openai", default_model="gpt-4o")
        )
        await db_session.commit()
        await store.put_llm_key(db_session, TEST_USER_ID, "openai", "sk-user-key")

        client = await build_llm_client_for_user(db_session, TEST_USER_ID, store)

        assert client._credentials is not None
        assert client._credentials.api_key == "sk-user-key"
        assert client._credentials.provider == "openai"
        # BYO-key uses only the user's model — no cross-provider fallback chain.
        assert client._get_model_chain(None) == ["gpt-4o"]
