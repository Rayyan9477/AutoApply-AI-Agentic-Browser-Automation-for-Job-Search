"""Browser automation: AI-driven agents and platform integrations.

Platform session persistence lives in the encrypted CredentialStore
(``app/core/secrets/credential_store.py``) via the platform-sessions API.
"""

from app.core.automation.agent import BrowserAgent

__all__ = ["BrowserAgent"]
