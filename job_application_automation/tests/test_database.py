"""
Tests for database functionality and monitoring.
"""
import os
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool, QueuePool
from pathlib import Path
import json
import csv

from job_application_automation.src.models import Base, JobApplication, ApplicationInteraction, JobSkill, SearchHistory
from job_application_automation.src.database import get_db, check_database_connection, get_database_stats, init_db
from job_application_automation.src.database_monitor import (
    QueryPerformanceMonitor,
    DatabaseMonitorService,
    analyze_query_patterns
)

# Test database URL
TEST_DB_URL = "sqlite:///:memory:"

@pytest.fixture
def engine():
    """Create test database engine."""
    engine = create_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    return engine

@pytest.fixture
def TestingSessionLocal(engine):
    """Create test database session."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal

@pytest.fixture
def db(TestingSessionLocal):
    """Get test database session."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_create_job_application(db):
    """Test creating a job application."""
    application = JobApplication(
        job_id="test123",
        job_title="Software Engineer",
        company="Test Company",
        source="linkedin",
        match_score=0.85,
        resume_path="/path/to/resume.pdf"
    )
    db.add(application)
    db.commit()
    db.refresh(application)

    assert application.id is not None
    assert application.job_id == "test123"
    assert application.status == "submitted"  # Default status

def test_create_application_interaction(db):
    """Test creating an application interaction."""
    # Create application first
    application = JobApplication(
        job_id="test456",
        job_title="Data Scientist",
        company="Another Company",
        source="indeed",
        match_score=0.9,
        resume_path="/path/to/resume.pdf"
    )
    db.add(application)
    db.commit()

    # Create interaction
    interaction = ApplicationInteraction(
        application=application,
        interaction_type="email",
        notes="Received response from hiring manager",
        next_steps="Schedule interview"
    )
    db.add(interaction)
    db.commit()

    assert interaction.id is not None
    assert interaction.application_id == application.id
    assert interaction.interaction_type == "email"

def test_create_job_skill(db):
    """Test creating job skills."""
    # Create application first
    application = JobApplication(
        job_id="test789",
        job_title="Full Stack Developer",
        company="Tech Corp",
        source="linkedin",
        match_score=0.95,
        resume_path="/path/to/resume.pdf"
    )
    db.add(application)
    db.commit()

    # Create skills
    skills = [
        JobSkill(
            application=application,
            skill_name="Python",
            skill_category="technical",
            required=True,
            candidate_has=True,
            match_score=1.0
        ),
        JobSkill(
            application=application,
            skill_name="React",
            skill_category="technical",
            required=True,
            candidate_has=False,
            match_score=0.0
        )
    ]
    db.add_all(skills)
    db.commit()

    assert len(application.skills) == 2
    assert any(skill.skill_name == "Python" for skill in application.skills)
    assert any(skill.skill_name == "React" for skill in application.skills)

def test_search_history(db):
    """Test creating search history."""
    search = SearchHistory(
        keywords="software engineer, python",
        location="Remote",
        source="linkedin",
        results_count=100,
        filtered_count=25,
        search_params='{"experience": "mid-level", "remote": true}'
    )
    db.add(search)
    db.commit()

    assert search.id is not None
    assert search.keywords == "software engineer, python"
    assert search.results_count == 100

def test_database_connection():
    """Test database connection checking."""
    success, error = check_database_connection()
    assert success is True
    assert error is None

def test_database_stats(db):
    """Test getting database statistics."""
    # Add some test data
    application = JobApplication(
        job_id="test_stats",
        job_title="Test Position",
        company="Stats Corp",
        source="linkedin",
        match_score=0.75,
        resume_path="/path/to/resume.pdf"
    )
    db.add(application)
    db.commit()

    stats = get_database_stats()
    assert stats["status"] == "healthy"
    assert "connection_pool" in stats
    assert "tables" in stats
    assert stats["tables"]["job_applications"]["row_count"] >= 1

@pytest.fixture
def test_monitor():
    """Create a test query monitor."""
    return QueryPerformanceMonitor()

@pytest.fixture
def test_db_engine():
    """Create a test database engine."""
    engine = create_engine(
        'sqlite:///:memory:',
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10
    )
    Base.metadata.create_all(engine)
    return engine

@pytest.fixture
def test_monitor_service(test_db_engine):
    """Create a test database monitor service."""
    return DatabaseMonitorService(test_db_engine)

def test_query_recording(test_monitor):
    """Test query performance recording."""
    test_query = "SELECT * FROM test_table"
    duration = 1.5
    
    test_monitor.record_query(test_query, duration)
    stats = test_monitor.query_stats[test_query]
    
    assert stats["count"] == 1
    assert stats["total_time"] == duration
    assert stats["min_time"] == duration
    assert stats["max_time"] == duration
    assert stats["avg_time"] == duration
    assert isinstance(stats["last_executed"], datetime)

def test_slow_query_detection(test_monitor):
    """Test slow query detection."""
    fast_query = "SELECT 1"
    slow_query = "SELECT * FROM large_table"
    
    test_monitor.record_query(fast_query, 0.1)
    test_monitor.record_query(slow_query, 2.0)
    
    slow_queries = test_monitor.get_slow_queries()
    assert len(slow_queries) == 1
    assert slow_queries[0]["query"] == slow_query
    assert slow_queries[0]["stats"]["avg_time"] == 2.0

@pytest.mark.asyncio
async def test_health_check(test_monitor_service):
    """Test database health check."""
    health_check = await test_monitor_service.check_database_health()
    
    assert health_check["status"] == "healthy"
    assert "connection_pool" in health_check
    assert "query_stats" in health_check
    assert isinstance(health_check["last_check"], datetime)

def test_performance_metrics(test_monitor_service):
    """Test performance metrics calculation."""
    metrics = test_monitor_service.get_performance_metrics()
    
    assert "timestamp" in metrics
    assert "query_stats" in metrics
    assert "pool_stats" in metrics
    assert "performance_score" in metrics
    assert 0 <= metrics["performance_score"] <= 100

def test_slow_query_report(test_monitor_service, test_monitor):
    """Test slow query report generation."""
    # Record some test queries
    test_monitor.record_query("SELECT 1", 0.1)
    test_monitor.record_query("SELECT * FROM big_table", 2.0)
    test_monitor.record_query("SELECT * FROM huge_table", 3.0)
    
    report = test_monitor_service.get_slow_query_report(days=1)
    
    assert report["total_slow_queries"] == 2
    assert len(report["queries"]) == 2
    assert "total_time" in report["summary"]
    assert "avg_time" in report["summary"]

def test_query_pattern_analysis():
    """Test query pattern analysis."""
    monitor = QueryPerformanceMonitor()
    
    # Record some test queries with patterns
    for _ in range(10):
        monitor.record_query("SELECT * FROM users", 0.1)
    monitor.record_query("SELECT * FROM large_table", 2.0)
    
    analysis = analyze_query_patterns()
    
    assert "recommendations" in analysis
    assert "query_patterns" in analysis
    assert "peak_times" in analysis

def test_performance_score_calculation(test_monitor_service):
    """Test performance score calculation."""
    # Simulate different database states
    stats = {
        "total_queries": 100,
        "total_time": 50.0,
        "avg_time": 0.5,
        "slow_queries": 5
    }
    
    score = test_monitor_service._calculate_performance_score(stats)
    assert 0 <= score <= 100

    # Test with poor performance
    poor_stats = {
        "total_queries": 100,
        "total_time": 200.0,
        "avg_time": 2.0,
        "slow_queries": 50
    }
    
    poor_score = test_monitor_service._calculate_performance_score(poor_stats)
    assert poor_score < score  # Poor performance should have lower score

def test_monitor_reset(test_monitor):
    """Test monitor statistics reset."""
    test_monitor.record_query("SELECT 1", 0.1)
    assert len(test_monitor.query_stats) > 0
    
    test_monitor.reset_stats()
    assert len(test_monitor.query_stats) == 0

@pytest.mark.parametrize("query_time,expected_warning", [
    (0.5, False),  # Fast query
    (1.5, True),   # Slow query
])
def test_slow_query_warning(test_monitor, caplog, query_time, expected_warning):
    """Test slow query warning logging."""
    test_query = "SELECT * FROM test_table"
    test_monitor.record_query(test_query, query_time)
    
    has_warning = any(
        record.levelname == "WARNING" and "Slow query detected" in record.message
        for record in caplog.records
    )
    assert has_warning == expected_warning

@pytest.mark.asyncio
async def test_database_health_check(test_engine):
    monitor = DatabaseMonitorService(test_engine)
    health = await monitor.check_database_health()
    
    assert isinstance(health, dict)
    assert "status" in health
    assert "connection_pool" in health
    assert isinstance(health["connection_pool"], dict)

def test_performance_metrics(test_engine):
    monitor = DatabaseMonitorService(test_engine)
    metrics = monitor.get_performance_metrics()
    
    assert isinstance(metrics, dict)
    assert "timestamp" in metrics
    assert isinstance(metrics["timestamp"], datetime)
    assert "performance_score" in metrics
    assert isinstance(metrics["performance_score"], float)
    assert 0 <= metrics["performance_score"] <= 100

def test_metrics_export(test_engine, tmp_path):
    monitor = DatabaseMonitorService(test_engine)
    
    # Test CSV export
    csv_file = monitor.export_metrics(format='csv', output_dir=str(tmp_path))
    assert Path(csv_file).exists()
    with open(csv_file) as f:
        reader = csv.DictReader(f)
        row = next(reader)
        assert "timestamp" in row
        assert "performance_score" in row
    
    # Test JSON export
    json_file = monitor.export_metrics(format='json', output_dir=str(tmp_path))
    assert Path(json_file).exists()
    with open(json_file) as f:
        data = json.load(f)
        assert "timestamp" in data
        assert "performance_score" in data
        assert "query_stats" in data
        assert "pool_stats" in data

def test_slow_query_report(test_engine):
    monitor = DatabaseMonitorService(test_engine)
    report = monitor.get_slow_query_report(days=1)
    
    assert isinstance(report, dict)
    assert "total_slow_queries" in report
    assert isinstance(report["total_slow_queries"], int)
    assert "queries" in report
    assert isinstance(report["queries"], list)
    
    if report["queries"]:
        query = report["queries"][0]
        assert "query" in query
        assert "stats" in query
        assert isinstance(query["stats"], dict)

def test_slow_queries_export(test_engine, tmp_path):
    monitor = DatabaseMonitorService(test_engine)
    
    # Test CSV export
    csv_file = monitor.export_slow_queries_report(
        days=1, format='csv', output_dir=str(tmp_path)
    )
    assert Path(csv_file).exists()
    
    # Test JSON export
    json_file = monitor.export_slow_queries_report(
        days=1, format='json', output_dir=str(tmp_path)
    )
    assert Path(json_file).exists()
    with open(json_file) as f:
        data = json.load(f)
        assert "total_slow_queries" in data
        assert "queries" in data
        assert "summary" in data

def test_metrics_history(test_engine, tmp_path):
    monitor = DatabaseMonitorService(test_engine)
    
    # Generate some test metrics files
    for i in range(3):
        monitor.export_metrics(format='json', output_dir=str(tmp_path))
    
    history = monitor.get_metrics_history(days=1)
    assert isinstance(history, list)
    assert len(history) > 0
    
    for metrics in history:
        assert isinstance(metrics, dict)
        assert "timestamp" in metrics
        assert isinstance(metrics["timestamp"], datetime)
        assert "performance_score" in metrics

def test_query_pattern_analysis(test_engine):
    monitor = DatabaseMonitorService(test_engine)
    analysis = monitor.analyze_query_patterns()
    
    assert isinstance(analysis, dict)
    assert "recommendations" in analysis
    assert isinstance(analysis["recommendations"], list)
    assert "peak_times" in analysis
    assert isinstance(analysis["peak_times"], dict)

    if analysis["recommendations"]:
        rec = analysis["recommendations"][0]
        assert "type" in rec
        assert "message" in rec