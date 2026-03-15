"""Shared test fixtures for the backend test suite."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.models.base import Base

TEST_DATABASE_URL = "sqlite+aiosqlite://"


@pytest.fixture
async def async_engine():
    """Create an in-memory async SQLite engine for testing."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional async database session for testing."""
    session_factory = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
def sample_job_data() -> dict:
    """Sample job listing data for tests."""
    return {
        "platform": "linkedin",
        "platform_job_id": "job-12345",
        "title": "Senior Python Developer",
        "company": "TechCorp Inc.",
        "location": "Remote",
        "url": "https://linkedin.com/jobs/view/12345",
        "description": "We are looking for a Senior Python Developer...",
        "job_type": "full-time",
        "remote": True,
        "match_score": 0.85,
        "skills_required": {"required": ["python", "fastapi", "postgresql"], "preferred": []},
        "status": "new",
    }


@pytest.fixture
async def client(db_session):
    """HTTP test client with overridden DB dependency."""
    from app.main import create_app

    @asynccontextmanager
    async def _noop_lifespan(app):
        yield

    app = create_app()
    # Replace the lifespan so we don't attempt Redis/engine setup
    app.router.lifespan_context = _noop_lifespan

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def sample_candidate_profile() -> dict:
    """Sample candidate profile for tests."""
    return {
        "full_name": "Jane Doe",
        "email": "jane@example.com",
        "phone": "+1-555-0100",
        "summary": "Experienced Python developer with 5+ years...",
        "skills": ["python", "fastapi", "react", "postgresql", "docker"],
        "experience": [
            {
                "title": "Senior Developer",
                "company": "TechCo",
                "dates": "Jan 2020 - Present",
                "description": "Led backend development...",
            },
        ],
        "education": [
            {
                "degree": "BS Computer Science",
                "university": "MIT",
                "year": "2019",
            },
        ],
    }
