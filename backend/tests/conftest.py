"""Shared test fixtures for the backend test suite.

Multi-tenancy note: every test runs with the ``current_user_id`` ContextVar set to
:data:`TEST_USER_ID` (autouse ``_tenant_context``), so ORM SELECTs are scoped exactly as
in production. ``sample_job_data`` carries ``user_id`` so ``Job(**sample_job_data)`` is
tenant-correct. The ``client`` fixture is authenticated (auth dependencies overridden);
``anon_client`` exercises the real auth stack for register/login/guard tests.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user, get_db, get_tenant_db
from app.db.tenant import current_user_id
from app.models.base import Base
from app.models.user import User

TEST_DATABASE_URL = "sqlite+aiosqlite://"
TEST_USER_ID = "testuser0000000000000000000000aa"


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


@pytest.fixture(autouse=True)
def _tenant_context():
    """Scope all ORM SELECTs to the canonical test user for each test."""
    token = current_user_id.set(TEST_USER_ID)
    yield
    current_user_id.reset(token)


@pytest.fixture
async def current_user(db_session) -> User:
    """Persist and return the canonical authenticated test user."""
    user = User(
        id=TEST_USER_ID,
        email="test@example.com",
        hashed_password="x",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def sample_job_data() -> dict:
    """Sample job listing data for tests (carries the tenant ``user_id``)."""
    return {
        "user_id": TEST_USER_ID,
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


def _build_test_app(db_session: AsyncSession, *, authenticated: bool):
    """Build a FastAPI app wired to the test session, optionally pre-authenticated."""
    from app.main import create_app

    @asynccontextmanager
    async def _noop_lifespan(app):
        yield

    app = create_app()
    app.router.lifespan_context = _noop_lifespan

    async def override_get_db():
        yield db_session

    async def override_get_tenant_db():
        token = current_user_id.set(TEST_USER_ID)
        try:
            yield db_session
        finally:
            current_user_id.reset(token)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_tenant_db] = override_get_tenant_db

    if authenticated:
        async def override_get_current_user():
            return User(id=TEST_USER_ID, email="test@example.com", is_active=True)

        app.dependency_overrides[get_current_user] = override_get_current_user

    return app


@pytest.fixture
async def client(db_session):
    """Authenticated HTTP test client (auth dependencies overridden)."""
    app = _build_test_app(db_session, authenticated=True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def anon_client(db_session):
    """HTTP client that exercises the REAL auth stack (no current-user override)."""
    app = _build_test_app(db_session, authenticated=False)
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
