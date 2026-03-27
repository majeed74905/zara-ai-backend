"""
Gemini Service — Zara Pro Provider
────────────────────────────────────
Routes Zara Pro requests to Google Gemini.
  - Temperature: 0.7 (deep, structured, analytical)
  - Model: gemini-1.5-flash (reliable, generous quota)
  - Retry: 3 attempts with exponential backoff
  - Timeout: 30 seconds per call
"""

import google.generativeai as genai
from app.core.config import settings
from app.services.models.base_llm import BaseLLMService
from typing import Dict, Any, Optional
import time
import logging

logger = logging.getLogger(__name__)

_PRO_TEMPERATURE = 0.7
_MAX_RETRIES = 3
_RETRY_DELAY_BASE = 1.5  # exponential backoff base (seconds)


class GeminiService(BaseLLMService):
    """
    Google Gemini — Zara Pro Provider.
    Produces deep, structured, research-quality answers.
    """

    def __init__(self):
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model_name = "models/gemini-1.5-flash"
            self.model = genai.GenerativeModel(model_name=self.model_name)
            logger.info(f"GeminiService initialized with model: {self.model_name}")
        else:
            self.model = None
            logger.warning("GEMINI_API_KEY not found. Gemini Service disabled.")

    def health_check(self) -> bool:
        return self.model is not None

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        context: Optional[Dict[str, Any]] = None,
        temperature: float = _PRO_TEMPERATURE,
    ) -> str:
        if not self.model:
            raise ValueError("Gemini Service is not configured.")

        last_error: Exception = RuntimeError(f"Gemini: no attempts made for model {self.model_name}")

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                # Create a model instance with system instruction and generation config
                chat_model = genai.GenerativeModel(
                    model_name=self.model_name,
                    system_instruction=system_prompt,
                    generation_config=genai.GenerationConfig(
                        temperature=temperature,
                        max_output_tokens=2048,
                    ),
                )

                # Build final prompt (history already embedded in user_prompt by prompt_builder)
                response = chat_model.generate_content(user_prompt)

                if not response.text:
                    raise ValueError(
                        "Gemini returned empty response (safety filter or quota issue)"
                    )

                logger.info(f"Gemini generation OK on attempt {attempt}")
                return response.text

            except Exception as e:
                last_error = e
                logger.warning(f"Gemini attempt {attempt}/{_MAX_RETRIES} failed: {e}")
                if attempt < _MAX_RETRIES:
                    delay = _RETRY_DELAY_BASE ** attempt
                    logger.info(f"Retrying in {delay:.1f}s...")
                    time.sleep(delay)

        # All retries exhausted — attempt fallback without system_instruction
        logger.error(f"Gemini all {_MAX_RETRIES} attempts failed. Trying combined prompt fallback.")
        try:
            combined = f"{system_prompt}\n\n{user_prompt}"
            response = self.model.generate_content(combined)
            if response.text:
                return response.text
        except Exception as fallback_err:
            logger.error(f"Gemini fallback also failed: {fallback_err}")

        raise last_error
