"""
ATS integration module for job application automation.
This module integrates ATS scoring and optimization with the job application process.
"""

import os
import json
import logging
import tempfile
import shutil
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for headless environments
import matplotlib.pyplot as plt
from datetime import datetime

# Import project modules
from job_application_automation.src.resume_optimizer import ATSScorer, ResumeOptimizer
from job_application_automation.src.application_tracker import ApplicationTracker
from job_application_automation.config.llama_config import LlamaConfig

# Import for GitHub token-based Llama 4 integration
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential

# Set up logging
from job_application_automation.src.utils.path_utils import get_data_path as _get_data_path
_data_dir = _get_data_path()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(_data_dir / "ats_integration.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Define paths
DATA_DIR = _data_dir
REPORTS_DIR = DATA_DIR / "ats_reports"
os.makedirs(REPORTS_DIR, exist_ok=True)

class ATSIntegrationManager:
    """
    Manager class for ATS integration in the job application process.
    """
    
    def __init__(self, llm_config=None):
        """
        Initialize the ATS Integration Manager with the given configuration.
        
        Args:
            llm_config: Configuration for LLM integration. If None, default settings will be used.
        """
        # Use LlamaConfig directly
        if llm_config:
            self.llama_config = llm_config
        else:
            self.llama_config = LlamaConfig()
        
        # Initialize components
        self.scorer = ATSScorer()
        self.optimizer = ResumeOptimizer(self.llama_config)
        
        # For tracking state
        self.app_tracker = ApplicationTracker()
        self.score_history = []
        self.resume_cache = {}  # Cache for resume scores
        self.state_file = os.path.join(DATA_DIR, "ats_state.json") 
        self.state = {}
        
        # Set up LLM client
        self.llm_client = self._setup_llm_client()
        
    def _setup_llm_client(self):
        """Set up the LLM client based on configuration."""
        if not self.llama_config.use_api:
            logger.info("Using local LLM model")
            return None
            
        if self.llama_config.api_provider == "github":
            logger.info("Setting up Llama 4 with GitHub token")
            try:
                config = self.llama_config.get_api_config()
                token = config.get("token")
                endpoint = config.get("endpoint", "https://models.github.ai/inference")
                model = config.get("model", "meta/Llama-4-Maverick-17B-128E-Instruct-FP8")
                
                if not token:
                    logger.error("GitHub token not found. Set GITHUB_TOKEN environment variable.")
                    return None
                
                client = ChatCompletionsClient(
                    endpoint=endpoint,
                    credential=AzureKeyCredential(token),
                )
                logger.info(f"Successfully set up Llama 4 client with model {model}")
                return {"client": client, "model": model}
            except Exception as e:
                logger.error(f"Failed to set up Llama 4 client: {e}")
                return None
        else:
            logger.info(f"Using {self.llama_config.api_provider} API provider")
            # Other API providers would be set up differently here
            return None
    
    def get_llm_response(self, system_prompt: str, user_prompt: str) -> str:
        """Get a response from the LLM."""
        if not self.llm_client:
            logger.error("LLM client not properly set up")
            return ""
            
        try:
            logger.info("Sending request to Llama 4")
            response = self.llm_client["client"].complete(
                messages=[
                    SystemMessage(system_prompt),
                    UserMessage(user_prompt),
                ],
                temperature=self.llama_config.temperature,
                top_p=self.llama_config.top_p,
                max_tokens=1000,
                model=self.llm_client["model"]
            )
            
            result = response.choices[0].message.content
            logger.info(f"Received {len(result)} characters from LLM")
            return result
        except Exception as e:
            logger.error(f"Error getting LLM response: {e}")
            return ""
        
    def process_job_application(self, 
                             resume_path: str,
                             job_description: str,
                             job_metadata: Dict[str, Any],
                             min_score_threshold: float = 0.7,
                             auto_optimize: bool = True) -> Dict[str, Any]:
        """
        Process a job application with ATS scoring and optimization.
        
        Args:
            resume_path: Path to the resume file
            job_description: Job description text
            job_metadata: Job metadata including title, company, etc.
            min_score_threshold: Minimum ATS score to proceed with application
            auto_optimize: Whether to automatically optimize the resume
            
        Returns:
            Dictionary with processing results
        """
        logger.info(f"Processing job application for {job_metadata.get('job_title', 'Unknown')} "
                   f"at {job_metadata.get('company', 'Unknown')}")
        
        # Score the original resume
        resume_data = self.scorer.parse_resume(resume_path)
        original_score = self.scorer.score_resume(resume_data, job_description)
        
        logger.info(f"Original resume score: {original_score['overall_score']}%")
        
        # Add to score history
        self._add_to_score_history(
            job_metadata.get('job_title', 'Unknown'),
            job_metadata.get('company', 'Unknown'),
            original_score['overall_score'] / 100.0
        )
        
        result = {
            "original_resume": resume_path,
            "original_score": original_score,
            "should_proceed": original_score['overall_score'] / 100.0 >= min_score_threshold,
            "optimized_resume": None,
            "optimized_score": None,
            "job_metadata": job_metadata
        }
        
        # Check if optimization is needed
        if not result["should_proceed"] and auto_optimize:
            logger.info(f"Score below threshold ({min_score_threshold*100}%). Optimizing resume...")
            
            optimization_result = self.optimizer.optimize_resume(
                resume_path, 
                job_description,
                target_score=min_score_threshold
            )
            
            result["optimized_resume"] = optimization_result["optimized_path"]
            result["optimized_score"] = optimization_result["optimized_score"]
            result["keywords_added"] = optimization_result.get("keywords_added", [])
            
            # Update should_proceed based on optimized score
            optimized_score_value = optimization_result["optimized_score"]["overall_score"] / 100.0
            result["should_proceed"] = optimized_score_value >= min_score_threshold
            
            logger.info(f"Optimized resume score: {optimization_result['optimized_score']['overall_score']}%")
            logger.info(f"Should proceed with application: {result['should_proceed']}")
            
            # Add optimized score to history
            self._add_to_score_history(
                job_metadata.get('job_title', 'Unknown'),
                job_metadata.get('company', 'Unknown'),
                optimized_score_value,
                is_optimized=True
            )
        
        # Create report
        report_path = self._generate_application_report(result)
        result["report_path"] = report_path
        
        # Cache result for future reference
        job_id = job_metadata.get('job_id', f"job_{len(self.resume_cache)}")
        self.resume_cache[job_id] = {
            "original_score": original_score,
            "optimized_score": result.get("optimized_score"),
            "resume_path": resume_path,
            "optimized_path": result.get("optimized_resume"),
            "timestamp": datetime.now().isoformat()
        }
        
        return result
    
    def _add_to_score_history(self, job_title: str, company: str, score: float, is_optimized: bool = False) -> None:
        """Add a score to the history for tracking and analysis."""
        self.score_history.append({
            "job_title": job_title,
            "company": company,
            "score": score,
            "is_optimized": is_optimized,
            "timestamp": datetime.now().isoformat()
        })
    
    def _generate_application_report(self, result: Dict[str, Any]) -> str:
        """Generate a detailed report for the job application ATS analysis."""
        try:
            job_title = result["job_metadata"].get("job_title", "Unknown")
            company = result["job_metadata"].get("company", "Unknown")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            report_filename = f"ats_report_{company.replace(' ', '_')}_{timestamp}.html"
            report_path = str(REPORTS_DIR / report_filename)
            
            # Create HTML report
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(f"""
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>ATS Analysis Report - {job_title} at {company}</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; color: #333; }}
                        .container {{ max-width: 900px; margin: 0 auto; }}
                        .header {{ background-color: #f4f4f4; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
                        .header h1 {{ margin: 0; color: #2c3e50; }}
                        .score-card {{ display: flex; margin-bottom: 20px; }}
                        .score-box {{ flex: 1; padding: 15px; border-radius: 5px; margin-right: 10px; }}
                        .original {{ background-color: #e8f4f8; }}
                        .optimized {{ background-color: #e8f8ea; }}
                        .score-value {{ font-size: 36px; font-weight: bold; margin: 10px 0; }}
                        .keywords {{ background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                        .keywords h3 {{ margin-top: 0; }}
                        .keyword-list {{ display: flex; flex-wrap: wrap; }}
                        .keyword-item {{ background-color: #e0e0e0; padding: 5px 10px; border-radius: 15px; margin: 5px; }}
                        .matched {{ background-color: #d4edda; }}
                        .missing {{ background-color: #f8d7da; }}
                        .suggestions {{ background-color: #fff3cd; padding: 15px; border-radius: 5px; }}
                        .improvement {{ margin-bottom: 10px; padding-left: 20px; position: relative; }}
                        .improvement:before {{ content: "→"; position: absolute; left: 0; }}
                        .proceed {{ padding: 15px; border-radius: 5px; font-weight: bold; text-align: center; margin-top: 20px; }}
                        .proceed-yes {{ background-color: #d4edda; }}
                        .proceed-no {{ background-color: #f8d7da; }}
                        .footer {{ text-align: center; margin-top: 30px; font-size: 0.9em; color: #777; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>ATS Analysis Report</h1>
                            <p>Job Title: <strong>{job_title}</strong> at <strong>{company}</strong></p>
                            <p>Date: {datetime.now().strftime("%B %d, %Y %H:%M")}</p>
                        </div>
                        
                        <div class="score-card">
                            <div class="score-box original">
                                <h2>Original Resume Score</h2>
                                <div class="score-value">{result["original_score"]["overall_score"]}%</div>
                                <p>Keyword Score: {result["original_score"]["keyword_score"]}%</p>
                                <p>Semantic Score: {result["original_score"]["semantic_score"]}%</p>
                                <p>Format Score: {result["original_score"]["format_score"]}%</p>
                            </div>
                """)
                
                # Add optimized score if available
                if result.get("optimized_score"):
                    f.write(f"""
                            <div class="score-box optimized">
                                <h2>Optimized Resume Score</h2>
                                <div class="score-value">{result["optimized_score"]["overall_score"]}%</div>
                                <p>Keyword Score: {result["optimized_score"]["keyword_score"]}%</p>
                                <p>Semantic Score: {result["optimized_score"]["semantic_score"]}%</p>
                                <p>Format Score: {result["optimized_score"]["format_score"]}%</p>
                            </div>
                    """)
                
                f.write("""
                        </div>
                        
                        <div class="keywords">
                            <h3>Keyword Analysis</h3>
                """)
                
                # Add matched keywords
                f.write("""
                            <h4>Matched Keywords</h4>
                            <div class="keyword-list">
                """)
                
                for kw in result["original_score"]["matched_keywords"][:15]:  # Limit to top 15
                    weight = round(kw["weight"] * 100)
                    f.write(f'<span class="keyword-item matched">{kw["keyword"]} ({weight}%)</span>\n')
                
                f.write("""
                            </div>
                            
                            <h4>Missing Important Keywords</h4>
                            <div class="keyword-list">
                """)
                
                # Add missing keywords
                for kw in result["original_score"]["missing_important_keywords"]:
                    weight = round(kw["weight"] * 100)
                    f.write(f'<span class="keyword-item missing">{kw["keyword"]} ({weight}%)</span>\n')
                
                f.write("""
                            </div>
                        </div>
                        
                        <div class="suggestions">
                            <h3>Improvement Suggestions</h3>
                """)
                
                # Add suggestions
                for suggestion in result["original_score"]["improvement_suggestions"]:
                    f.write(f'<div class="improvement">{suggestion}</div>\n')
                
                # Add application recommendation
                proceed_class = "proceed-yes" if result["should_proceed"] else "proceed-no"
                proceed_text = "Recommended to Proceed" if result["should_proceed"] else "Not Recommended to Proceed"
                
                f.write(f"""
                        </div>
                        
                        <div class="proceed {proceed_class}">
                            {proceed_text}
                        </div>
                        
                        <div class="footer">
                            <p>Generated by Job Application Automation System</p>
                            <p>Resume file: {os.path.basename(result["original_resume"])}</p>
                """)
                
                if result.get("optimized_resume"):
                    f.write(f'<p>Optimized resume: {os.path.basename(result["optimized_resume"])}</p>\n')
                
                f.write("""
                        </div>
                    </div>
                </body>
                </html>
                """)
            
            logger.info(f"Generated ATS report: {report_path}")
            return report_path
            
        except Exception as e:
            logger.error(f"Error generating application report: {e}")
            return ""
    
    def get_best_resume_for_job(self, job_description: str) -> Optional[str]:
        """
        Find the best resume from cache for a similar job description.
        
        Args:
            job_description: Job description text to match
            
        Returns:
            Path to the best matching resume, or None if no good match found
        """
        try:
            similar_resumes = self.scorer.find_similar_resumes(job_description)
            
            if similar_resumes:
                # Get highest scored resume
                best_match = max(similar_resumes, key=lambda x: x["score"])
                
                # Check if it's a good match
                if best_match["score"] >= 0.7 and best_match["similarity"] >= 0.75:
                    logger.info(f"Found good resume match with score {best_match['score']:.2f} "
                              f"and similarity {best_match['similarity']:.2f}")
                    return best_match["resume_path"]
            
            logger.info("No good resume match found")
            return None
            
        except Exception as e:
            logger.error(f"Error finding best resume for job: {e}")
            return None
    
    def generate_ats_performance_report(self) -> str:
        """
        Generate a report showing ATS performance over time.
        
        Returns:
            Path to the generated report
        """
        if not self.score_history:
            logger.warning("No score history available for report generation")
            return ""
        
        try:
            # Convert history to DataFrame
            df = pd.DataFrame(self.score_history)
            df["date"] = pd.to_datetime(df["timestamp"])
            
            # Generate timestamp for filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_filename = f"ats_performance_{timestamp}"
            
            # Create charts directory
            charts_dir = REPORTS_DIR / "charts"
            os.makedirs(charts_dir, exist_ok=True)
            
            # Generate score trend chart
            plt.figure(figsize=(10, 6))
            plt.plot(df["date"], df["score"] * 100, marker='o')
            plt.title("ATS Score Trend Over Time")
            plt.xlabel("Date")
            plt.ylabel("Score (%)")
            plt.grid(True, linestyle='--', alpha=0.7)
            plt.tight_layout()
            chart_path = str(charts_dir / f"{report_filename}_trend.png")
            plt.savefig(chart_path)
            plt.close()
            
            # Generate optimization comparison chart if we have optimized scores
            if any(df["is_optimized"]):
                # Group and calculate average scores
                original_avg = df[~df["is_optimized"]]["score"].mean() * 100
                optimized_avg = df[df["is_optimized"]]["score"].mean() * 100
                
                plt.figure(figsize=(8, 6))
                bars = plt.bar(["Original", "Optimized"], [original_avg, optimized_avg], color=['#6c757d', '#28a745'])
                plt.title("Average ATS Score: Original vs. Optimized Resumes")
                plt.ylabel("Average Score (%)")
                plt.ylim(0, 100)
                
                # Add values on top of bars
                for bar in bars:
                    height = bar.get_height()
                    plt.text(bar.get_x() + bar.get_width()/2., height + 1,
                            f"{height:.1f}%", ha='center', va='bottom')
                
                plt.tight_layout()
                comp_chart_path = str(charts_dir / f"{report_filename}_comparison.png")
                plt.savefig(comp_chart_path)
                plt.close()
            
            # Generate HTML report
            report_path = str(REPORTS_DIR / f"{report_filename}.html")
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(f"""
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>ATS Performance Report</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; color: #333; }}
                        .container {{ max-width: 900px; margin: 0 auto; }}
                        .header {{ background-color: #f4f4f4; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
                        .header h1 {{ margin: 0; color: #2c3e50; }}
                        .chart {{ margin-bottom: 30px; background-color: white; padding: 15px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                        .chart img {{ max-width: 100%; height: auto; display: block; margin: 0 auto; }}
                        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
                        th {{ background-color: #f2f2f2; }}
                        tr:hover {{ background-color: #f5f5f5; }}
                        .footer {{ text-align: center; margin-top: 30px; font-size: 0.9em; color: #777; }}
                        .stats {{ display: flex; justify-content: space-between; margin-bottom: 20px; }}
                        .stat-box {{ flex: 1; padding: 15px; background-color: #f9f9f9; margin-right: 10px; border-radius: 5px; text-align: center; }}
                        .stat-box:last-child {{ margin-right: 0; }}
                        .stat-value {{ font-size: 24px; font-weight: bold; margin: 10px 0; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>ATS Performance Report</h1>
                            <p>Generated on: {datetime.now().strftime("%B %d, %Y %H:%M")}</p>
                        </div>
                        
                        <div class="stats">
                            <div class="stat-box">
                                <h3>Total Resumes Analyzed</h3>
                                <div class="stat-value">{len(df[~df["is_optimized"]])}</div>
                            </div>
                            <div class="stat-box">
                                <h3>Average Original Score</h3>
                                <div class="stat-value">{df[~df["is_optimized"]]["score"].mean()*100:.1f}%</div>
                            </div>
                """)
                
                # Add optimized stats if available
                if any(df["is_optimized"]):
                    f.write(f"""
                            <div class="stat-box">
                                <h3>Resumes Optimized</h3>
                                <div class="stat-value">{len(df[df["is_optimized"]])}</div>
                            </div>
                            <div class="stat-box">
                                <h3>Average After Optimization</h3>
                                <div class="stat-value">{df[df["is_optimized"]]["score"].mean()*100:.1f}%</div>
                            </div>
                    """)
                
                f.write("""
                        </div>
                        
                        <div class="chart">
                            <h2>ATS Score Trend</h2>
                """)
                
                # Add trend chart
                rel_path = os.path.relpath(chart_path, os.path.dirname(report_path))
                f.write(f'<img src="{rel_path}" alt="ATS Score Trend">\n')
                
                # Add comparison chart if available
                if any(df["is_optimized"]) and os.path.exists(comp_chart_path):
                    rel_comp_path = os.path.relpath(comp_chart_path, os.path.dirname(report_path))
                    f.write(f"""
                        </div>
                        
                        <div class="chart">
                            <h2>Original vs. Optimized Scores</h2>
                            <img src="{rel_comp_path}" alt="Original vs. Optimized Comparison">
                    """)
                
                f.write("""
                        </div>
                        
                        <h2>Recent ATS Scores</h2>
                        <table>
                            <tr>
                                <th>Date</th>
                                <th>Job Title</th>
                                <th>Company</th>
                                <th>Score (%)</th>
                                <th>Type</th>
                            </tr>
                """)
                
                # Add recent scores (most recent first)
                recent_scores = sorted(self.score_history, key=lambda x: x["timestamp"], reverse=True)[:15]
                for score in recent_scores:
                    score_type = "Optimized" if score["is_optimized"] else "Original"
                    score_date = datetime.fromisoformat(score["timestamp"]).strftime("%Y-%m-%d %H:%M")
                    f.write(f"""
                            <tr>
                                <td>{score_date}</td>
                                <td>{score["job_title"]}</td>
                                <td>{score["company"]}</td>
                                <td>{score["score"]*100:.1f}%</td>
                                <td>{score_type}</td>
                            </tr>
                    """)
                
                f.write("""
                        </table>
                        
                        <div class="footer">
                            <p>Generated by Job Application Automation System</p>
                        </div>
                    </div>
                </body>
                </html>
                """)
            
            logger.info(f"Generated ATS performance report: {report_path}")
            return report_path
            
        except Exception as e:
            logger.error(f"Error generating ATS performance report: {e}")
            return ""
    
    def save_state(self) -> bool:
        """Save current state including score history and resume cache with atomic writes."""
        try:
            state = {
                "score_history": self.score_history,
                "resume_cache": self.resume_cache
            }
            
            state_path = DATA_DIR / "ats_state.json"
            
            # Ensure parent directory exists
            state_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to temporary file first (atomic write pattern)
            with tempfile.NamedTemporaryFile('w', delete=False, 
                                             dir=state_path.parent, 
                                             encoding='utf-8',
                                             suffix='.tmp') as tmp:
                json.dump(state, tmp, indent=2)
                tmp.flush()
                os.fsync(tmp.fileno())
                tmp_path = tmp.name
            
            # Atomic rename (replaces existing file safely)
            shutil.move(tmp_path, state_path)
            
            logger.info(f"Saved ATS state to {state_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving ATS state: {e}")
            # Clean up temp file if it exists
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception as cleanup_error:
                    logger.error(f"Error cleaning up temp file: {cleanup_error}")
            return False
    
    def load_state(self) -> bool:
        """
        Load ATS integration state from file.
        
        Returns:
            True if the state was loaded successfully, False otherwise.
        """
        try:
            # Create directory if it doesn't exist
            data_dir = os.path.dirname(self.state_file)
            os.makedirs(data_dir, exist_ok=True)
            
            # If state file doesn't exist, create a default state
            if not os.path.exists(self.state_file):
                logger.info("ATS state file not found, creating default state file")
                self.state = {
                    "processed_jobs": [],
                    "ats_scores": {},
                    "resume_performance": {},
                    "last_updated": datetime.now().isoformat()
                }
                # Immediately save the default state
                self.save_state()
                return True
                
            # Load the state file
            with open(self.state_file, "r") as f:
                self.state = json.load(f)
            
            logger.info("ATS state loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error loading ATS state: {e}")
            # Initialize empty state
            self.state = {
                "processed_jobs": [],
                "ats_scores": {},
                "resume_performance": {},
                "last_updated": datetime.now().isoformat()
            }
            return False


# Example usage when run directly
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ATS Integration for Job Applications")
    parser.add_argument("--resume", type=str, help="Path to resume file")
    parser.add_argument("--job-desc", type=str, help="Path to job description file")
    parser.add_argument("--company", type=str, default="Sample Company", help="Company name")
    parser.add_argument("--job-title", type=str, default="Sample Position", help="Job title")
    parser.add_argument("--report", action="store_true", help="Generate performance report only")
    
    args = parser.parse_args()
    
    ats_manager = ATSIntegrationManager()
    ats_manager.load_state()
    
    if args.report:
        # Generate overall performance report
        report_path = ats_manager.generate_ats_performance_report()
        if report_path:
            print(f"Generated ATS performance report: {report_path}")
        else:
            print("Failed to generate ATS performance report")
    
    elif args.resume and args.job_desc:
        # Process a job application
        with open(args.job_desc, 'r', encoding='utf-8') as f:
            job_description = f.read()
            
        result = ats_manager.process_job_application(
            args.resume,
            job_description,
            {
                "job_title": args.job_title,
                "company": args.company,
                "job_id": f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            }
        )
        
        if result["should_proceed"]:
            print(f"✅ Resume is suitable for the job with score: {result['original_score']['overall_score']}%")
        else:
            if result.get("optimized_resume"):
                print(f"⚠️ Original resume score: {result['original_score']['overall_score']}%")
                print(f"✅ Optimized resume score: {result['optimized_score']['overall_score']}%")
                print(f"Optimized resume saved to: {result['optimized_resume']}")
            else:
                print(f"❌ Resume is not suitable for the job with score: {result['original_score']['overall_score']}%")
        
        print(f"Report generated at: {result['report_path']}")
        
        # Save state for future reference
        ats_manager.save_state()
    else:
        print("Please provide both resume and job description files, or use --report flag.")
        parser.print_help()