"""Small pure-unit coverage: ATS-optimize prompt builder + secrets factory/provider."""

from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet

from app.core.llm.prompts.ats_optimize import (
    ATS_OPTIMIZE_SYSTEM_PROMPT,
    render_ats_optimize_prompt,
)
from app.core.secrets.base import EncryptedBlob
from app.core.secrets.local import LocalSecretsProvider


class TestAtsOptimizePrompt:
    def test_embeds_all_inputs(self):
        prompt = render_ats_optimize_prompt(
            resume_text="Jane Doe — Python dev",
            job_description="Seeking a senior Python engineer",
            score_breakdown={"overall": 0.62, "missing_skills": ["docker"]},
            suggestions=["Add docker experience", "Mirror the job title"],
        )
        assert "Jane Doe — Python dev" in prompt
        assert "senior Python engineer" in prompt
        assert "docker" in prompt  # score_breakdown serialized as JSON
        assert "- Add docker experience" in prompt  # suggestions bulleted
        assert "- Mirror the job title" in prompt
        assert prompt.rstrip().endswith("JSON object.")

    def test_system_prompt_enforces_no_fabrication(self):
        assert "NEVER fabricate" in ATS_OPTIMIZE_SYSTEM_PROMPT

    def test_handles_empty_suggestions(self):
        prompt = render_ats_optimize_prompt("r", "j", {}, [])
        assert "IMPROVEMENT SUGGESTIONS:" in prompt  # section present even when empty


class TestSecretsFactory:
    def test_selects_local_provider(self):
        from app.core.secrets import factory

        factory.get_secrets_provider.cache_clear()
        with patch("app.core.secrets.factory.get_settings") as gs:
            gs.return_value.secrets.provider = "local"
            gs.return_value.secrets.app_keys = f"{Fernet.generate_key().decode()}"
            provider = factory.get_secrets_provider()
        assert isinstance(provider, LocalSecretsProvider)
        factory.get_secrets_provider.cache_clear()

    def test_unknown_provider_raises(self):
        from app.core.secrets import factory

        factory.get_secrets_provider.cache_clear()
        with patch("app.core.secrets.factory.get_settings") as gs:
            gs.return_value.secrets.provider = "vault"
            with pytest.raises(ValueError, match="Unknown secrets provider"):
                factory.get_secrets_provider()
        factory.get_secrets_provider.cache_clear()


class TestLocalSecretsProvider:
    async def test_encrypt_decrypt_roundtrip(self):
        provider = LocalSecretsProvider([Fernet.generate_key().decode()])
        blob = await provider.encrypt(b"sk-secret", context={"user_id": "u1"})
        assert isinstance(blob, EncryptedBlob)
        assert blob.ciphertext != "sk-secret"  # actually encrypted
        assert await provider.decrypt(blob, context={"user_id": "u1"}) == b"sk-secret"

    def test_requires_at_least_one_key(self):
        with pytest.raises(ValueError, match="at least one key"):
            LocalSecretsProvider([])

    async def test_multifernet_rotation_decrypts_old_blob(self):
        old_key = Fernet.generate_key().decode()
        new_key = Fernet.generate_key().decode()
        old = LocalSecretsProvider([old_key])
        blob = await old.encrypt(b"token", context={})
        # New KEK prepended (rotation): MultiFernet still decrypts the old-key blob.
        rotated = LocalSecretsProvider([new_key, old_key])
        assert await rotated.decrypt(blob, context={}) == b"token"
        assert rotated.current_kek_id != old.current_kek_id

    async def test_rotate_reencrypts_under_current_kek(self):
        old_key = Fernet.generate_key().decode()
        new_key = Fernet.generate_key().decode()
        old = LocalSecretsProvider([old_key])
        blob = await old.encrypt(b"token", context={})
        rotated_provider = LocalSecretsProvider([new_key, old_key])
        new_blob = await rotated_provider.rotate(blob, context={})
        assert new_blob.kek_id == rotated_provider.current_kek_id
        assert await rotated_provider.decrypt(new_blob, context={}) == b"token"
