"""
Unified LLM client that selects a provider based on available API keys or explicit config.
Supported providers: openai, groq, openrouter, github (GitHub Models), gemini, local (no-op fallback).
"""

from typing import Optional, Dict, Any
import os
import logging

from job_application_automation.config.llama_config import LlamaConfig

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, cfg: Optional[LlamaConfig] = None) -> None:
        self.cfg = cfg or LlamaConfig.from_env()
        # Auto-detect provider if not explicitly set
        self._auto_detect_provider()
        self._client = None
        self._init_client()

    def _auto_detect_provider(self) -> None:
        if getattr(self.cfg, "use_api", True) is False:
            self.cfg.api_provider = "local"
            return
        # Respect explicit provider
        if getattr(self.cfg, "api_provider", None):
            return
        # Infer from keys
        if os.getenv("OPENAI_API_KEY"):
            self.cfg.api_provider = "openai"
        elif os.getenv("GROQ_API_KEY"):
            self.cfg.api_provider = "groq"
        elif os.getenv("OPENROUTER_API_KEY"):
            self.cfg.api_provider = "openrouter"
        elif os.getenv("GITHUB_TOKEN"):
            self.cfg.api_provider = "github"
        elif os.getenv("GEMINI_API_KEY"):
            self.cfg.api_provider = "gemini"
        else:
            self.cfg.api_provider = "local"

    def _init_client(self) -> None:
        provider = getattr(self.cfg, "api_provider", "local").lower()
        try:
            if provider == "openai":
                from openai import OpenAI

                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise ValueError("OPENAI_API_KEY environment variable not set. Please add it to your .env file.")
                self._client = OpenAI(api_key=api_key)
                self._base_url = "https://api.openai.com/v1"
                self._model = getattr(self.cfg, "api_model", getattr(self.cfg, "openai_model", "gpt-4o-mini"))

            elif provider == "groq":
                from openai import OpenAI

                api_key = os.getenv("GROQ_API_KEY")
                if not api_key:
                    raise ValueError("GROQ_API_KEY environment variable not set. Please add it to your .env file.")
                self._client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
                self._base_url = "https://api.groq.com/openai/v1"
                self._model = getattr(self.cfg, "api_model", "llama-3.1-8b-instant")

            elif provider == "openrouter":
                from openai import OpenAI

                api_key = os.getenv("OPENROUTER_API_KEY")
                if not api_key:
                    raise ValueError("OPENROUTER_API_KEY environment variable not set. Please add it to your .env file.")
                self._client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
                self._base_url = "https://openrouter.ai/api/v1"
                self._model = getattr(self.cfg, "api_model", "meta-llama/llama-3.1-8b-instruct")

            elif provider == "github":
                # Use Azure AI SDK for GitHub Models endpoint
                from azure.ai.inference import ChatCompletionsClient
                from azure.core.credentials import AzureKeyCredential

                token = os.getenv("GITHUB_TOKEN")
                if not token:
                    raise ValueError("GITHUB_TOKEN environment variable not set. Please add it to your .env file.")
                endpoint = getattr(self.cfg, "api_base_url", "https://models.github.ai/inference")
                self._client = ChatCompletionsClient(endpoint=endpoint, credential=AzureKeyCredential(token))
                self._model = getattr(self.cfg, "api_model", "meta/Llama-4-Maverick-17B-128E-Instruct-FP8")

            elif provider == "gemini":
                import google.generativeai as genai

                api_key = os.getenv("GEMINI_API_KEY")
                if not api_key:
                    raise ValueError("GEMINI_API_KEY environment variable not set. Please add it to your .env file.")
                genai.configure(api_key=api_key)
                self._client = genai.GenerativeModel(getattr(self.cfg, "gemini_model", "gemini-1.5-flash"))
                self._model = getattr(self.cfg, "gemini_model", "gemini-1.5-flash")

            else:
                self._client = None
                self._model = None
                logger.warning("LLMClient in local/no-op mode")

        except Exception as e:
            logger.error(f"Failed to initialize LLM client for provider {provider}: {e}")
            self._client = None

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 1000) -> str:
        provider = getattr(self.cfg, "api_provider", "local").lower()
        temperature = getattr(self.cfg, "temperature", 0.7)
        top_p = getattr(self.cfg, "top_p", 0.9)
        try:
            if provider in ("openai", "groq", "openrouter") and self._client:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
                resp = self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                )
                return resp.choices[0].message.content or ""

            if provider == "github" and self._client:
                from azure.ai.inference.models import SystemMessage, UserMessage

                resp = self._client.complete(
                    messages=[SystemMessage(system_prompt), UserMessage(user_prompt)],
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                    model=self._model,
                )
                return resp.choices[0].message.content or ""

            if provider == "gemini" and self._client:
                # Combine system and user in a single prompt for simplicity
                prompt = f"{system_prompt}\n\n{user_prompt}"
                resp = self._client.generate_content(prompt)
                return getattr(resp, "text", "") or ""

            # Local fallback
            return ""
        except Exception as e:
            logger.error(f"LLM generate error ({provider}): {e}")
            return ""


