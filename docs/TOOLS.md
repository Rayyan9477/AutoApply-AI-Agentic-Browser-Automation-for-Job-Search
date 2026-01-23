# Tools and Libraries Documentation

## Core Dependencies

### 1. Configuration and Environment
- **python-dotenv** (>=1.0.0): Loads environment variables from .env files
- **pydantic** (>=2.4.0): Data validation and settings management
- **structlog** (>=23.2.0): Structured logging
- **python-json-logger** (>=2.0.7): JSON formatter for logging

### 2. Browser Automation
- **browser-use** (>=0.1.40): High-level browser automation
- **playwright** (>=1.40.0): Cross-browser automation
- **selenium** (>=4.15.0): Web browser automation
- **undetected-chromedriver** (>=3.5.0): Bypass detection in Selenium

### 3. Web Scraping
- **crawl4ai** (>=0.5.0): Web crawling and content extraction
- **beautifulsoup4** (>=4.12.0): HTML/XML parsing
- **requests** (>=2.31.0): HTTP requests
- **lxml** (>=4.9.0): XML and HTML processing

### 4. Document Processing
- **python-docx** (>=1.0.0): Read/write Word documents
- **docxtpl** (>=0.16.7): Template-based Word document generation
- **markdown** (>=3.4.0): Markdown processing
- **PyPDF2** (>=3.0.0): PDF processing
- **pdf2image** (>=1.16.0): Convert PDF to images

### 5. AI/ML Integration
- **transformers** (>=4.35.0): State-of-the-art NLP models
- **torch** (>=2.1.0): PyTorch deep learning framework
- **openai** (>=1.3.0): OpenAI API client
- **sentence-transformers**: Generate sentence embeddings
- **faiss-cpu**: Efficient similarity search and clustering

### 6. Database and ORM
- **SQLAlchemy** (>=2.0.0): SQL toolkit and ORM
- **alembic** (>=1.13.0): Database migrations
- **psycopg2-binary** (>=2.9.0): PostgreSQL adapter (optional)
- **mysqlclient** (>=2.2.0): MySQL adapter (optional)

## Integration Points

### 1. LinkedIn Integration (`linkedin_integration.py`)
- **Purpose**: Interacts with LinkedIn's API for job search and application
- **Key Features**:
  - Job search and filtering
  - Application submission
  - Profile data extraction

### 2. Resume Optimization (`resume_optimizer.py`)
- **Purpose**: Optimizes resumes for ATS compatibility
- **Key Features**:
  - ATS scoring
  - Keyword optimization
  - Format standardization

### 3. Application Tracking (`application_tracker.py`)
- **Purpose**: Tracks job applications and status
- **Key Features**:
  - Application history
  - Status updates
  - Follow-up reminders

### 4. Browser Automation (`browser_automation.py`)
- **Purpose**: Automates web browser interactions
- **Key Features**:
  - Job site navigation
  - Form filling
  - Data extraction

## Development Dependencies

### 1. Testing
- **pytest** (>=7.4.0): Testing framework
- **pytest-asyncio** (>=0.21.0): Async test support
- **pytest-cov** (>=4.1.0): Test coverage reporting
- **pytest-mock** (>=3.12.0): Mocking for tests

### 2. Code Quality
- **mypy**: Static type checking
- **black**: Code formatting
- **flake8**: Linting
- **isort**: Import sorting

## Configuration

### Environment Variables
- `LINKEDIN_EMAIL`: LinkedIn account email
- `LINKEDIN_PASSWORD`: LinkedIn account password
- `OPENAI_API_KEY`: OpenAI API key
- `GROQ_API_KEY`: Groq API key (alternative to OpenAI)

## Usage Examples

### Running the Application
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your credentials

# Run the application
python -m src.main
```

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src tests/
```

## Troubleshooting

### Common Issues
1. **Browser Automation Failures**:
   - Ensure Chrome/Firefox is installed
   - Run `playwright install` to install browser dependencies

2. **API Rate Limiting**:
   - Implement retry logic with exponential backoff
   - Consider using multiple API keys if applicable

3. **Missing Dependencies**:
   - Run `pip install -r requirements.txt --upgrade`
   - Check for platform-specific requirements

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and ensure they pass
5. Submit a pull request

## License
[Specify your license here]
