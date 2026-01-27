"""
Gemini API provider implementation.
"""
import logging
from typing import Dict, List, Optional, Any
import google.generativeai as genai
from job_application_automation.config.gemini_config import GeminiConfig

logger = logging.getLogger(__name__)

class GeminiProvider:
    """Provider for Google's Gemini API."""
    
    def __init__(self, config: Optional[GeminiConfig] = None):
        """
        Initialize the Gemini provider.
        
        Args:
            config: Gemini configuration settings. If None, default settings will be used.
        """
        self.config = config or GeminiConfig.from_env()
        self._setup_client()
        
    def _setup_client(self) -> None:
        """Set up the Gemini client."""
        try:
            api_config = self.config.get_api_config()
            genai.configure(api_key=api_config["api_key"])
            
            # Configure the model
            generation_config = {
                "temperature": api_config["temperature"],
                "top_p": api_config["top_p"],
                "top_k": api_config["top_k"],
                "max_output_tokens": api_config["max_tokens"],
            }
            
            # Set up safety settings
            safety_settings = []
            for category, threshold in api_config["safety_settings"].items():
                safety_settings.append({
                    "category": category,
                    "threshold": threshold
                })
            
            # Initialize the model
            self.model = genai.GenerativeModel(
                model_name=api_config["model"],
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            
            logger.info(f"Successfully initialized Gemini model: {api_config['model']}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            raise
    
    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Generate text using the Gemini model.
        
        Args:
            prompt: The user prompt to generate text from.
            system_prompt: Optional system prompt to guide the model's behavior.
            
        Returns:
            Generated text response.
        """
        try:
            # Combine system prompt and user prompt if provided
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            
            # Generate response
            response = self.model.generate_content(full_prompt)
            
            # Extract and return the generated text
            return response.text
            
        except Exception as e:
            logger.error(f"Error generating text with Gemini: {e}")
            return ""
    
    def generate_chat(self, messages: List[Dict[str, str]]) -> str:
        """
        Generate chat completion using the Gemini model.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys.
            
        Returns:
            Generated chat response.
        """
        try:
            # Convert messages to Gemini chat format
            chat = self.model.start_chat(history=[])
            
            # Add messages to chat
            for message in messages:
                if message["role"] == "user":
                    chat.send_message(message["content"])
                elif message["role"] == "assistant":
                    # Store assistant's response in history
                    chat.history.append({
                        "role": "model",
                        "parts": [message["content"]]
                    })
            
            # Get the last response
            response = chat.last.text
            return response
            
        except Exception as e:
            logger.error(f"Error generating chat with Gemini: {e}")
            return "" 