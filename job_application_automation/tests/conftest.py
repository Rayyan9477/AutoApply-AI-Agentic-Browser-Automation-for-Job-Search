"""
Shared pytest fixtures and configuration.
"""
import os
import pytest
from contextlib import contextmanager
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from job_application_automation.src.models import Base
from job_application_automation.src.application_tracker import ApplicationTracker

# Test database URL
TEST_DB_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def test_engine():
    """Create test database engine (per-function for isolation)."""
    engine = create_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def test_session(test_engine):
    """Create test database session."""
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
def test_db(test_session):
    """Get test database session with tables created."""
    yield test_session


@pytest.fixture(scope="function")
def test_app_tracker(test_session):
    """Create test application tracker with mocked database session."""

    @contextmanager
    def _mock_get_db():
        try:
            yield test_session
        except Exception:
            test_session.rollback()
            raise

    with patch(
        "job_application_automation.src.application_tracker.get_db", _mock_get_db
    ):
        tracker = ApplicationTracker()
        yield tracker


# Sample test data
@pytest.fixture
def sample_job_data():
    """Sample job application data."""
    return {
        "job_id": "test_job_123",
        "job_title": "Senior Software Engineer",
        "company": "Test Tech Corp",
        "source": "linkedin",
        "match_score": 0.92,
        "resume_path": "/path/to/resume.pdf",
        "cover_letter_path": "/path/to/cover_letter.pdf",
        "notes": "Great opportunity",
        "skills": [
            {
                "name": "Python",
                "category": "technical",
                "required": True,
                "candidate_has": True,
                "match_score": 1.0,
            },
            {
                "name": "AWS",
                "category": "technical",
                "required": True,
                "candidate_has": True,
                "match_score": 0.9,
            },
        ],
    }


@pytest.fixture
def sample_interaction_data():
    """Sample interaction data."""
    return {
        "interaction_type": "phone_screen",
        "notes": "Great conversation with hiring manager",
        "next_steps": "Technical interview scheduled",
        "outcome": "Positive",
    }
