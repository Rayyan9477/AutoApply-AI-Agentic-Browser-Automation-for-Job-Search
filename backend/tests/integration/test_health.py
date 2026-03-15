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
