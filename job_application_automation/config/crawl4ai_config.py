"""
Configuration settings for web scraping using Crawl4AI.
"""
import os
from pathlib import Path
from pydantic import BaseModel
from typing import Optional, Dict, List, Literal, Any
from dotenv import load_dotenv

_CRAWL_CONFIG_ROOT = Path(__file__).resolve().parent.parent

# Load environment variables
load_dotenv()


class Crawl4AIConfig(BaseModel):
    """
    Configuration settings for web scraping using Crawl4AI.
    """
    # Crawling strategies
    crawler_strategy: Literal["playwright", "http"] = "playwright"  # Options: "playwright" or "http"
    deep_crawling_enabled: bool = True
    
    # Deep crawling settings
    crawling_strategy: Literal["bfs", "dfs", "bestfirst"] = "bestfirst"
    max_pages: int = 10  # Maximum number of pages to crawl per job site
    max_depth: int = 3  # Maximum depth for deep crawling
    
    # Rate limiting
    rate_limit: float = 1.0  # Requests per second
    
    # Content extraction settings
    extract_job_title: bool = True
    extract_company: bool = True
    extract_location: bool = True
    extract_job_description: bool = True
    extract_qualifications: bool = True
    extract_responsibilities: bool = True
    extract_salary: bool = True
    extract_application_url: bool = True
    extract_posting_date: bool = True
    extract_job_type: bool = True

    # Enhanced content extraction settings
    content_extraction_rules: Dict[str, List[str]] = {
        "job_title": [
            "h1.job-title", 
            ".position-title",
            "h1[data-automation='job-title']"
        ],
        "company": [
            ".company-name",
            "a[data-automation='employer-name']",
            ".employer-info h2"
        ],
        "location": [
            ".location",
            "span[data-automation='location']",
            ".job-location"
        ],
        "salary": [
            ".salary-range",
            "span[data-automation='salary']",
            ".compensation"
        ],
        "requirements": [
            ".requirements",
            ".qualifications",
            "#job-requirements"
        ],
        "responsibilities": [
            ".responsibilities",
            ".duties",
            "#job-description"
        ]
    }

    # AI-powered extraction settings
    use_llm_extraction: bool = True
    llm_batch_size: int = 5
    extract_company_culture: bool = True
    extract_tech_stack: bool = True
    extract_benefits: bool = True
    ai_extraction_enabled: bool = True
    ai_confidence_threshold: float = 0.7
    use_llm_for_unstructured: bool = True
    
    # Skills extraction settings
    skills_extraction: Dict[str, Any] = {
        "technical_skills": [
            "programming languages",
            "frameworks",
            "tools",
            "databases",
            "cloud platforms",
            "methodologies"
        ],
        "soft_skills": [
            "communication",
            "leadership",
            "teamwork",
            "problem-solving",
            "time management"
        ],
        "certifications": [
            "certified",
            "certificate",
            "certification",
            "licensed"
        ]
    }

    # Company info extraction
    company_info_extraction: bool = True
    company_info_fields: List[str] = [
        "company_size",
        "industry",
        "company_type",
        "benefits",
        "culture",
        "tech_stack"
    ]

    # Job match scoring weights
    scoring_weights: Dict[str, float] = {
        "technical_skills": 0.4,
        "experience": 0.3,
        "soft_skills": 0.2,
        "education": 0.1
    }
    
    # Question answering settings
    answer_questions: bool = True
    question_model_path: str = str(_CRAWL_CONFIG_ROOT / "models" / "qa_model")
    question_templates_path: str = str(_CRAWL_CONFIG_ROOT / "data" / "question_templates.json")

    # Output settings
    output_format: Literal["markdown", "json", "html"] = "markdown"
    output_dir: str = str(_CRAWL_CONFIG_ROOT / "data")
    job_listings_file: str = str(_CRAWL_CONFIG_ROOT / "data" / "job_listings.json")
    scraped_job_details_file: str = str(_CRAWL_CONFIG_ROOT / "data" / "scraped_job_details.json")
    
    # Memory settings
    memory_adaptive_dispatcher: bool = True
    max_memory_percent: float = 80.0  # Maximum memory usage percentage
    
    # Robots.txt compliance
    respect_robots_txt: bool = True
    
    # Browser profile for authenticated crawling
    browser_profile_name: Optional[str] = None
    
    # URL filtering
    url_include_patterns: List[str] = ["jobs", "careers", "position", "apply"]
    url_exclude_patterns: List[str] = ["login", "signin", "404", "error"]
    
    # Relevant content scoring for BestFirst crawling
    content_relevance_keywords: List[str] = [
        "job", "career", "position", "role", "opportunity", 
        "responsibilities", "qualifications", "requirements",
        "skills", "experience", "education", "salary", "benefits",
        "remote", "hybrid", "onsite", "full-time", "part-time", "contract",
        "tech stack", "programming languages", "frameworks",
        "company culture", "work life balance", "benefits",
        "healthcare", "equity", "bonus", "professional development"
    ]
    
    # Timeout settings
    request_timeout: int = 30  # seconds
    
    @classmethod
    def from_env(cls) -> "Crawl4AIConfig":
        """
        Create a Crawl4AIConfig instance from environment variables.
        """
        return cls(
            crawler_strategy=os.getenv("CRAWL4AI_STRATEGY", "playwright"),
            deep_crawling_enabled=os.getenv("CRAWL4AI_DEEP_CRAWLING", "True").lower() == "true",
            crawling_strategy=os.getenv("CRAWL4AI_CRAWLING_STRATEGY", "bestfirst"),
            max_pages=int(os.getenv("CRAWL4AI_MAX_PAGES", "10")),
            max_depth=int(os.getenv("CRAWL4AI_MAX_DEPTH", "3")),
            rate_limit=float(os.getenv("CRAWL4AI_RATE_LIMIT", "1.0")),
            respect_robots_txt=os.getenv("CRAWL4AI_RESPECT_ROBOTS", "True").lower() == "true",
            output_format=os.getenv("CRAWL4AI_OUTPUT_FORMAT", "markdown"),
            browser_profile_name=os.getenv("CRAWL4AI_BROWSER_PROFILE", None),
        )