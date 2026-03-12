"""Custom exception hierarchy for AutoApply AI.

All domain exceptions inherit from AutoApplyError.
API routes catch these at the boundary and convert to HTTP responses.
"""


class AutoApplyError(Exception):
    """Root exception for all AutoApply domain errors."""

    def __init__(self, message: str = "", code: str = "AUTOAPPLY_ERROR") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


# --- Database Errors ---


class DatabaseError(AutoApplyError):
    """Base database error."""

    def __init__(self, message: str = "Database error") -> None:
        super().__init__(message, code="DATABASE_ERROR")


class DatabaseConnectionError(DatabaseError):
    """Failed to connect to database."""

    def __init__(self, message: str = "Database connection failed") -> None:
        super().__init__(message)
        self.code = "DATABASE_CONNECTION_ERROR"


class QueryError(DatabaseError):
    """Query execution failed."""

    def __init__(self, message: str = "Query execution failed") -> None:
        super().__init__(message)
        self.code = "DATABASE_QUERY_ERROR"


class IntegrityError(DatabaseError):
    """Constraint violation (duplicate, FK, etc.)."""

    def __init__(self, message: str = "Data integrity violation") -> None:
        super().__init__(message)
        self.code = "DATABASE_INTEGRITY_ERROR"


class RecordNotFoundError(DatabaseError):
    """Requested record does not exist."""

    def __init__(self, entity: str = "Record", entity_id: str = "") -> None:
        message = f"{entity} not found"
        if entity_id:
            message = f"{entity} with id '{entity_id}' not found"
        super().__init__(message)
        self.code = "RECORD_NOT_FOUND"


# --- LLM Errors ---


class LLMError(AutoApplyError):
    """Base LLM error."""

    def __init__(self, message: str = "LLM error") -> None:
        super().__init__(message, code="LLM_ERROR")


class LLMProviderError(LLMError):
    """Provider-specific failure."""

    def __init__(self, provider: str, message: str = "") -> None:
        full_message = f"LLM provider '{provider}' error: {message}"
        super().__init__(full_message)
        self.code = "LLM_PROVIDER_ERROR"
        self.provider = provider


class LLMRateLimitError(LLMError):
    """Rate limit exceeded."""

    def __init__(self, provider: str = "", retry_after: float = 0) -> None:
        message = f"Rate limit exceeded for provider '{provider}'"
        super().__init__(message)
        self.code = "LLM_RATE_LIMIT"
        self.retry_after = retry_after


class LLMTimeoutError(LLMError):
    """LLM call timed out."""

    def __init__(self, message: str = "LLM call timed out") -> None:
        super().__init__(message)
        self.code = "LLM_TIMEOUT"


# --- Browser Automation Errors ---


class BrowserError(AutoApplyError):
    """Base browser automation error."""

    def __init__(self, message: str = "Browser automation error") -> None:
        super().__init__(message, code="BROWSER_ERROR")


class SessionError(BrowserError):
    """Session management failure (cookies, auth state)."""

    def __init__(self, message: str = "Browser session error") -> None:
        super().__init__(message)
        self.code = "BROWSER_SESSION_ERROR"


class NavigationError(BrowserError):
    """Page navigation or loading failure."""

    def __init__(self, url: str = "", message: str = "") -> None:
        full_message = f"Navigation failed for '{url}': {message}" if url else message
        super().__init__(full_message)
        self.code = "BROWSER_NAVIGATION_ERROR"


class FormFillError(BrowserError):
    """Form interaction failure (fill, click, upload)."""

    def __init__(self, field: str = "", message: str = "") -> None:
        full_message = f"Form fill failed for '{field}': {message}" if field else message
        super().__init__(full_message)
        self.code = "BROWSER_FORM_FILL_ERROR"


# --- Document Errors ---


class DocumentError(AutoApplyError):
    """Base document processing error."""

    def __init__(self, message: str = "Document processing error") -> None:
        super().__init__(message, code="DOCUMENT_ERROR")


class ParseError(DocumentError):
    """Failed to parse a document."""

    def __init__(self, file_path: str = "", message: str = "") -> None:
        full_message = f"Failed to parse '{file_path}': {message}" if file_path else message
        super().__init__(full_message)
        self.code = "DOCUMENT_PARSE_ERROR"


class GenerationError(DocumentError):
    """Failed to generate a document."""

    def __init__(self, message: str = "Document generation failed") -> None:
        super().__init__(message)
        self.code = "DOCUMENT_GENERATION_ERROR"


class TemplateError(DocumentError):
    """Template not found or invalid."""

    def __init__(self, template_name: str = "", message: str = "") -> None:
        full_message = f"Template '{template_name}' error: {message}" if template_name else message
        super().__init__(full_message)
        self.code = "DOCUMENT_TEMPLATE_ERROR"


# --- ATS Errors ---


class ATSError(AutoApplyError):
    """ATS scoring or optimization error."""

    def __init__(self, message: str = "ATS processing error") -> None:
        super().__init__(message, code="ATS_ERROR")


# --- Job Platform Errors ---


class JobPlatformError(AutoApplyError):
    """Base job platform error."""

    def __init__(self, platform: str = "", message: str = "") -> None:
        full_message = f"Platform '{platform}' error: {message}" if platform else message
        super().__init__(full_message, code="PLATFORM_ERROR")
        self.platform = platform


class AuthenticationError(JobPlatformError):
    """Authentication or login failure."""

    def __init__(self, platform: str = "", message: str = "Authentication failed") -> None:
        super().__init__(platform, message)
        self.code = "PLATFORM_AUTH_ERROR"


class SearchError(JobPlatformError):
    """Job search failure."""

    def __init__(self, platform: str = "", message: str = "Job search failed") -> None:
        super().__init__(platform, message)
        self.code = "PLATFORM_SEARCH_ERROR"


class ApplicationSubmissionError(JobPlatformError):
    """Job application submission failure."""

    def __init__(self, platform: str = "", message: str = "Application submission failed") -> None:
        super().__init__(platform, message)
        self.code = "PLATFORM_APPLICATION_ERROR"
