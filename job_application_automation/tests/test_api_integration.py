"""
Test script for API integration with Groq or OpenRouter.
This script demonstrates how to use the API integration for the Llama 4 Maverick model.
"""

import os
import sys
import logging
from dotenv import load_dotenv
from job_application_automation.config.llama_config import LlamaConfig
from src.resume_cover_letter_generator import ResumeGenerator

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_api_connection():
    """Test API connection with configured provider."""
    # Load environment variables from .env file
    load_dotenv()
    
    # Check if API key is set
    api_provider = os.getenv("LLAMA_API_PROVIDER", "").lower()
    api_key_var = "GROQ_API_KEY" if api_provider == "groq" else "OPENROUTER_API_KEY"
    api_key = os.getenv(api_key_var, "")
    
    if not api_key:
        logger.error(f"No API key found for {api_provider}. Please set {api_key_var} in your .env file.")
        return False
        
    # Create config with API settings
    config = LlamaConfig(
        use_api=True,
        api_provider=api_provider,
        api_key=api_key,
        api_model=os.getenv("LLAMA_API_MODEL", "llama-4-maverick")
    )
    
    # Initialize the ResumeGenerator with this config
    generator = ResumeGenerator(config)
    
    # Test if API is available
    if generator.api_available:
        logger.info(f"✅ Successfully connected to the {api_provider.upper()} API!")
        return True
    else:
        logger.error(f"❌ Failed to connect to the {api_provider.upper()} API. Check your configuration and API key.")
        return False

def test_text_generation():
    """Test text generation using the API."""
    # Load environment variables
    load_dotenv()
    
    # Create config with API settings
    api_provider = os.getenv("LLAMA_API_PROVIDER", "").lower()
    api_key_var = "GROQ_API_KEY" if api_provider == "groq" else "OPENROUTER_API_KEY"
    
    config = LlamaConfig(
        use_api=True,
        api_provider=api_provider,
        api_key=os.getenv(api_key_var, ""),
        api_model=os.getenv("LLAMA_API_MODEL", "llama-4-maverick")
    )
    
    # Initialize the ResumeGenerator with this config
    generator = ResumeGenerator(config)
    
    # If API is not available, exit
    if not generator.api_available:
        logger.error(f"API not available. Cannot test text generation.")
        return
    
    # Test prompt
    test_prompt = """
    Write a short professional summary for a Software Engineer with 5 years of experience
    specializing in Python development, cloud technologies (AWS), and machine learning.
    The summary should be concise (3-4 sentences) and highlight key strengths.
    """
    
    logger.info(f"Generating text using {api_provider.upper()} API for Llama 4 Maverick...")
    
    # Generate text
    generated_text = generator.generate_text(test_prompt)
    
    # Display the result
    logger.info("Generated Text:")
    print("\n" + "-" * 80)
    print(generated_text)
    print("-" * 80 + "\n")
    
    return generated_text

def test_main():
    """Main test function to run the tests."""
    print("\n===== TESTING API INTEGRATION =====\n")
    
    # Test API connection
    connection_success = test_api_connection()
    
    if connection_success:
        # If connection successful, test text generation
        test_text_generation()
    else:
        print("\nTo use the API integration, follow these steps:")
        print("1. Create a copy of .env.example named .env")
        print("2. Set your API key for either Groq or OpenRouter in the .env file")
        print("3. Configure the API provider (groq or openrouter) in the .env file")
        print("4. Run this script again\n")
        
    print("===== API INTEGRATION TEST COMPLETE =====")
