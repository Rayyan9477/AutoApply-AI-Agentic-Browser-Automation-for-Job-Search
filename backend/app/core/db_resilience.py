"""Database resilience utilities: error mapping and async retry.

Provides decorators for async database functions that automatically
map SQLAlchemy exceptions to domain-specific errors and optionally
retry on transient failures with exponential backoff.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

import structlog
from sqlalchemy.exc import (
    DBAPIError,
    OperationalError,
    SQLAlchemyError,
)
from sqlalchemy.exc import (
    IntegrityError as SAIntegrityError,
)
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.exceptions import (
    DatabaseConnectionError as DBConnectionError,
)
from app.core.exceptions import (
    IntegrityError,
    QueryError,
)

logger = structlog.get_logger(__name__)

T = TypeVar("T")


def handle_db_errors(func: Callable[..., T]) -> Callable[..., T]:
    """Async decorator that maps SQLAlchemy errors to domain exceptions.

    Exception mapping:
        - ``SAIntegrityError`` -> ``IntegrityError``
        - ``OperationalError`` -> ``ConnectionError``
        - ``SQLAlchemyError``  -> ``QueryError``

    Args:
        func: An async callable that performs database operations.

    Returns:
        Wrapped async callable with automatic error translation.
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            return await func(*args, **kwargs)
        except SAIntegrityError as exc:
            logger.error(
                "db_integrity_error", func=func.__name__, error=str(exc)
            )
            raise IntegrityError(str(exc)) from exc
        except OperationalError as exc:
            logger.error(
                "db_connection_error", func=func.__name__, error=str(exc)
            )
            raise DBConnectionError(str(exc)) from exc
        except SQLAlchemyError as exc:
            logger.error(
                "db_query_error", func=func.__name__, error=str(exc)
            )
            raise QueryError(str(exc)) from exc

    return wrapper  # type: ignore[return-value]


def with_retry(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
) -> Callable:
    """Async retry decorator with exponential backoff for transient DB errors.

    Retries on ``OperationalError`` and ``DBAPIError`` which typically
    indicate transient issues (connection drops, lock contention, etc.).

    Args:
        max_attempts: Maximum total attempts before giving up.
        min_wait: Minimum wait between retries in seconds.
        max_wait: Maximum wait between retries in seconds.

    Returns:
        Decorator that wraps an async function with retry logic.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=min_wait, max=max_wait),
            retry=retry_if_exception_type((OperationalError, DBAPIError)),
            reraise=True,
        )
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator
