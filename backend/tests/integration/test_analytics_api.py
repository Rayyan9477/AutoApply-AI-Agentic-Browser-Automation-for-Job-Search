"""Integration tests for the Analytics API routes."""



API_PREFIX = "/api/v1/analytics"


class TestDashboard:
    """Tests for GET /api/v1/analytics/dashboard."""

    async def test_dashboard_empty_db(self, client):
        response = await client.get(f"{API_PREFIX}/dashboard")

        assert response.status_code == 200
        body = response.json()
        assert body["total_jobs_found"] == 0
        assert body["total_applications"] == 0
        assert body["applications_pending"] == 0
        assert body["applications_applied"] == 0
        assert body["applications_interview"] == 0
        assert body["applications_rejected"] == 0
        assert body["applications_offer"] == 0
        assert body["avg_ats_score"] == 0.0
        assert body["total_llm_cost_usd"] == 0.0


class TestFunnel:
    """Tests for GET /api/v1/analytics/funnel."""

    async def test_funnel_returns_all_stages(self, client):
        response = await client.get(f"{API_PREFIX}/funnel")

        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, list)
        assert len(body) == 9  # 9 funnel stages defined in _FUNNEL_STAGES

        stages = [entry["stage"] for entry in body]
        assert "queued" in stages
        assert "approved" in stages
        assert "applied" in stages
        assert "interview" in stages
        assert "offer" in stages
        assert "rejected" in stages

        # All counts should be zero on empty DB
        for entry in body:
            assert entry["count"] == 0


class TestATSScores:
    """Tests for GET /api/v1/analytics/ats-scores."""

    async def test_ats_scores_returns_distribution_buckets(self, client):
        response = await client.get(f"{API_PREFIX}/ats-scores")

        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, list)
        assert len(body) == 5  # 5 score range buckets

        labels = [bucket["range_label"] for bucket in body]
        assert "0-20" in labels
        assert "20-40" in labels
        assert "40-60" in labels
        assert "60-80" in labels
        assert "80-100" in labels

        for bucket in body:
            assert bucket["count"] == 0


class TestLLMUsage:
    """Tests for GET /api/v1/analytics/llm-usage."""

    async def test_llm_usage_returns_empty_list(self, client):
        response = await client.get(f"{API_PREFIX}/llm-usage")

        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, list)
        assert len(body) == 0


class TestTimeline:
    """Tests for GET /api/v1/analytics/timeline."""

    async def test_timeline_returns_empty_list(self, client):
        response = await client.get(f"{API_PREFIX}/timeline")

        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, list)
        assert len(body) == 0
