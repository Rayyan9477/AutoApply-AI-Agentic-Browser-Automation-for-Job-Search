"""Phase 3.6: LLM usage persistence (record_usage + purpose coercion)."""

from sqlalchemy import select

from app.core.llm.client import LLMResponse
from app.core.llm.usage_tracker import _coerce_purpose, record_usage
from app.models.enums import LLMPurpose
from app.models.llm_usage import LLMUsage
from app.models.user import User
from tests.conftest import TEST_USER_ID


def _resp() -> LLMResponse:
    return LLMResponse(
        content="x", model="gpt-4o", provider="openai",
        prompt_tokens=10, completion_tokens=20, total_tokens=30,
        cost_usd=0.001, latency_ms=12.0,
    )


class TestCoercePurpose:
    def test_valid_value(self):
        assert _coerce_purpose("cover_letter") == LLMPurpose.COVER_LETTER

    def test_unknown_falls_back_to_general(self):
        assert _coerce_purpose("structured") == LLMPurpose.GENERAL
        assert _coerce_purpose("general") == LLMPurpose.GENERAL

    def test_enum_passthrough(self):
        assert _coerce_purpose(LLMPurpose.HARNESS_JUDGE) == LLMPurpose.HARNESS_JUDGE


class TestRecordUsage:
    async def _user(self, db):
        db.add(User(id=TEST_USER_ID, email="u@x.com", hashed_password="x"))
        await db.commit()

    async def test_writes_row(self, db_session):
        await self._user(db_session)
        row = await record_usage(
            db_session, _resp(), user_id=TEST_USER_ID, purpose="harness_judge", trace_id="t-1"
        )
        assert row.id is not None

        rows = (await db_session.execute(select(LLMUsage))).scalars().all()
        assert len(rows) == 1
        r = rows[0]
        assert r.user_id == TEST_USER_ID
        assert r.purpose == LLMPurpose.HARNESS_JUDGE
        assert r.total_tokens == 30 and r.cost_usd == 0.001
        assert r.status == "success" and r.trace_id == "t-1"

    async def test_coerces_unknown_purpose(self, db_session):
        await self._user(db_session)
        row = await record_usage(db_session, _resp(), user_id=TEST_USER_ID, purpose="structured")
        assert row.purpose == LLMPurpose.GENERAL
