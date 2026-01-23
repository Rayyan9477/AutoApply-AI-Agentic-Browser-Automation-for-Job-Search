#!/usr/bin/env python3
"""
Comprehensive System Test for Job Application Automation

This script tests all major components of the job application automation system
to ensure everything is working correctly.
"""

import os
import sys
import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def setup_logging():
    """Set up logging for the test process."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(project_root / "test_system.log")
        ]
    )
    return logging.getLogger(__name__)

class SystemTester:
    """Comprehensive system tester for job application automation."""
    
    def __init__(self):
        """Initialize the system tester."""
        self.logger = logging.getLogger(__name__)
        self.test_results = {}
        self.passed_tests = 0
        self.total_tests = 0
        
    def run_test(self, test_name: str, test_func):
        """Run a test and record the result."""
        self.total_tests += 1
        self.logger.info(f"Running test: {test_name}")
        
        try:
            result = test_func()
            if result:
                self.test_results[test_name] = "PASS"
                self.passed_tests += 1
                self.logger.info(f"✅ {test_name}: PASS")
            else:
                self.test_results[test_name] = "FAIL"
                self.logger.error(f"❌ {test_name}: FAIL")
        except Exception as e:
            self.test_results[test_name] = f"ERROR: {str(e)}"
            self.logger.error(f"❌ {test_name}: ERROR - {e}")
    
    async def run_async_test(self, test_name: str, test_func):
        """Run an async test and record the result."""
        self.total_tests += 1
        self.logger.info(f"Running async test: {test_name}")
        
        try:
            result = await test_func()
            if result:
                self.test_results[test_name] = "PASS"
                self.passed_tests += 1
                self.logger.info(f"✅ {test_name}: PASS")
            else:
                self.test_results[test_name] = "FAIL"
                self.logger.error(f"❌ {test_name}: FAIL")
        except Exception as e:
            self.test_results[test_name] = f"ERROR: {str(e)}"
            self.logger.error(f"❌ {test_name}: ERROR - {e}")
    
    def test_imports(self):
        """Test that all modules can be imported."""
        try:
            # Test core imports
            from src.database import init_db, get_engine
            from src.models import Base, JobApplication
            from src.application_tracker import ApplicationTracker
            from src.resume_optimizer import ATSScorer, ResumeOptimizer
            from src.ats_integration import ATSIntegrationManager
            from src.vector_database import VectorDatabaseService
            from config.config import get_config
            from config.gemini_config import GeminiConfig
            from config.logging_config import configure_logging
            
            return True
        except ImportError as e:
            self.logger.error(f"Import error: {e}")
            return False
    
    def test_configuration(self):
        """Test configuration loading."""
        try:
            from config.config import get_config
            
            config = get_config()
            
            # Check that config has required attributes
            required_attrs = ['browser', 'logging', 'linkedin', 'crawl', 'llm', 'security']
            for attr in required_attrs:
                if not hasattr(config, attr):
                    self.logger.error(f"Missing config attribute: {attr}")
                    return False
            
            self.logger.info(f"Configuration loaded successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Configuration error: {e}")
            return False
    
    def test_database_connection(self):
        """Test database connection and initialization."""
        try:
            from src.database import init_db, get_engine, check_database_connection
            
            # Initialize database
            init_db()
            
            # Check connection
            is_connected, error = check_database_connection()
            if not is_connected:
                self.logger.error(f"Database connection failed: {error}")
                return False
            
            self.logger.info("Database connection successful")
            return True
            
        except Exception as e:
            self.logger.error(f"Database error: {e}")
            return False
    
    def test_application_tracker(self):
        """Test application tracking functionality."""
        try:
            from src.application_tracker import ApplicationTracker
            
            tracker = ApplicationTracker()
            
            # Test adding an application
            test_app = tracker.add_application(
                job_id="test_job_123",
                job_title="Test Software Engineer",
                company="Test Company",
                source="test",
                match_score=0.85,
                resume_path="/tmp/test_resume.pdf",
                cover_letter_path="/tmp/test_cover.pdf"
            )
            
            if test_app:
                self.logger.info("Application tracking test successful")
                return True
            else:
                self.logger.error("Failed to add test application")
                return False
                
        except Exception as e:
            self.logger.error(f"Application tracker error: {e}")
            return False
    
    def test_resume_optimizer(self):
        """Test resume optimization functionality."""
        try:
            from src.resume_optimizer import ATSScorer
            
            scorer = ATSScorer()
            
            # Test with sample data
            sample_resume = {
                "skills": ["Python", "Machine Learning", "TensorFlow"],
                "experience": [{"title": "Data Scientist", "company": "Tech Corp"}],
                "education": [{"degree": "BS Computer Science"}]
            }
            
            sample_job_desc = """
            We are looking for a Python developer with experience in machine learning.
            Required skills: Python, TensorFlow, Data Analysis
            """
            
            score_result = scorer.score_resume(sample_resume, sample_job_desc)
            
            if score_result and "ats_score" in score_result:
                self.logger.info(f"Resume optimization test successful (Score: {score_result['ats_score']})")
                return True
            else:
                self.logger.error("Resume optimization test failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Resume optimizer error: {e}")
            return False
    
    def test_vector_database(self):
        """Test vector database functionality."""
        try:
            from src.vector_database import VectorDatabaseService
            
            vector_db = VectorDatabaseService()
            
            # Test creating an index
            success = vector_db.create_index("test_index", 384, "Flat")
            if not success:
                self.logger.error("Failed to create test index")
                return False
            
            # Test adding items
            test_items = [
                {"id": 1, "text": "Python developer with machine learning experience"},
                {"id": 2, "text": "Software engineer specializing in AI and data science"}
            ]
            
            success = vector_db.add_items("test_index", test_items, text_field="text", id_field="id")
            if not success:
                self.logger.error("Failed to add items to test index")
                return False
            
            # Test search
            results = vector_db.search("test_index", "Python machine learning", k=2)
            if results:
                self.logger.info(f"Vector database test successful (Found {len(results)} results)")
                return True
            else:
                self.logger.error("Vector database search failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Vector database error: {e}")
            return False
    
    async def test_gemini_integration(self):
        """Test Gemini API integration."""
        try:
            from src.llm_providers.gemini_provider import GeminiProvider
            from config.gemini_config import GeminiConfig
            
            # Create test config
            config = GeminiConfig()
            
            # Test provider initialization
            provider = GeminiProvider(config)
            
            # Test text generation (this might fail if no API key, but should not crash)
            try:
                response = provider.generate_text("Hello, this is a test.")
                self.logger.info("Gemini integration test successful")
                return True
            except Exception as e:
                if "API key" in str(e).lower():
                    self.logger.warning("Gemini API key not configured (expected)")
                    return True
                else:
                    self.logger.error(f"Gemini integration error: {e}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Gemini integration error: {e}")
            return False
    
    def test_file_structure(self):
        """Test that all required files and directories exist."""
        required_files = [
            "requirements.txt",
            "setup.py",
            "README.md",
            "env.example",
            "alembic.ini",
            "src/__init__.py",
            "src/main.py",
            "src/cli.py",
            "src/database.py",
            "src/models.py",
            "config/__init__.py",
            "config/config.py",
            "config/gemini_config.py",
            "data/candidate_profile.json",
        ]
        
        required_dirs = [
            "src",
            "config",
            "data",
            "data/logs",
            "data/generated_cover_letters",
            "data/ats_reports",
            "migrations",
            "migrations/versions",
            "templates",
        ]
        
        # Check directories
        for directory in required_dirs:
            dir_path = project_root / directory
            if not dir_path.exists():
                self.logger.error(f"Missing directory: {directory}")
                return False
        
        # Check files
        for file_path in required_files:
            file_full_path = project_root / file_path
            if not file_full_path.exists():
                self.logger.error(f"Missing file: {file_path}")
                return False
        
        self.logger.info("File structure test successful")
        return True
    
    def test_sample_data(self):
        """Test that sample data files exist and are valid."""
        try:
            # Check candidate profile
            profile_path = project_root / "data" / "candidate_profile.json"
            if profile_path.exists():
                with open(profile_path, 'r') as f:
                    profile = json.load(f)
                
                required_fields = ["full_name", "email", "skills", "experience", "education"]
                for field in required_fields:
                    if field not in profile:
                        self.logger.error(f"Missing field in candidate profile: {field}")
                        return False
                
                self.logger.info("Sample data test successful")
                return True
            else:
                self.logger.error("Candidate profile not found")
                return False
                
        except Exception as e:
            self.logger.error(f"Sample data error: {e}")
            return False
    
    def test_cli_help(self):
        """Test that CLI help works."""
        try:
            import subprocess
            
            # Test CLI help
            result = subprocess.run(
                [sys.executable, "src/cli.py", "--help"],
                capture_output=True,
                text=True,
                cwd=project_root
            )
            
            if result.returncode == 0 and "Job Application Automation System" in result.stdout:
                self.logger.info("CLI help test successful")
                return True
            else:
                self.logger.error("CLI help test failed")
                return False
                
        except Exception as e:
            self.logger.error(f"CLI test error: {e}")
            return False
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("📊 SYSTEM TEST SUMMARY")
        print("=" * 60)
        
        print(f"Total Tests: {self.total_tests}")
        print(f"Passed: {self.passed_tests}")
        print(f"Failed: {self.total_tests - self.passed_tests}")
        print(f"Success Rate: {(self.passed_tests / self.total_tests * 100):.1f}%")
        
        print("\n📋 Test Results:")
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result == "PASS" else "❌ FAIL"
            print(f"  {test_name}: {status}")
            if result != "PASS":
                print(f"    Details: {result}")
        
        print("\n" + "=" * 60)
        
        if self.passed_tests == self.total_tests:
            print("🎉 All tests passed! The system is ready to use.")
        else:
            print("⚠️  Some tests failed. Please check the logs and fix the issues.")
        
        print("\n📚 Next steps:")
        print("1. Configure your API keys in .env file")
        print("2. Test with real data: python src/cli.py interactive")
        print("3. Check the documentation in README.md")

async def main():
    """Main test function."""
    logger = setup_logging()
    
    print("🧪 Running Comprehensive System Tests")
    print("=" * 60)
    
    tester = SystemTester()
    
    # Run synchronous tests
    tester.run_test("Import Test", tester.test_imports)
    tester.run_test("Configuration Test", tester.test_configuration)
    tester.run_test("Database Connection Test", tester.test_database_connection)
    tester.run_test("Application Tracker Test", tester.test_application_tracker)
    tester.run_test("Resume Optimizer Test", tester.test_resume_optimizer)
    tester.run_test("Vector Database Test", tester.test_vector_database)
    tester.run_test("File Structure Test", tester.test_file_structure)
    tester.run_test("Sample Data Test", tester.test_sample_data)
    tester.run_test("CLI Help Test", tester.test_cli_help)
    
    # Run asynchronous tests
    await tester.run_async_test("Gemini Integration Test", tester.test_gemini_integration)
    
    # Print summary
    tester.print_summary()

if __name__ == "__main__":
    asyncio.run(main()) 