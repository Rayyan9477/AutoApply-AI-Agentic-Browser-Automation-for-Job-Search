"""
Command-line runner for job application automation.
"""

import asyncio
import logging
from typing import Any

from job_application_automation.src.core.job_application import JobApplicationAutomation
from job_application_automation.src.utils.error_handling import with_error_handling

# Set up logging
logger = logging.getLogger(__name__)


@with_error_handling(reraise=False)
async def run_job_application_process(args: Any) -> None:
    """
    Run the job application process with the specified arguments.
    
    Args:
        args: Command-line arguments.
    """
    # Initialize the automation system
    automation = JobApplicationAutomation()
    
    # Setup
    setup_success = await automation.setup()
    if not setup_success:
        logger.error("Failed to set up job application automation")
        return
        
    # Search for jobs
    job_listings = await automation.search_jobs(
        keywords=args.keywords,
        location=args.location,
        use_linkedin=not args.no_linkedin,
        use_browser=not args.no_browser,
        job_site=args.job_site
    )
    
    if not job_listings:
        logger.error("No job listings found")
        print("\nNo job listings were found matching your search criteria. Possible solutions:")
        print("1. Try different keywords or location")
        print("2. Check your internet connection")
        print("3. LinkedIn might be rate-limiting access - try again later")
        print("4. Consider signing in to LinkedIn for better results")
        
        # Create a dummy job listing for demonstration purposes if requested
        if args.demo_mode or args.create_samples:
            logger.info("Creating sample job listings for demonstration")
            job_listings = [
                {
                    "job_title": "Sample Software Engineer Position",
                    "company": "Example Tech Company",
                    "location": args.location,
                    "job_description": "This is a sample job description for demonstration purposes. " +
                                      "Requirements: Python, JavaScript, SQL. Experience with cloud platforms preferred.",
                    "url": "https://www.linkedin.com/jobs/",
                    "source": "Sample"
                },
                {
                    "job_title": "Sample Data Scientist",
                    "company": "Demo Analytics Inc.",
                    "location": args.location,
                    "job_description": "Sample data scientist position requiring experience with machine learning, " +
                                      "Python, and data visualization. Must have strong analytical skills.",
                    "url": "https://www.linkedin.com/jobs/",
                    "source": "Sample"
                }
            ]
            print("\nCreated sample job listings for demonstration purposes.")
        else:
            return
        
    # Scrape job details
    job_details = await automation.scrape_job_details(max_jobs=args.max_jobs)
    
    if not job_details and not args.demo_mode and not args.create_samples:
        logger.error("No job details found")
        print("\nCould not retrieve job details. This may happen if:")
        print("1. The job listings don't have enough information")
        print("2. There are connection issues with the job posting websites")
        print("3. The websites have changed their structure")
        return
    
    # If in demo mode and no details were scraped, use the sample listings as details
    if not job_details and (args.demo_mode or args.create_samples):
        job_details = job_listings
    
    # Filter jobs
    required_skills = args.required_skills.split(",") if args.required_skills else None
    excluded_keywords = args.excluded_keywords.split(",") if args.excluded_keywords else None
    
    filtered_jobs = await automation.filter_jobs(
        min_match_score=args.min_match_score,
        required_skills=required_skills,
        excluded_keywords=excluded_keywords
    )
    
    if not filtered_jobs:
        logger.error("No jobs passed the filtering criteria")
        print("\nNo jobs passed the filtering criteria. Consider:")
        print("1. Lowering the minimum match score")
        print("2. Adjusting your required skills")
        print("3. Updating your candidate profile to better match job requirements")
        return
        
    # Generate resumes/cover letters and apply
    applications = await automation.generate_and_apply(
        filtered_jobs=filtered_jobs,
        max_applications=args.max_applications,
        auto_apply=args.auto_apply,
        min_ats_score=args.min_ats_score,
        auto_optimize_resume=args.auto_optimize_resume
    )
    
    logger.info(f"Job application process completed. Applications submitted: {applications}")
    
    if applications > 0:
        print(f"\nSuccessfully submitted {applications} job applications.")
    else:
        print("\nNo applications were submitted. Resume and cover letter files were generated for manual application.")
    
    # Print final stats
    stats = automation.application_tracker.get_application_stats()
    print(f"\nApplication Summary:")
    print(f"- Total jobs processed: {stats['total']}")
    print(f"- Applications submitted: {applications}")
    print(f"- Pending for manual review: {stats.get('pending', 0)}")
    print(f"- Failed applications: {stats.get('failed', 0) + stats.get('error', 0)}")
