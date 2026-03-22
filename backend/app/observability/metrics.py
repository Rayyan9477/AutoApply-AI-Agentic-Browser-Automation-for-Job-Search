"""Prometheus metrics definitions.

All metrics are defined at module level as singletons.
Import and use them directly: `from app.observability.metrics import applications_total`.
"""

from prometheus_client import Counter, Gauge, Histogram

# --- Application Metrics ---

applications_total = Counter(
    "autoapply_applications_total",
    "Total number of job applications submitted",
    ["status", "platform"],
)

# --- ATS Metrics ---

ats_score_histogram = Histogram(
    "autoapply_ats_score",
    "Distribution of ATS scores",
    ["template"],
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0],
)

# --- LLM Metrics ---

llm_latency_seconds = Histogram(
    "autoapply_llm_latency_seconds",
    "LLM call latency in seconds",
    ["provider", "model", "purpose"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
)

llm_tokens_total = Counter(
    "autoapply_llm_tokens_total",
    "Total LLM tokens consumed",
    ["provider", "model", "direction"],
)

llm_cost_usd = Counter(
    "autoapply_llm_cost_usd_total",
    "Cumulative LLM cost in USD",
    ["provider", "model"],
)

llm_requests_total = Counter(
    "autoapply_llm_requests_total",
    "Total LLM API requests",
    ["provider", "model", "status"],
)

# --- Browser Automation Metrics ---

browser_actions_total = Counter(
    "autoapply_browser_actions_total",
    "Total browser automation actions",
    ["platform", "action"],
)

browser_session_duration_seconds = Histogram(
    "autoapply_browser_session_duration_seconds",
    "Browser session duration in seconds",
    ["platform"],
    buckets=[5, 15, 30, 60, 120, 300, 600],
)

# --- Queue Metrics ---

queue_depth = Gauge(
    "autoapply_queue_depth",
    "Current number of items in queue",
    ["queue_name"],
)

queue_processing_duration_seconds = Histogram(
    "autoapply_queue_processing_duration_seconds",
    "Time to process a queue item",
    ["queue_name"],
    buckets=[1, 5, 15, 30, 60, 120, 300],
)

# --- Document Metrics ---

documents_generated_total = Counter(
    "autoapply_documents_generated_total",
    "Total documents generated",
    ["document_type", "template", "format"],
)

# --- Job Search Metrics ---

job_searches_total = Counter(
    "autoapply_job_searches_total",
    "Total job searches performed",
    ["platform"],
)

jobs_found_total = Counter(
    "autoapply_jobs_found_total",
    "Total jobs found from searches",
    ["platform"],
)
