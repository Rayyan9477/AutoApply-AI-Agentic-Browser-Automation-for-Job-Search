#!/usr/bin/env python3
"""
Comprehensive CLI for Job Application Automation System

This module provides a unified command-line interface for all features of the
job application automation system, including job search, resume optimization,
application tracking, and more.
"""

import os
import argparse
import logging
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import webbrowser

# Import project modules
from job_application_automation.src.main import JobApplicationAutomation
from job_application_automation.src.smart_apply import SmartJobApplicant
from job_application_automation.src.ats_cli import analyze_resume, batch_analyze_resumes
from job_application_automation.src.manage_db import cli as db_cli
from job_application_automation.src.application_tracker import ApplicationTracker
from job_application_automation.config.config import get_config
from job_application_automation.config.logging_config import configure_logging

# Configure logging
logger = configure_logging()

class JobApplicationCLI:
    """Main CLI class for job application automation."""
    
    def __init__(self):
        """Initialize the CLI with configuration."""
        self.config = get_config()
        self.app_tracker = ApplicationTracker()
        
    async def search_jobs(self, args):
        """Search for jobs using multiple sources."""
        print("🔍 Searching for jobs...")
        
        # Initialize the automation system
        automation = JobApplicationAutomation()
        await automation.setup()
        
        # Search for jobs
        keywords = args.keywords.split(',') if args.keywords else ["python", "software engineer"]
        location = args.location or "Remote"
        
        jobs = await automation.search_jobs(
            keywords=keywords,
            location=location,
            use_linkedin=args.linkedin,
            use_browser=args.browser,
            job_site=args.site
        )
        
        if jobs:
            print(f"\n✅ Found {len(jobs)} jobs:")
            for i, job in enumerate(jobs[:10], 1):  # Show first 10
                print(f"{i}. {job.get('title', 'N/A')} at {job.get('company', 'N/A')}")
                print(f"   Location: {job.get('location', 'N/A')}")
                print(f"   URL: {job.get('url', 'N/A')}")
                print()
            
            # Save job listings
            output_file = Path(self.config.data_dir) / "job_listings.json"
            with open(output_file, 'w') as f:
                json.dump(jobs, f, indent=2, default=str)
            print(f"💾 Job listings saved to: {output_file}")
        else:
            print("❌ No jobs found matching your criteria.")
    
    async def apply_to_job(self, args):
        """Apply to a specific job."""
        print("📝 Processing job application...")
        
        # Initialize smart applicant
        applicant = SmartJobApplicant()
        
        # Process the application
        result = await applicant.process_job(
            resume_path=args.resume,
            job_description=args.job_desc,
            job_metadata={
                "title": args.job_title,
                "company": args.company,
                "url": args.external_url
            },
            score_threshold=args.threshold / 100,  # Convert percentage to decimal
            auto_apply=not args.no_apply,
            external_url=args.external_url
        )
        
        if result.get("success"):
            print("✅ Application processed successfully!")
            if result.get("applied"):
                print("🚀 Application submitted!")
            else:
                print("📋 Application prepared but not submitted (use --apply to submit)")
        else:
            print("❌ Application processing failed.")
            if result.get("error"):
                print(f"Error: {result['error']}")
    
    def optimize_resume(self, args):
        """Optimize resume for a job description."""
        print("🔧 Optimizing resume...")
        
        # Analyze and optimize resume
        result = analyze_resume(
            resume_path=args.resume,
            job_desc_path=args.job_desc,
            optimize=args.optimize,
            target_score=args.target_score,
            output_format=args.format
        )
        
        if result.get("success"):
            print("✅ Resume optimization completed!")
            print(f"📊 ATS Score: {result.get('ats_score', 'N/A')}")
            print(f"📁 Output file: {result.get('output_path', 'N/A')}")
        else:
            print("❌ Resume optimization failed.")
    
    def batch_optimize(self, args):
        """Batch optimize multiple resumes."""
        print("🔧 Batch optimizing resumes...")
        
        results = batch_analyze_resumes(
            resumes_dir=args.resumes_dir,
            job_desc_path=args.job_desc,
            optimize=args.optimize,
            target_score=args.target_score
        )
        
        print(f"✅ Processed {len(results)} resumes:")
        for result in results:
            print(f"📄 {result.get('resume_name', 'N/A')}: {result.get('ats_score', 'N/A')}")
    
    def generate_report(self, args):
        """Generate ATS performance report."""
        print("📊 Generating ATS performance report...")
        
        applicant = SmartJobApplicant()
        report_path = applicant.generate_ats_report(
            format=args.format,
            output_path=args.output
        )
        
        if report_path:
            print(f"✅ Report generated: {report_path}")
            if args.format == "html" and args.open:
                webbrowser.open(f"file://{os.path.abspath(report_path)}")
        else:
            print("❌ Failed to generate report.")
    
    def check_status(self, args):
        """Check application status."""
        if args.id:
            # Check specific application
            app = self.app_tracker.get_application(application_id=args.id)
            if app:
                self._print_application_status(app)
            else:
                print(f"❌ Application with ID {args.id} not found.")
        else:
            # Show recent applications
            applications = self.app_tracker.get_application_history()
            if applications:
                print(f"📋 Found {len(applications)} applications:")
                for app in applications[:args.count]:
                    self._print_application_status(app)
                    print("-" * 50)
            else:
                print("📋 No applications found.")
    
    def _print_application_status(self, app):
        """Print application status in a formatted way."""
        print(f"📄 {app.get('job_title', 'N/A')} at {app.get('company', 'N/A')}")
        print(f"   Status: {app.get('status', 'N/A')}")
        print(f"   Match Score: {app.get('match_score', 'N/A')}")
        print(f"   Applied: {app.get('application_date', 'N/A')}")
        if app.get('response_received'):
            print(f"   Response: {app.get('response_date', 'N/A')}")
    
    def show_stats(self, args):
        """Show application statistics."""
        print("📊 Application Statistics:")
        
        stats = self.app_tracker.get_application_stats()
        if "error" in stats:
            print(f"❌ Error: {stats['error']}")
            return
        
        print(f"📈 Total Applications: {stats.get('total_applications', 0)}")
        print(f"📊 Response Rate: {stats.get('response_rate', 0):.1%}")
        print(f"🎯 Average Match Score: {stats.get('average_match_score', 0):.2f}")
        
        print("\n📋 Applications by Status:")
        for status, count in stats.get('applications_by_status', {}).items():
            print(f"   {status}: {count}")
        
        print("\n🌐 Applications by Source:")
        for source, count in stats.get('applications_by_source', {}).items():
            print(f"   {source}: {count}")
    
    def interactive_mode(self, args):
        """Run interactive mode."""
        print("🎯 Welcome to Job Application Automation Interactive Mode!")
        print("=" * 60)
        
        while True:
            print("\nAvailable commands:")
            print("1. search - Search for jobs")
            print("2. apply - Apply to a job")
            print("3. optimize - Optimize resume")
            print("4. status - Check application status")
            print("5. stats - Show statistics")
            print("6. report - Generate report")
            print("7. quit - Exit")
            
            choice = input("\nEnter your choice (1-7): ").strip()
            
            if choice == "1":
                await self._interactive_search()
            elif choice == "2":
                await self._interactive_apply()
            elif choice == "3":
                self._interactive_optimize()
            elif choice == "4":
                self._interactive_status()
            elif choice == "5":
                self.show_stats(None)
            elif choice == "6":
                self._interactive_report()
            elif choice == "7":
                print("👋 Goodbye!")
                break
            else:
                print("❌ Invalid choice. Please try again.")
    
    async def _interactive_search(self):
        """Interactive job search."""
        keywords = input("Enter keywords (comma-separated): ").strip()
        location = input("Enter location (default: Remote): ").strip() or "Remote"
        
        # Create mock args object
        class MockArgs:
            pass
        args = MockArgs()
        args.keywords = keywords
        args.location = location
        args.linkedin = True
        args.browser = True
        args.site = "linkedin"
        
        await self.search_jobs(args)
    
    async def _interactive_apply(self):
        """Interactive job application."""
        job_desc = input("Enter job description or path to file: ").strip()
        resume = input("Enter resume path (default: Rayyan_Ahmed_Resume_2025.pdf): ").strip() or "Rayyan_Ahmed_Resume_2025.pdf"
        threshold = input("Enter ATS threshold (default: 80): ").strip() or "80"
        
        # Create mock args object
        class MockArgs:
            pass
        args = MockArgs()
        args.job_desc = job_desc
        args.resume = resume
        args.threshold = float(threshold)
        args.job_title = ""
        args.company = ""
        args.external_url = None
        args.no_apply = False
        
        await self.apply_to_job(args)
    
    def _interactive_optimize(self):
        """Interactive resume optimization."""
        resume = input("Enter resume path: ").strip()
        job_desc = input("Enter job description or path to file: ").strip()
        
        # Create mock args object
        class MockArgs:
            pass
        args = MockArgs()
        args.resume = resume
        args.job_desc = job_desc
        args.optimize = True
        args.target_score = 0.75
        args.format = "docx"
        
        self.optimize_resume(args)
    
    def _interactive_status(self):
        """Interactive status check."""
        app_id = input("Enter application ID (or press Enter for recent): ").strip()
        
        # Create mock args object
        class MockArgs:
            pass
        args = MockArgs()
        args.id = app_id if app_id else None
        args.count = 10
        
        self.check_status(args)
    
    def _interactive_report(self):
        """Interactive report generation."""
        format_choice = input("Enter format (html/json/text, default: html): ").strip() or "html"
        
        # Create mock args object
        class MockArgs:
            pass
        args = MockArgs()
        args.format = format_choice
        args.output = None
        args.open = True
        
        self.generate_report(args)

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Job Application Automation System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search for jobs
  python cli.py search --keywords "python,ai" --location "Remote"
  
  # Apply to a job
  python cli.py apply --job-desc "job_description.txt" --resume "resume.pdf"
  
  # Optimize resume
  python cli.py optimize --resume "resume.pdf" --job-desc "job_description.txt"
  
  # Check status
  python cli.py status --count 5
  
  # Generate report
  python cli.py report --format html --open
  
  # Interactive mode
  python cli.py interactive
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search for jobs")
    search_parser.add_argument("--keywords", help="Job keywords (comma-separated)")
    search_parser.add_argument("--location", help="Job location")
    search_parser.add_argument("--linkedin", action="store_true", default=True, help="Use LinkedIn")
    search_parser.add_argument("--browser", action="store_true", default=True, help="Use browser automation")
    search_parser.add_argument("--site", default="linkedin", choices=["linkedin", "indeed", "glassdoor"], help="Job site to search")
    
    # Apply command
    apply_parser = subparsers.add_parser("apply", help="Apply to a job")
    apply_parser.add_argument("--job-desc", required=True, help="Job description or path to file")
    apply_parser.add_argument("--resume", default="Rayyan_Ahmed_Resume_2025.pdf", help="Path to resume")
    apply_parser.add_argument("--threshold", type=float, default=80, help="ATS score threshold (0-100)")
    apply_parser.add_argument("--job-title", help="Job title")
    apply_parser.add_argument("--company", help="Company name")
    apply_parser.add_argument("--external-url", help="External application URL")
    apply_parser.add_argument("--no-apply", action="store_true", help="Don't submit application")
    
    # Optimize command
    optimize_parser = subparsers.add_parser("optimize", help="Optimize resume")
    optimize_parser.add_argument("--resume", required=True, help="Path to resume")
    optimize_parser.add_argument("--job-desc", required=True, help="Job description or path to file")
    optimize_parser.add_argument("--optimize", action="store_true", help="Generate optimized version")
    optimize_parser.add_argument("--target-score", type=float, default=0.75, help="Target ATS score")
    optimize_parser.add_argument("--format", choices=["docx", "pdf", "txt"], default="docx", help="Output format")
    
    # Batch optimize command
    batch_parser = subparsers.add_parser("batch", help="Batch optimize resumes")
    batch_parser.add_argument("--resumes-dir", required=True, help="Directory containing resumes")
    batch_parser.add_argument("--job-desc", required=True, help="Job description or path to file")
    batch_parser.add_argument("--optimize", action="store_true", help="Generate optimized versions")
    batch_parser.add_argument("--target-score", type=float, default=0.75, help="Target ATS score")
    
    # Report command
    report_parser = subparsers.add_parser("report", help="Generate ATS performance report")
    report_parser.add_argument("--format", choices=["html", "json", "text"], default="html", help="Report format")
    report_parser.add_argument("--output", help="Output file path")
    report_parser.add_argument("--open", action="store_true", help="Open report in browser")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Check application status")
    status_parser.add_argument("--id", help="Application ID to check")
    status_parser.add_argument("--count", type=int, default=10, help="Number of recent applications to show")
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show application statistics")
    
    # Interactive command
    interactive_parser = subparsers.add_parser("interactive", help="Run in interactive mode")
    
    # Database commands (delegate to manage_db)
    db_parser = subparsers.add_parser("db", help="Database management commands")
    db_parser.add_argument("db_command", nargs=argparse.REMAINDER, help="Database command and arguments")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize CLI
    cli = JobApplicationCLI()
    
    try:
        if args.command == "search":
            asyncio.run(cli.search_jobs(args))
        elif args.command == "apply":
            asyncio.run(cli.apply_to_job(args))
        elif args.command == "optimize":
            cli.optimize_resume(args)
        elif args.command == "batch":
            cli.batch_optimize(args)
        elif args.command == "report":
            cli.generate_report(args)
        elif args.command == "status":
            cli.check_status(args)
        elif args.command == "stats":
            cli.show_stats(args)
        elif args.command == "interactive":
            asyncio.run(cli.interactive_mode(args))
        elif args.command == "db":
            # Delegate to database CLI
            sys.argv = ["manage_db"] + args.db_command
            db_cli()
        else:
            parser.print_help()
            
    except KeyboardInterrupt:
        print("\n👋 Operation cancelled by user.")
    except Exception as e:
        logger.error(f"Error in CLI: {e}")
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main() 