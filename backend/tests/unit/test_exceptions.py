"""Unit tests for app.core.exceptions — full hierarchy coverage."""

from __future__ import annotations

from app.core.exceptions import (
    ApplicationSubmissionError,
    ATSError,
    AuthenticationError,
    AutoApplyError,
    BrowserError,
    DatabaseConnectionError,
    DatabaseError,
    DocumentError,
    FormFillError,
    GenerationError,
    IntegrityError,
    JobPlatformError,
    LLMError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
    NavigationError,
    ParseError,
    QueryError,
    RecordNotFoundError,
    SearchError,
    SessionError,
    TemplateError,
)

# ---------------------------------------------------------------------------
# Root exception
# ---------------------------------------------------------------------------


class TestAutoApplyError:
    def test_default_code(self):
        e = AutoApplyError("oops")
        assert e.code == "AUTOAPPLY_ERROR"
        assert e.message == "oops"
        assert str(e) == "oops"

    def test_custom_code(self):
        e = AutoApplyError("msg", code="CUSTOM")
        assert e.code == "CUSTOM"


# ---------------------------------------------------------------------------
# Database errors
# ---------------------------------------------------------------------------


class TestDatabaseErrors:
    def test_database_error_defaults(self):
        e = DatabaseError()
        assert e.code == "DATABASE_ERROR"
        assert "Database error" in e.message

    def test_connection_error(self):
        e = DatabaseConnectionError()
        assert e.code == "DATABASE_CONNECTION_ERROR"

    def test_query_error(self):
        e = QueryError()
        assert e.code == "DATABASE_QUERY_ERROR"

    def test_integrity_error(self):
        e = IntegrityError()
        assert e.code == "DATABASE_INTEGRITY_ERROR"

    def test_record_not_found_without_id(self):
        e = RecordNotFoundError("User")
        assert e.code == "RECORD_NOT_FOUND"
        assert "User not found" in e.message

    def test_record_not_found_with_id(self):
        e = RecordNotFoundError("User", "abc-123")
        assert "abc-123" in e.message
        assert "User" in e.message


# ---------------------------------------------------------------------------
# LLM errors
# ---------------------------------------------------------------------------


class TestLLMErrors:
    def test_llm_error_defaults(self):
        e = LLMError()
        assert e.code == "LLM_ERROR"

    def test_llm_provider_error(self):
        e = LLMProviderError("openai", "quota exceeded")
        assert e.code == "LLM_PROVIDER_ERROR"
        assert e.provider == "openai"
        assert "openai" in e.message
        assert "quota exceeded" in e.message

    def test_llm_rate_limit_error(self):
        e = LLMRateLimitError("openai", retry_after=30.0)
        assert e.code == "LLM_RATE_LIMIT"
        assert e.retry_after == 30.0
        assert "openai" in e.message

    def test_llm_timeout_error(self):
        e = LLMTimeoutError()
        assert e.code == "LLM_TIMEOUT"


# ---------------------------------------------------------------------------
# Browser errors
# ---------------------------------------------------------------------------


class TestBrowserErrors:
    def test_browser_error_defaults(self):
        e = BrowserError()
        assert e.code == "BROWSER_ERROR"

    def test_session_error(self):
        e = SessionError()
        assert e.code == "BROWSER_SESSION_ERROR"

    def test_navigation_error_with_url(self):
        e = NavigationError(url="https://example.com", message="timeout")
        assert e.code == "BROWSER_NAVIGATION_ERROR"
        assert "example.com" in e.message
        assert "timeout" in e.message

    def test_navigation_error_without_url(self):
        e = NavigationError(message="generic error")
        assert e.message == "generic error"

    def test_form_fill_error_with_field(self):
        e = FormFillError(field="email", message="not found")
        assert e.code == "BROWSER_FORM_FILL_ERROR"
        assert "email" in e.message

    def test_form_fill_error_without_field(self):
        e = FormFillError(message="general failure")
        assert e.message == "general failure"


# ---------------------------------------------------------------------------
# Document errors
# ---------------------------------------------------------------------------


class TestDocumentErrors:
    def test_document_error_defaults(self):
        e = DocumentError()
        assert e.code == "DOCUMENT_ERROR"

    def test_parse_error_with_path(self):
        e = ParseError("resume.pdf", "corrupt file")
        assert e.code == "DOCUMENT_PARSE_ERROR"
        assert "resume.pdf" in e.message

    def test_parse_error_without_path(self):
        e = ParseError(message="something went wrong")
        assert e.message == "something went wrong"

    def test_generation_error(self):
        e = GenerationError()
        assert e.code == "DOCUMENT_GENERATION_ERROR"

    def test_template_error_with_name(self):
        e = TemplateError("modern", "not found")
        assert e.code == "DOCUMENT_TEMPLATE_ERROR"
        assert "modern" in e.message

    def test_template_error_without_name(self):
        e = TemplateError(message="bad template")
        assert e.message == "bad template"


# ---------------------------------------------------------------------------
# ATS and Platform errors
# ---------------------------------------------------------------------------


class TestATSAndPlatformErrors:
    def test_ats_error(self):
        e = ATSError()
        assert e.code == "ATS_ERROR"

    def test_job_platform_error(self):
        e = JobPlatformError("linkedin", "rate limited")
        assert e.code == "PLATFORM_ERROR"
        assert e.platform == "linkedin"
        assert "linkedin" in e.message

    def test_authentication_error(self):
        e = AuthenticationError("indeed")
        assert e.code == "PLATFORM_AUTH_ERROR"
        assert e.platform == "indeed"

    def test_search_error(self):
        e = SearchError("glassdoor")
        assert e.code == "PLATFORM_SEARCH_ERROR"

    def test_application_submission_error(self):
        e = ApplicationSubmissionError("linkedin", "captcha")
        assert e.code == "PLATFORM_APPLICATION_ERROR"


# ---------------------------------------------------------------------------
# Inheritance checks
# ---------------------------------------------------------------------------


class TestInheritance:
    def test_database_errors_are_autoapply_errors(self):
        assert issubclass(DatabaseError, AutoApplyError)
        assert issubclass(RecordNotFoundError, DatabaseError)

    def test_llm_errors_are_autoapply_errors(self):
        assert issubclass(LLMError, AutoApplyError)
        assert issubclass(LLMProviderError, LLMError)

    def test_browser_errors_are_autoapply_errors(self):
        assert issubclass(BrowserError, AutoApplyError)
        assert issubclass(NavigationError, BrowserError)

    def test_document_errors_are_autoapply_errors(self):
        assert issubclass(DocumentError, AutoApplyError)
        assert issubclass(ParseError, DocumentError)

    def test_platform_errors_are_autoapply_errors(self):
        assert issubclass(JobPlatformError, AutoApplyError)
        assert issubclass(AuthenticationError, JobPlatformError)
