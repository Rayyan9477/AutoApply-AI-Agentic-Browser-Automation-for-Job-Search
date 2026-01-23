#!/usr/bin/env python3
"""
Smart Job Application Script

This script automates the job application process by:
1. Taking a job description as input
2. Scoring the resume against the job description
3. Optimizing the resume if the score is below threshold
4. Submitting the application if the score meets threshold

Usage:
    python smart_apply.py --job-desc "path/to/job_description.txt" --resume "path/to/resume.pdf" 
                         [--threshold 80] [--no-apply] [--external-url URL]
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
import asyncio
import webbrowser
from datetime import datetime

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

# Import project modules
from src.ats_integration import ATSIntegrationManager
from src.job_sources.linkedin_integration import LinkedInIntegration
from src.resume_optimizer import ATSScorer, ResumeOptimizer
from src.application_tracker import ApplicationTracker
from job_application_automation.config.llama_config import LlamaConfig

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(project_root, "data", "main.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SmartJobApplicant:
    """
    Class to handle the smart job application workflow.
    """
    
    def __init__(self, llama_config: Optional[LlamaConfig] = None):
        """Initialize the Smart Job Applicant."""
        self.ats_manager = ATSIntegrationManager(llama_config)
        self.linkedin = LinkedInIntegration()
        self.app_tracker = ApplicationTracker()
        self.score_threshold = 0.8  # Default 80% threshold
        
    async def process_job(self,
                     resume_path: str,
                     job_description: str,
                     job_metadata: Dict[str, Any],
                     score_threshold: float = 0.8,
                     auto_apply: bool = True,
                     external_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a job application using the smart workflow.
        
        Args:
            resume_path: Path to the resume file
            job_description: The job description text
            job_metadata: Dictionary with job metadata (title, company, etc.)
            score_threshold: ATS score threshold to proceed (0.0-1.0)
            auto_apply: Whether to attempt automatic application
            external_url: URL for external job application
            
        Returns:
            Dictionary with process results
        """
        logger.info(f"Processing job: {job_metadata.get('job_title')} at {job_metadata.get('company')}")
        
        # 1. Process through ATS and optimize if needed
        ats_result = self.ats_manager.process_job_application(
            resume_path=resume_path,
            job_description=job_description,
            job_metadata=job_metadata,
            min_score_threshold=score_threshold,
            auto_optimize=True
        )
        
        # 2. Determine if we should proceed with application
        if not ats_result["should_proceed"]:
            logger.warning(f"ATS score below threshold ({score_threshold*100}%), not proceeding with application")
            result = {
                "success": False,
                "message": f"ATS score too low: {ats_result['original_score']['overall_score']}%",
                "ats_result": ats_result
            }
            
            # Track in application tracker
            self.app_tracker.add_application(
                job_title=job_metadata.get("job_title", "Unknown"),
                company=job_metadata.get("company", "Unknown"),
                status="rejected",
                reason=f"ATS score below threshold: {ats_result['original_score']['overall_score']}%",
                url=job_metadata.get("url", external_url),
                application_data={
                    "resume_path": resume_path,
                    "ats_report": ats_result["report_path"]
                }
            )
            
            return result
        
        # 3. Determine which resume to use (original or optimized)
        selected_resume = ats_result.get("optimized_resume", resume_path) or resume_path
        
        # 4. Track the application attempt
        application_id = self.app_tracker.add_application(
            job_title=job_metadata.get("job_title", "Unknown"),
            company=job_metadata.get("company", "Unknown"),
            status="in_progress",
            url=job_metadata.get("url", external_url),
            application_data={
                "resume_path": selected_resume,
                "ats_report": ats_result["report_path"]
            }
        )
        
        # 5. Determine application approach based on job source
        if not auto_apply:
            # Just prepare materials but don't apply
            result = {
                "success": True,
                "applied": False,
                "message": "Resume optimized but auto-apply disabled",
                "resume_path": selected_resume,
                "ats_result": ats_result,
                "application_id": application_id
            }
            
            # Update application tracker
            self.app_tracker.update_application(
                application_id=application_id,
                status="prepared",
                notes="Resume optimized but auto-apply disabled"
            )
            
            return result
        
        # 6. Try to apply (LinkedIn or external)
        try:
            # A. Check if it's a LinkedIn job
            if job_metadata.get("source") == "linkedin" and job_metadata.get("job_id"):
                # Authenticate with LinkedIn
                authenticated = await self.linkedin.authenticate()
                if authenticated:
                    # Apply via LinkedIn
                    cover_letter_path = None  # Add cover letter generation if needed
                    
                    success = await self.linkedin.apply_to_job(
                        job_id=job_metadata["job_id"],
                        resume_path=selected_resume,
                        cover_letter_path=cover_letter_path
                    )
                    
                    if success:
                        self.app_tracker.update_application(
                            application_id=application_id,
                            status="applied",
                            notes=f"Successfully applied via LinkedIn on {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                        )
                        
                        result = {
                            "success": True,
                            "applied": True,
                            "message": "Successfully applied via LinkedIn",
                            "resume_path": selected_resume,
                            "ats_result": ats_result,
                            "application_id": application_id
                        }
                    else:
                        self.app_tracker.update_application(
                            application_id=application_id,
                            status="failed",
                            notes=f"Failed to apply via LinkedIn on {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                        )
                        
                        result = {
                            "success": False,
                            "applied": False,
                            "message": "Failed to apply via LinkedIn",
                            "resume_path": selected_resume,
                            "ats_result": ats_result,
                            "application_id": application_id
                        }
                else:
                    # LinkedIn auth failed
                    self.app_tracker.update_application(
                        application_id=application_id,
                        status="pending",
                        notes="LinkedIn authentication failed, manual application required"
                    )
                    
                    result = {
                        "success": False,
                        "applied": False,
                        "message": "LinkedIn authentication failed",
                        "resume_path": selected_resume,
                        "ats_result": ats_result,
                        "application_id": application_id
                    }
            
            # B. External URL provided
            elif external_url:
                # Open browser to the application URL
                webbrowser.open(external_url)
                
                self.app_tracker.update_application(
                    application_id=application_id,
                    status="in_progress",
                    notes=f"Browser opened to {external_url} for manual application completion"
                )
                
                result = {
                    "success": True,
                    "applied": False,
                    "message": "Browser opened for external application",
                    "resume_path": selected_resume,
                    "external_url": external_url,
                    "ats_result": ats_result,
                    "application_id": application_id
                }
            
            # C. No application method available
            else:
                self.app_tracker.update_application(
                    application_id=application_id,
                    status="pending",
                    notes="No application method available"
                )
                
                result = {
                    "success": False,
                    "applied": False,
                    "message": "No application method available",
                    "resume_path": selected_resume,
                    "ats_result": ats_result,
                    "application_id": application_id
                }
                
        except Exception as e:
            logger.error(f"Error during application process: {e}")
            
            self.app_tracker.update_application(
                application_id=application_id,
                status="error",
                notes=f"Error during application: {str(e)}"
            )
            
            result = {
                "success": False,
                "applied": False,
                "message": f"Error during application: {str(e)}",
                "resume_path": selected_resume,
                "ats_result": ats_result,
                "application_id": application_id
            }
        
        return result
    
    def get_application_status(self, application_id: str) -> Dict[str, Any]:
        """
        Get the status of an application.
        
        Args:
            application_id: Application ID to check
            
        Returns:
            Dictionary with application status information
        """
        return self.app_tracker.get_application(application_id)
    
    def generate_ats_report(self, format: str = "html", output_path: Optional[str] = None) -> str:
        """
        Generate overall ATS performance report.
        
        Args:
            format: Report format ("html", "json", or "text")
            output_path: Optional output file path
            
        Returns:
            Path to the generated report
        """
        return self.ats_manager.generate_ats_performance_report(format, output_path)


async def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Smart Job Application Script")
    
    # Create subparsers for different command modes
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Apply command - for applying to jobs
    apply_parser = subparsers.add_parser("apply", help="Apply to a job")
    apply_parser.add_argument("--job-desc", type=str, help="Path to job description file or raw job description")
    apply_parser.add_argument("--resume", type=str, default="Rayyan_Ahmed_Resume_2025.pdf", 
                            help="Path to resume file (default: Rayyan_Ahmed_Resume_2025.pdf)")
    apply_parser.add_argument("--threshold", type=float, default=80,
                            help="ATS score threshold percentage (default: 80)")
    apply_parser.add_argument("--no-apply", action="store_true",
                            help="Don't auto-apply, just optimize resume")
    apply_parser.add_argument("--external-url", type=str,
                            help="URL for external job application")
    apply_parser.add_argument("--job-title", type=str, default="",
                            help="Job title")
    apply_parser.add_argument("--company", type=str, default="",
                            help="Company name")
    
    # Report command - for generating reports
    report_parser = subparsers.add_parser("report", help="Generate ATS performance report")
    report_parser.add_argument("--format", choices=["html", "json", "text"], default="html",
                             help="Report output format (default: html)")
    report_parser.add_argument("--output", type=str,
                             help="Output file path (defaults to data/ats_reports/)")
    
    # Status command - for checking application status
    status_parser = subparsers.add_parser("status", help="Check application status")
    status_parser.add_argument("--id", type=str, help="Application ID to check")
    status_parser.add_argument("--all", action="store_true", help="Show all applications")
    status_parser.add_argument("--count", type=int, default=10, 
                             help="Number of recent applications to show (default: 10)")
    
    # Interactive mode
    interactive_parser = subparsers.add_parser("interactive", help="Run in interactive mode")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Determine default command if none provided
    if not args.command:
        # Default to interactive mode if no command-line arguments
        if len(sys.argv) <= 1:
            args.command = "interactive"
        else:
            # For backward compatibility, assume "apply" if job-desc is provided
            args.command = "apply" 
    
    # Create smart applicant
    applicant = SmartJobApplicant()
    
    # Handle different commands
    if args.command == "report":
        # Generate ATS report
        report_path = applicant.generate_ats_report(format=getattr(args, "format", "html"), 
                                                  output_path=getattr(args, "output", None))
        if report_path:
            print(f"Generated ATS performance report: {report_path}")
            
            # Open the report in browser if it's HTML
            if getattr(args, "format", "html") == "html":
                webbrowser.open(f"file://{os.path.abspath(report_path)}")
        else:
            print("Failed to generate ATS performance report")
            
    elif args.command == "status":
        # Check application status
        if getattr(args, "id", None):
            # Show specific application
            app_status = applicant.get_application_status(args.id)
            if app_status:
                print_application_status(app_status)
            else:
                print(f"No application found with ID: {args.id}")
        elif getattr(args, "all", False) or getattr(args, "count", 0) > 0:
            # Show all or recent applications
            count = -1 if getattr(args, "all", False) else getattr(args, "count", 10)
            applications = applicant.app_tracker.get_recent_applications(count)
            
            if not applications:
                print("No applications found")
            else:
                print(f"\nFound {len(applications)} application(s):")
                for app in applications:
                    print("\n" + "="*50)
                    print_application_status(app)
        else:
            print("Please specify --id, --all, or --count")
            
    elif args.command == "interactive":
        # Run interactive mode
        await run_interactive_mode(applicant)
        
    elif args.command == "apply":
        # Process job application (traditional mode)
        await process_job_application(args, applicant)
    else:
        parser.print_help()


def print_application_status(status):
    """Print formatted application status."""
    print(f"Application ID: {status.get('id', 'Unknown')}")
    print(f"Job Title: {status.get('job_title', 'Unknown')}")
    print(f"Company: {status.get('company', 'Unknown')}")
    print(f"Status: {status.get('status', 'Unknown')}")
    print(f"Created: {status.get('created_at', 'Unknown')}")
    print(f"Updated: {status.get('updated_at', 'Unknown')}")
    
    # Show URL if available
    if status.get('url'):
        print(f"URL: {status.get('url')}")
        
    # Show notes if available
    if status.get('notes'):
        print(f"Notes: {status.get('notes')}")
        
    # Show reason if available
    if status.get('reason'):
        print(f"Reason: {status.get('reason')}")


async def process_job_application(args, applicant):
    """Process a job application using command line arguments."""
    # Check required arguments
    if not args.job_desc:
        print("Error: Job description is required")
        return
    
    # Load resume path
    resume_path = args.resume
    if not os.path.isabs(args.resume):
        resume_path = os.path.join(project_root, args.resume)
    
    if not os.path.exists(resume_path):
        print(f"Error: Resume file not found: {resume_path}")
        return
    
    # Check if job description is a file or raw text
    job_description = args.job_desc
    if os.path.exists(args.job_desc):
        with open(args.job_desc, 'r', encoding='utf-8') as f:
            job_description = f.read()
    
    # Create job metadata
    job_title = args.job_title or "Job Position"
    company = args.company or "Company"
    
    job_metadata = {
        "job_title": job_title,
        "company": company,
        "url": args.external_url,
        "job_id": f"manual_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    }
    
    # Process job
    result = await applicant.process_job(
        resume_path=resume_path,
        job_description=job_description,
        job_metadata=job_metadata,
        score_threshold=args.threshold / 100.0,  # Convert percentage to decimal
        auto_apply=not args.no_apply,
        external_url=args.external_url
    )
    
    # Print result
    print("\n=== Smart Job Application Results ===")
    
    if result.get("ats_result"):
        ats_score = result["ats_result"]["original_score"]["overall_score"]
        print(f"Original ATS Score: {ats_score}%")
        
        if result["ats_result"].get("optimized_score"):
            opt_score = result["ats_result"]["optimized_score"]["overall_score"]
            print(f"Optimized ATS Score: {opt_score}%")
    
    print(f"Status: {'Success' if result['success'] else 'Failed'}")
    print(f"Message: {result['message']}")
    
    if result.get("resume_path"):
        print(f"Resume used: {result['resume_path']}")
    
    if result.get("application_id"):
        print(f"Application ID: {result['application_id']}")
        
    # Open ATS report if available
    if result.get("ats_result", {}).get("report_path"):
        report_path = result["ats_result"]["report_path"]
        print(f"ATS Report: {report_path}")
        
        # Ask if user wants to view the report
        view_report = input("Do you want to view the ATS report? (y/n): ")
        if view_report.lower() == 'y':
            webbrowser.open(f"file://{os.path.abspath(report_path)}")
    
    # Continue applying?
    if not args.no_apply and not result.get("applied", False):
        continue_app = input("Do you want to manually complete this application? (y/n): ")
        if continue_app.lower() == 'y' and args.external_url:
            webbrowser.open(args.external_url)
        elif continue_app.lower() == 'y' and result.get("job", {}).get("url"):
            webbrowser.open(result["job"]["url"])
        elif continue_app.lower() == 'y':
            print("No application URL available. Please apply manually.")
            
    # Check if user wants to review application status
    if result.get("application_id"):
        check_status = input("Do you want to see detailed application status? (y/n): ")
        if check_status.lower() == 'y':
            app_status = applicant.get_application_status(result["application_id"])
            print_application_status(app_status)


async def run_interactive_mode(applicant):
    """Run the application in interactive mode with command menu."""
    print("\n=== Smart Job Applicant - Interactive Mode ===")
    
    while True:
        print("\nAvailable commands:")
        print("1. Apply to job")
        print("2. Generate ATS performance report")
        print("3. Check application status")
        print("4. List recent applications")
        print("5. Exit")
        
        choice = input("\nEnter your choice (1-5): ")
        
        if choice == "1":
            await interactive_apply_to_job(applicant)
        elif choice == "2":
            interactive_generate_report(applicant)
        elif choice == "3":
            interactive_check_status(applicant)
        elif choice == "4":
            interactive_list_recent(applicant)
        elif choice == "5":
            print("Exiting Smart Job Applicant. Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")


async def interactive_apply_to_job(applicant):
    """Interactive job application process."""
    print("\n=== Apply to Job ===")
    
    # Get job description
    print("\nHow would you like to provide the job description?")
    print("1. Enter job description text")
    print("2. From a file")
    desc_choice = input("Choice (1-2): ")
    
    job_description = ""
    if desc_choice == "1":
        print("\nEnter job description (type END on a new line to finish):")
        while True:
            line = input()
            if line == "END":
                break
            job_description += line + "\n"
    elif desc_choice == "2":
        file_path = input("Enter path to job description file: ")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                job_description = f.read()
        except Exception as e:
            print(f"Error reading file: {e}")
            return
    else:
        print("Invalid choice.")
        return
    
    # Get resume
    resume_path = input("\nEnter path to resume file (or press Enter for default): ")
    if not resume_path:
        resume_path = os.path.join(project_root, "Rayyan_Ahmed_Resume_2025.pdf")
    elif not os.path.isabs(resume_path):
        resume_path = os.path.join(project_root, resume_path)
        
    if not os.path.exists(resume_path):
        print(f"Error: Resume file not found: {resume_path}")
        return
    
    # Get job metadata
    job_title = input("Enter job title: ")
    company = input("Enter company name: ")
    external_url = input("Enter application URL (optional): ")
    
    # Get threshold
    threshold_str = input("Enter ATS score threshold (1-100, default 80): ")
    try:
        threshold = float(threshold_str) if threshold_str else 80
    except ValueError:
        print("Invalid threshold. Using default of 80.")
        threshold = 80
        
    # Auto-apply option
    auto_apply_str = input("Attempt automatic application if possible? (y/n, default: n): ")
    auto_apply = auto_apply_str.lower() == 'y'
    
    # Create job metadata
    job_metadata = {
        "job_title": job_title,
        "company": company,
        "url": external_url,
        "job_id": f"manual_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    }
    
    print("\nProcessing job application...")
    
    # Process job
    result = await applicant.process_job(
        resume_path=resume_path,
        job_description=job_description,
        job_metadata=job_metadata,
        score_threshold=threshold / 100.0,
        auto_apply=auto_apply,
        external_url=external_url
    )
    
    # Print result
    print("\n=== Smart Job Application Results ===")
    
    if result.get("ats_result"):
        ats_score = result["ats_result"]["original_score"]["overall_score"]
        print(f"Original ATS Score: {ats_score}%")
        
        if result["ats_result"].get("optimized_score"):
            opt_score = result["ats_result"]["optimized_score"]["overall_score"]
            print(f"Optimized ATS Score: {opt_score}%")
    
    print(f"Status: {'Success' if result['success'] else 'Failed'}")
    print(f"Message: {result['message']}")
    
    if result.get("resume_path"):
        print(f"Resume used: {result['resume_path']}")
    
    if result.get("application_id"):
        print(f"Application ID: {result['application_id']}")
        
    # Open ATS report if available
    if result.get("ats_result", {}).get("report_path"):
        report_path = result["ats_result"]["report_path"]
        print(f"ATS Report: {report_path}")
        
        # Ask if user wants to view the report
        view_report = input("Do you want to view the ATS report? (y/n): ")
        if view_report.lower() == 'y':
            webbrowser.open(f"file://{os.path.abspath(report_path)}")


def interactive_generate_report(applicant):
    """Generate ATS performance report interactively."""
    print("\n=== Generate ATS Performance Report ===")
    
    # Get report format
    print("Select report format:")
    print("1. HTML (default)")
    print("2. JSON")
    print("3. Text")
    format_choice = input("Choice (1-3): ")
    
    if format_choice == "2":
        report_format = "json"
    elif format_choice == "3":
        report_format = "text"
    else:
        report_format = "html"
        
    # Get output path (optional)
    output_path = input("Enter output path (or press Enter for default): ")
    
    # Generate report
    report_path = applicant.generate_ats_report(format=report_format, output_path=output_path)
    
    if report_path:
        print(f"Generated ATS performance report: {report_path}")
        
        # Open the report if it's HTML
        if report_format == "html":
            open_report = input("Open report in browser? (y/n): ")
            if open_report.lower() == 'y':
                webbrowser.open(f"file://{os.path.abspath(report_path)}")
    else:
        print("Failed to generate ATS performance report")


def interactive_check_status(applicant):
    """Check application status interactively."""
    print("\n=== Check Application Status ===")
    
    app_id = input("Enter application ID: ")
    if not app_id:
        print("No application ID provided")
        return
        
    app_status = applicant.get_application_status(app_id)
    if app_status:
        print_application_status(app_status)
    else:
        print(f"No application found with ID: {app_id}")


def interactive_list_recent(applicant):
    """List recent applications interactively."""
    print("\n=== List Recent Applications ===")
    
    count_str = input("Number of applications to show (default: 10): ")
    try:
        count = int(count_str) if count_str else 10
    except ValueError:
        print("Invalid number. Using default of 10.")
        count = 10
        
    applications = applicant.app_tracker.get_recent_applications(count)
    
    if not applications:
        print("No applications found")
    else:
        print(f"\nFound {len(applications)} recent application(s):")
        for app in applications:
            print("\n" + "="*50)
            print_application_status(app)


if __name__ == "__main__":
    import re
    import sys
    import webbrowser
    from datetime import datetime
    
    # Fix missing imports
    try:
        import asyncio
    except ImportError:
        print("Error: asyncio package is required but not found.")
        sys.exit(1)
        
    try:
        import argparse
    except ImportError:
        print("Error: argparse package is required but not found.")
        sys.exit(1)
        
    asyncio.run(main())