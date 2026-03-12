"""Application-wide constants."""

# API version
API_V1_PREFIX = "/api/v1"

# Application version
APP_VERSION = "2.0.0"
APP_TITLE = "AutoApply AI"

# Queue names (Redis)
QUEUE_APPLY = "autoapply:queue:apply"
QUEUE_SCRAPE = "autoapply:queue:scrape"
QUEUE_GENERATE = "autoapply:queue:generate"

# FAISS index names
INDEX_JOBS = "job_embeddings"
INDEX_RESUMES = "resume_embeddings"
INDEX_SKILLS = "skill_embeddings"

# Application status values
class ApplicationStatus:
    QUEUED = "queued"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    APPLYING = "applying"
    APPLIED = "applied"
    INTERVIEW = "interview"
    REJECTED = "rejected"
    OFFER = "offer"
    WITHDRAWN = "withdrawn"
    FAILED = "failed"


# Job status values
class JobStatus:
    NEW = "new"
    SAVED = "saved"
    APPLIED = "applied"
    HIDDEN = "hidden"


# LLM usage purposes
class LLMPurpose:
    RESUME_TAILOR = "resume_tailor"
    COVER_LETTER = "cover_letter"
    ATS_OPTIMIZE = "ats_optimize"
    JOB_ANALYSIS = "job_analysis"


# Supported platforms
SUPPORTED_PLATFORMS = ["linkedin", "indeed", "glassdoor"]

# Resume templates
RESUME_TEMPLATES = ["modern", "classic", "creative", "executive", "minimal"]

# Cover letter templates
COVER_LETTER_TEMPLATES = ["standard", "technical", "creative"]

# ATS scoring weights
ATS_WEIGHT_SKILLS = 0.4
ATS_WEIGHT_EXPERIENCE = 0.3
ATS_WEIGHT_EDUCATION = 0.2
ATS_WEIGHT_KEYWORDS = 0.1

# Embedding model
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384

# Pagination defaults
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
