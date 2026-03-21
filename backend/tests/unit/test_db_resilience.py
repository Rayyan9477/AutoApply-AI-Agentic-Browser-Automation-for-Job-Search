"""Unit tests for app.core.db_resilience."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError as SAIntegrityError
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.core.db_resilience import handle_db_errors, with_retry
from app.core.exceptions import DatabaseConnectionError, IntegrityError, QueryError

# ---------------------------------------------------------------------------
# handle_db_errors
# ---------------------------------------------------------------------------


class TestHandleDbErrors:
    async def test_maps_integrity_error(self) -> None:
        @handle_db_errors
        async def failing_op() -> None:
            raise SAIntegrityError("duplicate", {}, None)

        with pytest.raises(IntegrityError):
            await failing_op()

    async def test_maps_operational_error(self) -> None:
        @handle_db_errors
        async def failing_op() -> None:
            raise OperationalError("connection lost", {}, None)

        with pytest.raises(DatabaseConnectionError):
            await failing_op()

    async def test_maps_generic_sqlalchemy_error(self) -> None:
        @handle_db_errors
        async def failing_op() -> None:
            raise SQLAlchemyError("bad query")

        with pytest.raises(QueryError):
            await failing_op()

    async def test_passes_through_on_success(self) -> None:
        @handle_db_errors
        async def ok_op() -> str:
            return "result"

        assert await ok_op() == "result"


# ---------------------------------------------------------------------------
# with_retry
# ---------------------------------------------------------------------------


class TestWithRetry:
    async def test_retries_on_operational_error_then_succeeds(self) -> None:
        call_count = 0

        @with_retry(max_attempts=3, min_wait=0.01, max_wait=0.02)
        async def flaky_op() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise OperationalError("transient", {}, None)
            return "ok"

        result = await flaky_op()
        assert result == "ok"
        assert call_count == 3

    async def test_raises_after_max_attempts_exhausted(self) -> None:
        @with_retry(max_attempts=2, min_wait=0.01, max_wait=0.02)
        async def always_fails() -> None:
            raise OperationalError("down", {}, None)

        with pytest.raises(OperationalError):
            await always_fails()

    async def test_does_not_retry_non_transient_errors(self) -> None:
        call_count = 0

        @with_retry(max_attempts=3, min_wait=0.01, max_wait=0.02)
        async def value_error_op() -> None:
            nonlocal call_count
            call_count += 1
            raise ValueError("not transient")

        with pytest.raises(ValueError):
            await value_error_op()

        assert call_count == 1
