#!/usr/bin/env python3
"""
Project Initialization Script for Job Application Automation

This script sets up the complete project environment, including:
- Database initialization and migrations
- Directory structure creation
- Configuration file setup
- Sample data creation
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
import logging

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def setup_logging():
    """Set up logging for the initialization process."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(project_root / "init.log")
        ]
    )
    return logging.getLogger(__name__)

def create_directories():
    """Create necessary directories for the project."""
    logger = logging.getLogger(__name__)
    logger.info("Creating project directories...")
    
    directories = [
        "data/logs",
        "data/screenshots",
        "data/videos",
        "data/cookies",
        "data/sessions",
        "data/generated_cover_letters",
        "data/ats_reports",
        "data/embeddings_cache",
        "data/vector_indices",
        "data/job_descriptions",
        "data/resumes",
        "migrations/versions",
        "models",
        "templates",
    ]
    
    for directory in directories:
        dir_path = project_root / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {directory}")
    
    logger.info("✅ All directories created successfully")

def setup_environment_file():
    """Set up the environment file from example."""
    logger = logging.getLogger(__name__)
    logger.info("Setting up environment file...")
    
    env_example = project_root / "env.example"
    env_file = project_root / ".env"
    
    if env_example.exists() and not env_file.exists():
        shutil.copy(env_example, env_file)
        logger.info("✅ Created .env file from env.example")
        logger.info("⚠️  Please edit .env file with your actual API keys and credentials")
    elif env_file.exists():
        logger.info("✅ .env file already exists")
    else:
        logger.warning("⚠️  env.example not found, please create .env file manually")

def initialize_database():
    """Initialize the database and run migrations."""
    logger = logging.getLogger(__name__)
    logger.info("Initializing database...")
    
    try:
        # Change to project directory
        os.chdir(project_root)
        
        # Import database modules
        from src.database import init_db, get_engine
        from src.models import Base
        
        # Initialize database
        init_db()
        logger.info("✅ Database initialized successfully")
        
        # Check if alembic is available
        try:
            import alembic
            logger.info("Running database migrations...")
            
            # Run alembic upgrade
            result = subprocess.run(
                ["alembic", "upgrade", "head"],
                capture_output=True,
                text=True,
                cwd=project_root
            )
            
            if result.returncode == 0:
                logger.info("✅ Database migrations completed successfully")
            else:
                logger.warning(f"⚠️  Migration warning: {result.stderr}")
                
        except ImportError:
            logger.warning("⚠️  Alembic not available, skipping migrations")
            
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False
    
    return True

def create_sample_data():
    """Create sample data for testing."""
    logger = logging.getLogger(__name__)
    logger.info("Creating sample data...")
    
    # Create sample job description if it doesn't exist
    sample_job_file = project_root / "data" / "job_descriptions" / "sample_ai_engineer.txt"
    if not sample_job_file.exists():
        sample_job_content = """AI Engineer - Machine Learning Specialist

Company: TechCorp AI Solutions
Location: Remote (US-based)
Type: Full-time

Job Description:
We are seeking an experienced AI Engineer with expertise in Python, TensorFlow, and PyTorch to join our machine learning team. The ideal candidate will have a strong background in deep learning, computer vision, and natural language processing.

Key Responsibilities:
- Develop and optimize deep learning models using TensorFlow and PyTorch
- Implement computer vision and NLP solutions using state-of-the-art frameworks
- Build production-ready ML pipelines using MLflow
- Optimize model performance and reduce inference time

Required Qualifications:
- Bachelor's degree in Computer Science, Software Engineering, or related field
- Strong proficiency in Python programming
- Experience with TensorFlow, PyTorch, and other ML frameworks
- Knowledge of computer vision and NLP techniques
- Experience with cloud platforms (AWS, Azure, GCP)

Technical Skills:
- Programming Languages: Python, R, SQL, Java, C++
- ML/DL Frameworks: TensorFlow, PyTorch, Scikit-learn
- Data Processing: Pandas, NumPy, Matplotlib
- Cloud Platforms: AWS, Azure, GCP
- Databases: MySQL, MongoDB, MS SQL Server
"""
        sample_job_file.write_text(sample_job_content)
        logger.info("✅ Created sample job description")
    
    # Create sample resume if it doesn't exist
    sample_resume_file = project_root / "data" / "resumes" / "sample_resume.txt"
    if not sample_resume_file.exists():
        sample_resume_content = """Rayyan Ahmed
rayyanahmed265@yahoo.com | +92 3429519234 | LinkedIn: linkedin.com/in/rayyan-ahmed9477

PROFESSIONAL SUMMARY
AI Engineer with extensive expertise in Python, TensorFlow, and PyTorch. Demonstrated success in optimizing deep learning models, reducing inference time by 25%, and developing production-ready ML pipelines using MLflow.

SKILLS
Programming Languages: Python, R, SQL, Java, C++
Tools and Frameworks: Machine Learning, Deep Learning, Pandas, NumPy, Matplotlib, TensorFlow, Scikit-learn, PyTorch
Databases and Cloud Services: MySQL, MS SQL Server, MongoDB, AWS, Azure, GCP
Soft Skills: Analytical Thinking, Communication, Problem-Solving, Attention to Detail

EXPERIENCE
Data Analyst: Ozibook | Bangalore, India | October 2024 - Present
- Optimized SQL Queries and Interactive Dashboards: Enhanced SQL query performance by 20%
- Predictive Analytics Implementation: Built machine learning models using Python libraries

AI Engineer (Machine Learning): Digital Empowerment Networks | Islamabad, Pakistan | July 2024 - September 2024
- Advanced Data Processing: Conducted data cleaning, preprocessing, and visualization
- Machine Learning Models: Implemented k-means clustering, logistic regression, and NLP tokenizing

EDUCATION
BS Software Engineering: FAST NUCES Islamabad | Islamabad, Pakistan | 2022 - 2026
"""
        sample_resume_file.write_text(sample_resume_content)
        logger.info("✅ Created sample resume")
    
    logger.info("✅ Sample data created successfully")

def check_dependencies():
    """Check if all required dependencies are installed."""
    logger = logging.getLogger(__name__)
    logger.info("Checking dependencies...")
    
    required_packages = [
        "pydantic",
        "sqlalchemy",
        "alembic",
        "requests",
        "beautifulsoup4",
        "python-docx",
        "google-generativeai",
        "sentence-transformers",
        "faiss-cpu",
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            logger.info(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            logger.warning(f"❌ {package} - Not installed")
    
    if missing_packages:
        logger.warning(f"⚠️  Missing packages: {', '.join(missing_packages)}")
        logger.info("💡 Run: pip install -r requirements.txt")
        return False
    
    logger.info("✅ All required dependencies are installed")
    return True

def create_initial_migration():
    """Create initial database migration if needed."""
    logger = logging.getLogger(__name__)
    logger.info("Creating initial database migration...")
    
    try:
        # Change to project directory
        os.chdir(project_root)
        
        # Check if migrations directory exists
        migrations_dir = project_root / "migrations" / "versions"
        if not migrations_dir.exists():
            logger.warning("⚠️  Migrations directory not found")
            return False
        
        # Check if there are any migration files
        migration_files = list(migrations_dir.glob("*.py"))
        if migration_files:
            logger.info(f"✅ Found {len(migration_files)} existing migration(s)")
            return True
        
        # Create initial migration
        result = subprocess.run(
            ["alembic", "revision", "--autogenerate", "-m", "Initial migration"],
            capture_output=True,
            text=True,
            cwd=project_root
        )
        
        if result.returncode == 0:
            logger.info("✅ Initial migration created successfully")
            return True
        else:
            logger.warning(f"⚠️  Migration creation warning: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Migration creation failed: {e}")
        return False

def main():
    """Main initialization function."""
    logger = setup_logging()
    
    print("🚀 Initializing Job Application Automation Project")
    print("=" * 60)
    
    # Check dependencies first
    if not check_dependencies():
        print("\n⚠️  Some dependencies are missing. Please install them first:")
        print("   pip install -r requirements.txt")
        print("\nContinue anyway? (y/n): ", end="")
        if input().lower() != 'y':
            return
    
    # Create directories
    create_directories()
    
    # Setup environment file
    setup_environment_file()
    
    # Initialize database
    if not initialize_database():
        print("\n❌ Database initialization failed. Please check the logs.")
        return
    
    # Create initial migration
    create_initial_migration()
    
    # Create sample data
    create_sample_data()
    
    print("\n" + "=" * 60)
    print("✅ Project initialization completed successfully!")
    print("\n📋 Next steps:")
    print("1. Edit .env file with your API keys and credentials")
    print("2. Test the system: python src/cli.py --help")
    print("3. Try interactive mode: python src/cli.py interactive")
    print("4. Optimize a resume: python src/cli.py optimize --resume data/resumes/sample_resume.txt --job-desc data/job_descriptions/sample_ai_engineer.txt")
    print("\n📚 Documentation: README.md")
    print("🐛 Issues: Check init.log for any warnings or errors")

if __name__ == "__main__":
    main() 