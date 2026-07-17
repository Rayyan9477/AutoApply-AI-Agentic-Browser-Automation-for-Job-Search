"""Platform session import: persist an encrypted storage_state so run_apply can reuse the login.

The import endpoint is the only write path into the ``platform_cookies`` credential + the
``platform_sessions`` metadata row that ``run_apply`` reads at prerequisite-check time.
"""

from app.core.secrets.credential_store import CredentialStore

API = "/api/v1/platform-sessions"
STORAGE = {
    "cookies": [{"name": "li_at", "value": "SECRET-COOKIE", "domain": ".linkedin.com"}],
    "origins": [],
}


class TestImport:
    async def test_import_persists_and_lists(self, client, db_session, current_user):
        r = await client.post(f"{API}/", json={"platform": "linkedin", "storage_state": STORAGE})
        assert r.status_code == 201, r.text
        assert r.json()["platform"] == "linkedin"
        assert r.json()["connected"] is True

        lst = await client.get(f"{API}/")
        assert lst.status_code == 200
        assert "linkedin" in [s["platform"] for s in lst.json()]

        # The raw cookie value must never be echoed back by the API.
        assert "SECRET-COOKIE" not in lst.text
        assert "SECRET-COOKIE" not in r.text

        # run_apply's read path can decrypt exactly what was imported.
        loaded = await CredentialStore().load_session_cookies(
            db_session, current_user.id, "linkedin"
        )
        assert loaded == STORAGE

    async def test_reimport_upserts_without_duplicate(self, client, current_user):
        await client.post(f"{API}/", json={"platform": "linkedin", "storage_state": STORAGE})
        await client.post(f"{API}/", json={"platform": "linkedin", "storage_state": STORAGE})
        rows = (await client.get(f"{API}/")).json()
        assert sum(1 for s in rows if s["platform"] == "linkedin") == 1

    async def test_rejects_unknown_platform(self, client):
        r = await client.post(f"{API}/", json={"platform": "monster", "storage_state": STORAGE})
        assert r.status_code == 422

    async def test_rejects_storage_state_without_cookies(self, client):
        r = await client.post(f"{API}/", json={"platform": "linkedin", "storage_state": {"origins": []}})
        assert r.status_code == 422


class TestDelete:
    async def test_delete_removes_session(self, client, db_session, current_user):
        await client.post(f"{API}/", json={"platform": "linkedin", "storage_state": STORAGE})
        r = await client.delete(f"{API}/linkedin")
        assert r.status_code == 204
        assert (await client.get(f"{API}/")).json() == []
        loaded = await CredentialStore().load_session_cookies(
            db_session, current_user.id, "linkedin"
        )
        assert loaded is None

    async def test_delete_missing_is_404(self, client):
        r = await client.delete(f"{API}/linkedin")
        assert r.status_code == 404
