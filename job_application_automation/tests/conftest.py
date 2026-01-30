"""
Shared pytest fixtures and configuration.
"""
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from job_application_automation.src.models import Base
from job_application_automation.src.database import get_db, init_db
from job_application_automation.src.application_tracker import ApplicationTracker

# Test database URL
TEST_DB_URL = "sqlite:///:memory:"

@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine."""
    engine = create_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    return engine

@pytest.fixture(scope="function")
def test_session(test_engine):
    """Create test database session."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()

@pytest.fixture(scope="function")
def test_db(test_session):
    """Get test database session with tables created."""
    Base.metadata.create_all(bind=test_session.bind)
    yield test_session
    Base.metadata.drop_all(bind=test_session.bind)

@pytest.fixture(scope="function")
def test_app_tracker(test_db):
    """Create test application tracker."""
    tracker = ApplicationTracker()
    return tracker

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
                "match_score": 1.0
            },
            {
                "name": "AWS",
                "category": "technical",
                "required": True,
                "candidate_has": True,
                "match_score": 0.9
            }
        ]
    }

@pytest.fixture
def sample_interaction_data():
    """Sample interaction data."""
    return {
        "interaction_type": "phone_screen",
        "notes": "Great conversation with hiring manager",
        "next_steps": "Technical interview scheduled",
        "outcome": "Positive"
    }