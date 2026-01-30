"""
Tests for application tracking functionality.

Uses `test_app_tracker` fixture from conftest.py which provides an
ApplicationTracker wired to an in-memory SQLite database.
"""
import pytest
from datetime import datetime

from job_application_automation.src.application_tracker import ApplicationTracker

def test_add_application(test_app_tracker):
    """Test adding a new application."""
    application = test_app_tracker.add_application(
        job_id="test_job_1",
        job_title="Senior Software Engineer",
        company="Tech Company",
        source="linkedin",
        match_score=0.92,
        resume_path="/path/to/resume.pdf",
        cover_letter_path="/path/to/cover_letter.pdf",
        notes="Great company culture",
        skills=[
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
    )
    
    assert application is not None
    assert application.job_id == "test_job_1"
    assert application.match_score == 0.92
    assert len(application.skills) == 2

def test_update_application_status(test_app_tracker):
    """Test updating application status."""
    # First create an application
    application = test_app_tracker.add_application(
        job_id="test_job_2",
        job_title="Data Engineer",
        company="Data Corp",
        source="indeed",
        match_score=0.85,
        resume_path="/path/to/resume.pdf"
    )
    
    # Update status
    updated = test_app_tracker.update_application_status(
        job_id="test_job_2",
        status="interview_scheduled",
        response_received=True,
        notes="First round interview scheduled"
    )
    
    assert updated is not None
    assert updated.status == "interview_scheduled"
    assert updated.response_received is True
    assert "First round interview scheduled" in updated.notes

def test_add_interaction(test_app_tracker):
    """Test adding an interaction to an application."""
    # Create application
    application = test_app_tracker.add_application(
        job_id="test_job_3",
        job_title="Product Manager",
        company="Product Inc",
        source="linkedin",
        match_score=0.88,
        resume_path="/path/to/resume.pdf"
    )
    
    # Add interaction
    interaction = test_app_tracker.add_interaction(
        job_id="test_job_3",
        interaction_type="phone_screen",
        notes="Had a great conversation with the hiring manager",
        next_steps="Technical interview to be scheduled",
        outcome="Positive"
    )
    
    assert interaction is not None
    assert interaction.interaction_type == "phone_screen"
    assert interaction.outcome == "Positive"

def test_get_application_stats(test_app_tracker):
    """Test getting application statistics."""
    # Add multiple applications
    test_app_tracker.add_application(
        job_id="stats_test_1",
        job_title="Software Engineer",
        company="Company A",
        source="linkedin",
        match_score=0.9,
        resume_path="/path/to/resume.pdf"
    )
    
    test_app_tracker.add_application(
        job_id="stats_test_2",
        job_title="Senior Developer",
        company="Company B",
        source="indeed",
        match_score=0.85,
        resume_path="/path/to/resume.pdf"
    )
    
    # Update status for one application
    test_app_tracker.update_application_status(
        job_id="stats_test_1",
        status="interview_scheduled",
        response_received=True
    )
    
    # Get stats
    stats = test_app_tracker.get_application_stats()
    
    assert stats is not None
    assert stats["total_applications"] == 2
    assert "linkedin" in stats["applications_by_source"]
    assert "indeed" in stats["applications_by_source"]
    assert stats["response_rate"] > 0

def test_get_application_history(test_app_tracker):
    """Test getting application history with filters."""
    # Add applications
    test_app_tracker.add_application(
        job_id="history_test_1",
        job_title="Software Engineer",
        company="Tech Corp",
        source="linkedin",
        match_score=0.95,
        resume_path="/path/to/resume.pdf"
    )
    
    test_app_tracker.add_application(
        job_id="history_test_2",
        job_title="Data Scientist",
        company="Data Corp",
        source="indeed",
        match_score=0.8,
        resume_path="/path/to/resume.pdf"
    )
    
    # Test filters
    linkedin_apps = test_app_tracker.get_application_history(source="linkedin")
    assert len(linkedin_apps) == 1
    assert linkedin_apps[0].source == "linkedin"
    
    high_score_apps = test_app_tracker.get_application_history(min_match_score=0.9)
    assert len(high_score_apps) == 1
    assert high_score_apps[0].match_score >= 0.9

def test_get_recommendations(test_app_tracker):
    """Test getting recommendations based on application history."""
    # Add applications with various outcomes
    test_app_tracker.add_application(
        job_id="rec_test_1",
        job_title="Software Engineer",
        company="Success Corp",
        source="linkedin",
        match_score=0.95,
        resume_path="/path/to/resume.pdf"
    )
    test_app_tracker.update_application_status(
        job_id="rec_test_1",
        status="accepted",
        response_received=True
    )
    
    test_app_tracker.add_application(
        job_id="rec_test_2",
        job_title="Developer",
        company="No Response Inc",
        source="indeed",
        match_score=0.7,
        resume_path="/path/to/resume.pdf"
    )
    
    # Get recommendations
    recommendations = test_app_tracker.get_recommendations()
    
    assert recommendations is not None
    assert "high_success_sources" in recommendations
    assert "best_match_scores" in recommendations
    assert len(recommendations["high_success_sources"]) > 0