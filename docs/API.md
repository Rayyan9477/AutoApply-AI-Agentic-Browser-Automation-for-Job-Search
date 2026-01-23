# API Documentation

This document describes the API interfaces available for integrating with the Job Application Automation system.

## Table of Contents
1. [Configuration](#configuration)
2. [LinkedIn Integration](#linkedin-integration)
3. [Resume Generation](#resume-generation)
4. [Database Integration](#database-integration)
5. [Error Handling](#error-handling)

## Configuration

The system uses a centralized configuration management approach with environment variable support and secure credential handling.

### Loading Configuration

```python
from config.config import get_config

# Get the central configuration
config = get_config()

# Access component configurations
browser_config = config.browser
linkedin_config = config.linkedin
llm_config = config.llm
```

### Updating Configuration

```python
from config.config import get_config_manager

# Get the configuration manager
config_manager = get_config_manager()

# Update configuration values
config_manager.update_config(
    "browser.headless", False,
    "max_applications_per_run", 10
)

# Update sensitive values
config_manager.update_secret("linkedin.client_secret", "your-secret-value")

# Save configuration
config_manager.save_config()
```

### Environment Variables

The system supports configuration via environment variables with the following format:
- Prefix: `JOB_APP_`
- Nested keys use double underscores: `__`

Examples:
```
JOB_APP_BROWSER__HEADLESS=false
JOB_APP_LINKEDIN__CLIENT_ID=your-client-id
JOB_APP_MAX_APPLICATIONS_PER_RUN=5
```

## LinkedIn Integration

The LinkedIn integration module provides functionality for job searching and application.

### Initialization

```python
from src.linkedin_integration import LinkedInIntegration
from config.linkedin_mcp_config import LinkedInMCPConfig

# Create configuration
linkedin_config = LinkedInMCPConfig(
    client_id="your-client-id",
    client_secret="your-client-secret",
    redirect_uri="http://localhost:8000/callback"
)

# Initialize integration
linkedin = LinkedInIntegration(linkedin_config)

# Authenticate (required before using other methods)
await linkedin.authenticate()
```

### Job Search

```python
# Search for jobs
jobs = await linkedin.search_jobs(
    keywords=["software engineer", "python"],
    location="Remote",
    count=10
)

# Get detailed job description
job_id = jobs[0]["job_id"]
job_details = await linkedin.get_job_description(job_id)

# Print job details
print(f"Title: {job_details.get('title')}")
print(f"Company: {job_details.get('company', {}).get('name')}")
print(f"Description: {job_details.get('description')}")
```

### Application Generation and Submission

```python
# Generate application materials (resume and cover letter)
materials = await linkedin.generate_application_materials(
    job_id="job-id-123",
    cover_letter_type="technical"  # Optional: standard, creative, technical, executive
)

# Apply to job
success = await linkedin.apply_to_job(
    job_id="job-id-123",
    resume_path=materials["resume_path"],
    cover_letter_path=materials["cover_letter_path"]
)

if success:
    print("Application submitted successfully!")
```

### Full Application Workflow

```python
# Execute the full workflow: search, generate materials, and apply
results = await linkedin.full_application_workflow(
    keywords=["software engineer", "python"],
    location="Remote",
    count=5,
    auto_apply=True  # Set to False to skip automatic application
)

# Process results
for result in results:
    job = result["job"]
    materials = result["materials"]
    applied = result.get("applied", False)
    
    print(f"Job: {job.get('job_title')} at {job.get('company')}")
    print(f"Applied: {applied}")
```

## Resume Generation

The resume generation module uses AI to create tailored resumes and cover letters.

### Basic Usage

```python
from src.resume_cover_letter_generator import ResumeGenerator

# Initialize generator
generator = ResumeGenerator()

# Generate resume
resume_path, resume_content = generator.generate_resume(
    job_description="Job description text...",
    candidate_profile=candidate_profile_dict
)

# Generate cover letter
cover_letter_path, cover_letter_content = generator.generate_cover_letter(
    job_description="Job description text...",
    candidate_resume=resume_content,
    company_info="Company information text..."
)
```

### Template Customization

```python
from src.resume_cover_letter_generator import ResumeGenerator, CoverLetterTemplate

# Initialize generator with custom templates
generator = ResumeGenerator(
    resume_template_path="path/to/custom_resume_template.docx",
    cover_letter_template_path="path/to/custom_cover_letter_template.docx"
)

# Generate cover letter with specific template type
cover_letter_path, _ = generator.generate_cover_letter(
    job_description="Job description text...",
    candidate_resume="Resume content...",
    company_info="Company information...",
    template_type=CoverLetterTemplate.TECHNICAL
)
```

## Database Integration

The system uses SQLAlchemy for database operations to track applications and job listings.

### Application Tracking

```python
from src.application_tracker import ApplicationTracker
from src.database import get_db

# Initialize tracker
tracker = ApplicationTracker()

# Add new application
application_id = tracker.add_application(
    job_id="job-id-123",
    job_title="Software Engineer",
    company="Example Corp",
    source="linkedin",
    match_score=0.85,
    resume_path="/path/to/resume.pdf",
    cover_letter_path="/path/to/cover_letter.pdf"
)

# Update application status
tracker.update_application_status(
    application_id=application_id,
    status="applied",
    notes="Application submitted via LinkedIn"
)

# Get application history
applications = tracker.get_applications(
    status="applied",
    company="Example Corp"
)
```

## Error Handling

The system provides custom exception classes for proper error handling.

### LinkedIn Integration Errors

```python
from src.linkedin_integration import (
    LinkedInAuthError, 
    LinkedInRateLimitError,
    LinkedInNetworkError
)

try:
    await linkedin.authenticate()
    jobs = await linkedin.search_jobs(keywords=["python"], location="Remote")
except LinkedInAuthError as e:
    print(f"Authentication error: {e}")
    # Handle authentication error (e.g., prompt for login)
except LinkedInRateLimitError as e:
    print(f"Rate limit exceeded: {e}")
    # Handle rate limiting (e.g., delay and retry)
except LinkedInNetworkError as e:
    print(f"Network error: {e}")
    # Handle network issues
except Exception as e:
    print(f"Unexpected error: {e}")
    # Handle other errors
```

### Database Errors

```python
from src.database_errors import (
    DatabaseConnectionError,
    RecordNotFoundError,
    DuplicateRecordError
)

try:
    tracker.add_application(...)
except DatabaseConnectionError as e:
    print(f"Database connection error: {e}")
    # Handle database connection issues
except DuplicateRecordError as e:
    print(f"Duplicate application: {e}")
    # Handle duplicate entry
except Exception as e:
    print(f"Unexpected error: {e}")
    # Handle other errors
```

## Logging

The system uses a structured logging system:

```python
import logging
from config.logging_config import configure_logging, AuditLogger

# Get configured logger
logger = configure_logging()

# Standard logging
logger.info("Operation started")
logger.error("An error occurred", extra={"job_id": "123", "context": "job_search"})

# Audit logging
audit = AuditLogger()
audit.log_application_event("application_submit", {
    "job_id": "job-123", 
    "company": "Example Corp",
    "success": True
})
```