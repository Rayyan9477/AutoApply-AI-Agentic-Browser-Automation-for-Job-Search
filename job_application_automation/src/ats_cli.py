#!/usr/bin/env python3
"""
Command-line tool for ATS resume scoring and optimization.
This module provides a simple CLI for scoring and optimizing resumes against job descriptions.
"""

import os
import argparse
import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

# Import project modules
from job_application_automation.src.resume_optimizer import ATSScorer, ResumeOptimizer
from job_application_automation.src.ats_integration import ATSIntegrationManager
from job_application_automation.config.llama_config import LlamaConfig
from job_application_automation.src.utils.path_utils import get_data_path

# Set up logging
_data_dir = get_data_path()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(_data_dir / "ats_cli.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Define paths
DATA_DIR = _data_dir
JOBS_DIR = DATA_DIR / "job_descriptions"
RESUMES_DIR = DATA_DIR / "resumes"

# Create necessary directories
os.makedirs(JOBS_DIR, exist_ok=True)
os.makedirs(RESUMES_DIR, exist_ok=True)


def analyze_resume(resume_path: str, 
                 job_desc_path: str, 
                 optimize: bool = False,
                 target_score: float = 0.75,
                 output_format: str = "docx") -> Dict[str, Any]:
    """
    Analyze and optionally optimize a resume against a job description.
    
    Args:
        resume_path: Path to the resume file
        job_desc_path: Path to the job description file
        optimize: Whether to optimize the resume if score is below target
        target_score: Target ATS score to achieve
        output_format: Output format for optimized resume
        
    Returns:
        Dictionary with analysis results
    """
    try:
        # Load job description
        with open(job_desc_path, 'r', encoding='utf-8') as f:
            job_description = f.read()
        
        # Set up ATS manager
        ats_manager = ATSIntegrationManager()
        ats_manager.load_state()
        
        # Extract job metadata from filename or use defaults
        job_id = f"job_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        job_title = "Job Position"
        company = "Company Name"
        
        # Try to extract company and position from filename
        job_desc_filename = os.path.basename(job_desc_path)
        if "_at_" in job_desc_filename:
            # Format: position_at_company.txt
            position_company = job_desc_filename.split(".")[0]
            parts = position_company.split("_at_")
            if len(parts) == 2:
                job_title = parts[0].replace("_", " ").title()
                company = parts[1].replace("_", " ").title()
        
        # Process job application
        result = ats_manager.process_job_application(
            resume_path=resume_path,
            job_description=job_description,
            job_metadata={
                "job_title": job_title,
                "company": company,
                "job_id": job_id,
                "source": "manual"
            },
            min_score_threshold=target_score,
            auto_optimize=optimize
        )
        
        # Save state for future reference
        ats_manager.save_state()
        
        return result
    
    except Exception as e:
        logger.error(f"Error analyzing resume: {e}")
        return {
            "error": str(e),
            "original_resume": resume_path,
            "should_proceed": False
        }


def save_job_description(job_desc: str, company: str, position: str) -> str:
    """
    Save a job description to a file.
    
    Args:
        job_desc: Job description text
        company: Company name
        position: Job position title
        
    Returns:
        Path to saved job description file
    """
    # Clean up names for filename
    company_name = company.lower().replace(" ", "_")
    position_name = position.lower().replace(" ", "_")
    
    # Create filename
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{position_name}_at_{company_name}_{timestamp}.txt"
    file_path = str(JOBS_DIR / filename)
    
    # Save to file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(job_desc)
    
    logger.info(f"Saved job description to {file_path}")
    return file_path


def batch_analyze_resumes(resumes_dir: str, 
                       job_desc_path: str,
                       optimize: bool = False,
                       target_score: float = 0.75) -> List[Dict[str, Any]]:
    """
    Analyze multiple resumes against a single job description.
    
    Args:
        resumes_dir: Directory containing resumes
        job_desc_path: Path to job description file
        optimize: Whether to optimize resumes
        target_score: Target ATS score
        
    Returns:
        List of analysis results
    """
    results = []
    
    # Load job description
    try:
        with open(job_desc_path, 'r', encoding='utf-8') as f:
            job_description = f.read()
    except Exception as e:
        logger.error(f"Error reading job description: {e}")
        return []
    
    # Set up ATS manager
    ats_manager = ATSIntegrationManager()
    ats_manager.load_state()
    
    # Extract job metadata from filename or use defaults
    job_id = f"job_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    job_title = "Job Position"
    company = "Company Name"
    
    # Try to extract company and position from filename
    job_desc_filename = os.path.basename(job_desc_path)
    if "_at_" in job_desc_filename:
        # Format: position_at_company.txt
        position_company = job_desc_filename.split(".")[0]
        parts = position_company.split("_at_")
        if len(parts) == 2:
            job_title = parts[0].replace("_", " ").title()
            company = parts[1].replace("_", " ").title()
    
    # Get all resume files
    resume_files = []
    for ext in ['.docx', '.pdf', '.txt', '.md']:
        resume_files.extend(list(Path(resumes_dir).glob(f"*{ext}")))
    
    if not resume_files:
        logger.error(f"No resume files found in {resumes_dir}")
        return []
    
    logger.info(f"Found {len(resume_files)} resumes to analyze")
    
    # Process each resume
    for resume_file in resume_files:
        try:
            logger.info(f"Analyzing resume: {resume_file}")
            
            result = ats_manager.process_job_application(
                resume_path=str(resume_file),
                job_description=job_description,
                job_metadata={
                    "job_title": job_title,
                    "company": company,
                    "job_id": f"{job_id}_{resume_file.stem}",
                    "source": "batch"
                },
                min_score_threshold=target_score,
                auto_optimize=optimize
            )
            
            # Add resume filename to result
            result["resume_filename"] = resume_file.name
            
            results.append(result)
            
        except Exception as e:
            logger.error(f"Error analyzing resume {resume_file}: {e}")
    
    # Save state for future reference
    ats_manager.save_state()
    
    # Sort results by score (highest first)
    results.sort(key=lambda x: x.get("original_score", {}).get("overall_score", 0), reverse=True)
    
    return results


def print_analysis_result(result: Dict[str, Any], verbose: bool = False) -> None:
    """
    Print analysis result in a readable format.
    
    Args:
        result: Analysis result dictionary
        verbose: Whether to print detailed information
    """
    print("\n" + "="*80)
    print(f"Resume: {os.path.basename(result['original_resume'])}")
    print(f"Job: {result['job_metadata']['job_title']} at {result['job_metadata']['company']}")
    print("-"*80)
    
    # Print scores
    original_score = result["original_score"]["overall_score"]
    print(f"Original ATS Score: {original_score}%")
    
    if result.get("optimized_score"):
        optimized_score = result["optimized_score"]["overall_score"]
        print(f"Optimized ATS Score: {optimized_score}%")
        print(f"Improvement: {optimized_score - original_score:.1f}%")
        print(f"Optimized Resume: {os.path.basename(result['optimized_resume'])}")
    
    # Print recommendation
    if result["should_proceed"]:
        print("\n✅ RECOMMENDATION: Submit application - ATS score meets threshold")
    else:
        print("\n❌ RECOMMENDATION: Do not submit - ATS score below threshold")
    
    # Print detailed analysis if verbose
    if verbose:
        print("\nDetailed Analysis:")
        print(f"  Keyword Score: {result['original_score']['keyword_score']}%")
        print(f"  Semantic Score: {result['original_score']['semantic_score']}%")
        print(f"  Format Score: {result['original_score']['format_score']}%")
        
        print("\nMissing Keywords:")
        for kw in result["original_score"]["missing_important_keywords"][:5]:
            print(f"  - {kw['keyword']}")
        
        print("\nImprovement Suggestions:")
        for suggestion in result["original_score"]["improvement_suggestions"][:5]:
            print(f"  - {suggestion}")
    
    print(f"\nDetailed report: {result.get('report_path', 'N/A')}")
    print("="*80 + "\n")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="ATS Resume Analyzer and Optimizer")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a resume against a job description")
    analyze_parser.add_argument("--resume", type=str, required=True, help="Path to resume file")
    analyze_parser.add_argument("--job-desc", type=str, required=True, help="Path to job description file")
    analyze_parser.add_argument("--optimize", action="store_true", help="Optimize resume if score is too low")
    analyze_parser.add_argument("--target-score", type=float, default=0.75, help="Target ATS score (0-1)")
    analyze_parser.add_argument("--output-format", type=str, default="docx", 
                             choices=["docx", "txt", "pdf"], help="Output format for optimized resume")
    analyze_parser.add_argument("--verbose", "-v", action="store_true", help="Print detailed analysis")
    
    # batch command
    batch_parser = subparsers.add_parser("batch", help="Analyze multiple resumes against a job description")
    batch_parser.add_argument("--resumes-dir", type=str, required=True, help="Directory containing resumes")
    batch_parser.add_argument("--job-desc", type=str, required=True, help="Path to job description file")
    batch_parser.add_argument("--optimize", action="store_true", help="Optimize resumes if score is too low")
    batch_parser.add_argument("--target-score", type=float, default=0.75, help="Target ATS score (0-1)")
    batch_parser.add_argument("--output-format", type=str, default="docx", 
                           choices=["docx", "txt", "pdf"], help="Output format for optimized resumes")
    batch_parser.add_argument("--verbose", "-v", action="store_true", help="Print detailed analysis")
    
    # save-job command
    save_job_parser = subparsers.add_parser("save-job", help="Save a job description to a file")
    save_job_parser.add_argument("--job-desc", type=str, required=True, help="Job description text or file path")
    save_job_parser.add_argument("--company", type=str, required=True, help="Company name")
    save_job_parser.add_argument("--position", type=str, required=True, help="Job position title")
    
    # report command
    report_parser = subparsers.add_parser("report", help="Generate ATS performance report")
    
    return parser.parse_args()


def main():
    """Main function for the CLI."""
    args = parse_arguments()
    
    if args.command == "analyze":
        # Analyze a single resume
        result = analyze_resume(
            resume_path=args.resume,
            job_desc_path=args.job_desc,
            optimize=args.optimize,
            target_score=args.target_score,
            output_format=args.output_format
        )
        
        print_analysis_result(result, verbose=args.verbose)
        
    elif args.command == "batch":
        # Batch analyze multiple resumes
        results = batch_analyze_resumes(
            resumes_dir=args.resumes_dir,
            job_desc_path=args.job_desc,
            optimize=args.optimize,
            target_score=args.target_score
        )
        
        # Print results summary
        print(f"\nAnalyzed {len(results)} resumes against job description:")
        print(f"File: {args.job_desc}")
        print("\nResults (ranked by ATS score):")
        
        for i, result in enumerate(results, 1):
            score = result.get("original_score", {}).get("overall_score", 0)
            filename = result.get("resume_filename", "Unknown")
            proceed = "✅" if result.get("should_proceed", False) else "❌"
            print(f"{i}. {proceed} {filename} - {score}%")
        
        # Print detailed results if verbose
        if args.verbose:
            for result in results:
                print_analysis_result(result, verbose=True)
        
        print(f"\nDetailed reports saved to {DATA_DIR / 'ats_reports'}")
        
    elif args.command == "save-job":
        # Check if job_desc is a file path or raw text
        if os.path.exists(args.job_desc):
            try:
                with open(args.job_desc, 'r', encoding='utf-8') as f:
                    job_desc_text = f.read()
            except Exception as e:
                print(f"Error reading job description file: {e}")
                return
        else:
            job_desc_text = args.job_desc
        
        # Save job description
        job_desc_path = save_job_description(
            job_desc=job_desc_text,
            company=args.company,
            position=args.position
        )
        
        print(f"Job description saved to: {job_desc_path}")
        
    elif args.command == "report":
        # Generate ATS performance report
        ats_manager = ATSIntegrationManager()
        ats_manager.load_state()
        
        report_path = ats_manager.generate_ats_performance_report()
        
        if report_path:
            print(f"ATS performance report generated: {report_path}")
        else:
            print("Failed to generate ATS performance report")
    
    else:
        print("No command specified. Use -h or --help for usage information.")


if __name__ == "__main__":
    main()