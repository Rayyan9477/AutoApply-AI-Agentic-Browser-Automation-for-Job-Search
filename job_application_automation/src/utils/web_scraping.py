"""
Web scraping module using Crawl4AI for job details extraction.
This module provides functionality to scrape job details from job listings.
"""

import os
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional, Union

# Import HTTPX and BeautifulSoup
import httpx
from bs4 import BeautifulSoup

# Import configuration
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.crawl4ai_config import Crawl4AIConfig

# Set up logging with absolute path for the log file
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
log_file_path = os.path.join(project_root, "data", "web_scraping.log")

# Ensure log directory exists
os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class JobDetailsScraper:
    """
    Class for scraping job details using Crawl4AI.
    This class provides methods to scrape job details from job listings.
    """

    def __init__(self, config: Optional[Crawl4AIConfig] = None):
        """
        Initialize the JobDetailsScraper with configuration settings.
        
        Args:
            config: Configuration settings for web scraping.
                   If None, default settings will be used.
        """
        self.config = config or Crawl4AIConfig()
        
    async def scrape_job_details(self, job_listings_or_url: Union[List[Dict[str, Any]], str]) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Scrape job descriptions using HTTPX and BeautifulSoup.
        
        Args:
            job_listings_or_url: Either a list of job listings or a single job URL
            
        Returns:
            Either a list of job details or a single job detail dictionary
        """
        # Handle single URL case
        if isinstance(job_listings_or_url, str):
            url = job_listings_or_url
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(url, timeout=self.config.request_timeout)
                    resp.raise_for_status()
                    soup = BeautifulSoup(resp.text, 'lxml')
                    
                    # Extract job details from the page
                    job_description = ""
                    description_elements = soup.select('.job-description, .description, [data-testid="jobDescriptionText"]')
                    
                    if description_elements:
                        for elem in description_elements:
                            job_description += elem.get_text(separator=' ', strip=True)
                    else:
                        # Fallback: get all paragraphs if no specific job description container found
                        job_description = ' '.join(p.get_text(separator=' ', strip=True) for p in soup.find_all('p'))
                    
                    # Extract job title
                    job_title_elem = soup.select_one('h1.job-title, h1.title, [data-testid="jobTitle"]')
                    job_title = job_title_elem.get_text(strip=True) if job_title_elem else "Unknown Position"
                    
                    # Extract company name
                    company_elem = soup.select_one('.company-name, .employer, [data-testid="companyName"]')
                    company = company_elem.get_text(strip=True) if company_elem else "Unknown Company"
                    
                    # Extract location
                    location_elem = soup.select_one('.location, [data-testid="jobLocationText"]')
                    location = location_elem.get_text(strip=True) if location_elem else "Unknown Location"
                    
                    return {
                        "job_title": job_title,
                        "company": company,
                        "location": location,
                        "job_description": job_description,
                        "url": url
                    }
            except Exception as e:
                logger.error(f"Error scraping {url}: {e}")
                return {}
        
        # Handle list of job listings
        if not job_listings_or_url:
            logger.warning("No job listings provided for scraping")
            return []
            
        job_details = []
        async with httpx.AsyncClient() as client:
            for listing in job_listings_or_url:
                url = listing.get("url")
                if not url:
                    continue
                try:
                    resp = await client.get(url, timeout=self.config.request_timeout)
                    resp.raise_for_status()
                    soup = BeautifulSoup(resp.text, 'lxml')
                    
                    # Extract job description from the page
                    job_description = ""
                    description_elements = soup.select('.job-description, .description, [data-testid="jobDescriptionText"]')
                    
                    if description_elements:
                        for elem in description_elements:
                            job_description += elem.get_text(separator=' ', strip=True)
                    else:
                        # Fallback: get all paragraphs if no specific job description container found
                        job_description = ' '.join(p.get_text(separator=' ', strip=True) for p in soup.find_all('p'))
                    
                    detail = {**listing, "job_description": job_description}
                    job_details.append(detail)
                    logger.info(f"Scraped job description from {url}")
                except Exception as e:
                    logger.error(f"Error scraping {url}: {e}")
        return job_details


# Example usage
async def main():
    # Load job listings from a file
    try:
        with open("../data/job_listings.json", "r") as f:
            job_listings = json.load(f)
    except Exception as e:
        logger.error(f"Error loading job listings: {e}")
        job_listings = []
    
    if job_listings:
        job_details_scraper = JobDetailsScraper()
        job_details = await job_details_scraper.scrape_job_details(job_listings)
        print(f"Scraped details for {len(job_details)} jobs")
    else:
        print("No job listings found to scrape")


if __name__ == "__main__":
    asyncio.run(main())