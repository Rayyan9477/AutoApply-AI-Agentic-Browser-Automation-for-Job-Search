#!/usr/bin/env python3
"""
Demo Script for Job Application Automation System

This script demonstrates the main features of the job application automation system
including resume optimization, job search, and application tracking.
"""

import os
import sys
import asyncio
import json
from pathlib import Path

from job_application_automation.src.utils.path_utils import get_project_root

project_root = get_project_root()

def print_banner():
    """Print a nice banner for the demo."""
    print("=" * 80)
    print("🚀 JOB APPLICATION AUTOMATION SYSTEM - DEMO")
    print("=" * 80)
    print("This demo showcases the main features of the system:")
    print("• Resume optimization with ATS scoring")
    print("• Job search across multiple platforms")
    print("• Application tracking and analytics")
    print("• AI-powered cover letter generation")
    print("• Vector-based job matching")
    print("=" * 80)

def demo_resume_optimization():
    """Demo resume optimization functionality."""
    print("\n🔧 DEMO: Resume Optimization")
    print("-" * 40)
    
    try:
        from job_application_automation.src.ats_cli import analyze_resume
        
        # Use sample files
        resume_path = project_root / "data" / "resumes" / "sample_resume.txt"
        job_desc_path = project_root / "data" / "job_descriptions" / "sample_ai_engineer.txt"
        
        if resume_path.exists() and job_desc_path.exists():
            print("📄 Analyzing resume against job description...")
            
            result = analyze_resume(
                resume_path=str(resume_path),
                job_desc_path=str(job_desc_path),
                optimize=True,
                target_score=0.75,
                output_format="docx"
            )
            
            if result.get("success"):
                print(f"✅ Resume optimization completed!")
                print(f"📊 ATS Score: {result.get('ats_score', 'N/A'):.2f}")
                print(f"📁 Optimized resume saved to: {result.get('output_path', 'N/A')}")
                
                # Show some analysis details
                if "analysis" in result:
                    analysis = result["analysis"]
                    print(f"🎯 Skills Match: {analysis.get('skills_match', 'N/A')}")
                    print(f"📝 Format Score: {analysis.get('format_score', 'N/A')}")
                    print(f"🔍 Keyword Match: {analysis.get('keyword_match', 'N/A')}")
            else:
                print("❌ Resume optimization failed")
        else:
            print("⚠️  Sample files not found. Please run init_project.py first.")
            
    except Exception as e:
        print(f"❌ Error in resume optimization demo: {e}")

def demo_application_tracking():
    """Demo application tracking functionality."""
    print("\n📋 DEMO: Application Tracking")
    print("-" * 40)
    
    try:
        from job_application_automation.src.application_tracker import ApplicationTracker
        
        tracker = ApplicationTracker()
        
        # Add a demo application
        print("📝 Adding demo application...")
        demo_app = tracker.add_application(
            job_id="demo_job_001",
            job_title="Senior AI Engineer",
            company="TechCorp AI Solutions",
            source="linkedin",
            match_score=0.92,
            resume_path="/tmp/demo_resume.pdf",
            cover_letter_path="/tmp/demo_cover.pdf",
            notes="Demo application for testing"
        )
        
        if demo_app:
            print("✅ Demo application added successfully")
            
            # Show statistics
            print("\n📊 Application Statistics:")
            stats = tracker.get_application_stats()
            
            if "error" not in stats:
                print(f"📈 Total Applications: {stats.get('total_applications', 0)}")
                print(f"📊 Response Rate: {stats.get('response_rate', 0):.1%}")
                print(f"🎯 Average Match Score: {stats.get('average_match_score', 0):.2f}")
                
                print("\n📋 Applications by Status:")
                for status, count in stats.get('applications_by_status', {}).items():
                    print(f"   {status}: {count}")
            else:
                print(f"❌ Error getting statistics: {stats['error']}")
        else:
            print("❌ Failed to add demo application")
            
    except Exception as e:
        print(f"❌ Error in application tracking demo: {e}")

def demo_vector_search():
    """Demo vector-based job search."""
    print("\n🔍 DEMO: Vector-Based Job Search")
    print("-" * 40)
    
    try:
        from job_application_automation.src.application_tracker import ApplicationTracker
        
        tracker = ApplicationTracker()
        
        # Perform semantic search
        print("🔍 Searching for similar jobs...")
        results = tracker.semantic_search_jobs("Python machine learning engineer", limit=5)
        
        if results:
            print(f"✅ Found {len(results)} similar jobs:")
            for i, job in enumerate(results[:3], 1):
                print(f"{i}. {job.get('job_title', 'N/A')} at {job.get('company', 'N/A')}")
                print(f"   Similarity Score: {job.get('similarity_score', 'N/A'):.3f}")
                print(f"   Match Score: {job.get('match_score', 'N/A'):.2f}")
                print()
        else:
            print("📭 No similar jobs found (database might be empty)")
            
    except Exception as e:
        print(f"❌ Error in vector search demo: {e}")

def demo_configuration():
    """Demo configuration system."""
    print("\n⚙️  DEMO: Configuration System")
    print("-" * 40)
    
    try:
        from job_application_automation.config.config import get_config
        
        config = get_config()
        
        print("✅ Configuration loaded successfully")
        print(f"🤖 LLM Provider: {config.llm.provider}")
        print(f"🌐 Browser Type: {config.browser.browser_type}")
        print(f"📊 Log Level: {config.logging.level}")
        print(f"💾 Data Directory: {config.data_dir}")
        print(f"🎯 Min Match Score: {config.min_match_score}")
        
    except Exception as e:
        print(f"❌ Error in configuration demo: {e}")

def demo_cli_interface():
    """Demo CLI interface."""
    print("\n💻 DEMO: Command Line Interface")
    print("-" * 40)
    
    try:
        import subprocess
        
        print("📋 Available CLI commands:")
        
        # Show CLI help
        result = subprocess.run(
            [sys.executable, "src/cli.py", "--help"],
            capture_output=True,
            text=True,
            cwd=project_root
        )
        
        if result.returncode == 0:
            # Extract and show main commands
            help_text = result.stdout
            lines = help_text.split('\n')
            
            commands = []
            for line in lines:
                if line.strip().startswith(('search', 'apply', 'optimize', 'status', 'stats', 'interactive')):
                    commands.append(line.strip())
            
            for cmd in commands[:6]:  # Show first 6 commands
                print(f"   {cmd}")
            
            print("\n💡 Try: python src/cli.py interactive")
        else:
            print("❌ CLI help not available")
            
    except Exception as e:
        print(f"❌ Error in CLI demo: {e}")

def demo_gemini_integration():
    """Demo Gemini API integration."""
    print("\n🤖 DEMO: Gemini AI Integration")
    print("-" * 40)
    
    try:
        from job_application_automation.src.llm_providers.gemini_provider import GeminiProvider
        from job_application_automation.config.gemini_config import GeminiConfig
        
        config = GeminiConfig()
        provider = GeminiProvider(config)
        
        print("✅ Gemini provider initialized")
        print(f"🤖 Model: {config.model}")
        print(f"🌡️  Temperature: {config.temperature}")
        print(f"📝 Max Tokens: {config.max_tokens}")
        
        # Test text generation (will fail without API key, but shows setup)
        try:
            response = provider.generate_text("Hello, this is a test of the Gemini integration.")
            print("✅ Text generation successful")
            print(f"📄 Response: {response[:100]}...")
        except Exception as e:
            if "API key" in str(e).lower():
                print("⚠️  Gemini API key not configured (expected)")
                print("💡 Add your GEMINI_API_KEY to .env file to enable AI features")
            else:
                print(f"❌ Text generation failed: {e}")
                
    except Exception as e:
        print(f"❌ Error in Gemini integration demo: {e}")

def main():
    """Main demo function."""
    print_banner()
    
    # Run demos
    demo_configuration()
    demo_resume_optimization()
    demo_application_tracking()
    demo_vector_search()
    demo_gemini_integration()
    demo_cli_interface()
    
    print("\n" + "=" * 80)
    print("🎉 DEMO COMPLETED!")
    print("=" * 80)
    print("\n📚 Next Steps:")
    print("1. Configure your API keys in .env file")
    print("2. Run: python src/cli.py interactive")
    print("3. Try: python src/cli.py optimize --resume data/resumes/sample_resume.txt --job-desc data/job_descriptions/sample_ai_engineer.txt")
    print("4. Check the documentation in README.md")
    print("5. Run tests: python test_system.py")
    print("\n🚀 Happy job hunting!")

if __name__ == "__main__":
    main() 