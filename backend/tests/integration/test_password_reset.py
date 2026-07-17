"""Password-reset flow: forgot-password (uniform, no enumeration) → reset-password.

The mailer is monkeypatched to capture the reset link the service would send, so the tests
can drive the full round-trip without a real email transport.
"""

from urllib.parse import parse_qs, urlparse

import pytest

from app.services import mailer

API = "/api/v1/auth"
CREDS = {"email": "reset@x.com", "password": "password123"}
FORM = {"username": "reset@x.com", "password": "password123"}


@pytest.fixture
def captured_links(monkeypatch):
    """Capture reset links the service would email (a list of URLs)."""
    links: list[str] = []

    async def _capture(to: str, reset_link: str) -> None:
        links.append(reset_link)

    monkeypatch.setattr(mailer, "send_password_reset_email", _capture)
    return links


def _token_from_link(link: str) -> str:
    return parse_qs(urlparse(link).query)["token"][0]


class TestForgotPassword:
    async def test_unknown_email_returns_200_and_sends_nothing(self, anon_client, captured_links):
        r = await anon_client.post(f"{API}/forgot-password", json={"email": "nobody@x.com"})
        assert r.status_code == 200, r.text
        assert "message" in r.json()
        assert captured_links == []  # no enumeration: nothing emailed for an unknown address

    async def test_known_email_returns_200_and_emails_a_link(self, anon_client, captured_links):
        await anon_client.post(f"{API}/register", json=CREDS)
        r = await anon_client.post(f"{API}/forgot-password", json={"email": CREDS["email"]})
        assert r.status_code == 200, r.text
        assert len(captured_links) == 1
        assert "token=" in captured_links[0]

    async def test_response_identical_for_known_and_unknown(self, anon_client, captured_links):
        await anon_client.post(f"{API}/register", json=CREDS)
        known = await anon_client.post(f"{API}/forgot-password", json={"email": CREDS["email"]})
        unknown = await anon_client.post(f"{API}/forgot-password", json={"email": "ghost@x.com"})
        assert known.status_code == unknown.status_code == 200
        assert known.json() == unknown.json()  # identical body → no enumeration


class TestResetPassword:
    async def _issue_token(self, client, captured_links) -> str:
        await client.post(f"{API}/register", json=CREDS)
        await client.post(f"{API}/forgot-password", json={"email": CREDS["email"]})
        return _token_from_link(captured_links[-1])

    async def test_valid_token_changes_password(self, anon_client, captured_links):
        token = await self._issue_token(anon_client, captured_links)
        r = await anon_client.post(
            f"{API}/reset-password", json={"token": token, "password": "newpassword456"}
        )
        assert r.status_code == 200, r.text
        # Old password no longer works; the new one does.
        assert (await anon_client.post(f"{API}/login", data=FORM)).status_code == 401
        r2 = await anon_client.post(
            f"{API}/login", data={"username": CREDS["email"], "password": "newpassword456"}
        )
        assert r2.status_code == 200, r2.text

    async def test_invalid_token_rejected(self, anon_client):
        r = await anon_client.post(
            f"{API}/reset-password",
            json={"token": "not-a-real-token-value-000000", "password": "newpassword456"},
        )
        assert r.status_code == 401

    async def test_token_is_single_use(self, anon_client, captured_links):
        token = await self._issue_token(anon_client, captured_links)
        assert (
            await anon_client.post(
                f"{API}/reset-password", json={"token": token, "password": "newpassword456"}
            )
        ).status_code == 200
        r = await anon_client.post(
            f"{API}/reset-password", json={"token": token, "password": "another789xyz"}
        )
        assert r.status_code == 401

    async def test_reset_revokes_existing_sessions(self, anon_client, captured_links):
        await anon_client.post(f"{API}/register", json=CREDS)
        await anon_client.post(f"{API}/login", data=FORM)  # establishes a refresh cookie
        await anon_client.post(f"{API}/forgot-password", json={"email": CREDS["email"]})
        token = _token_from_link(captured_links[-1])
        assert (
            await anon_client.post(
                f"{API}/reset-password", json={"token": token, "password": "newpassword456"}
            )
        ).status_code == 200
        # The pre-reset refresh session must no longer rotate.
        assert (await anon_client.post(f"{API}/refresh")).status_code == 401
