"""Integration tests for the health check endpoint."""


from app.config.constants import APP_VERSION


class TestHealthEndpoint:
    """Tests for GET /health."""

    async def test_health_returns_ok(self, client):
        response = await client.get("/health")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["version"] == APP_VERSION

    async def test_security_headers_are_present(self, client):
        response = await client.get("/health")
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert "Referrer-Policy" in response.headers

    async def test_health_reports_dependency_status(self, client):
        # /health is a real readiness probe: DB is connected in the test harness, so db is True.
        response = await client.get("/health")

        assert response.status_code == 200
        body = response.json()
        assert body["db"] is True
        assert "redis" in body

    async def test_health_returns_503_when_db_is_down(self, client, monkeypatch):
        # A dead database must surface as 503 so a healthcheck / uptime monitor can detect it.
        class _BoomConn:
            async def __aenter__(self):
                raise RuntimeError("db down")

            async def __aexit__(self, *a):
                return False

        class _FakeEngine:
            def connect(self):
                return _BoomConn()

        monkeypatch.setattr("app.db.session.engine", _FakeEngine())
        response = await client.get("/health")

        assert response.status_code == 503
        assert response.json()["db"] is False
