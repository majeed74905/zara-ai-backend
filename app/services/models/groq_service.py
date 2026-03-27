"""
Groq Service — Zara Fast Provider
────────────────────────────────────
Routes Zara Fast requests to Groq (llama-3.3-70b-versatile).
  - Temperature: 0.5 (fast, confident, minimal hedging)
  - Max tokens: 512 (enforces brevity for Fast mode)
  - Retry: 3 attempts with exponential backoff
  - Timeout: 15 seconds (Groq is fast — fail quickly if needed)
"""

from groq import Groq
from app.core.config import settings
from app.services.models.base_llm import BaseLLMService
from typing import Dict, Any, Optional
import time
import logging

logger = logging.getLogger(__name__)

_FAST_TEMPERATURE = 0.5
_FAST_MAX_TOKENS = 512
_MAX_RETRIES = 3
_RETRY_DELAY_BASE = 1.0


class GroqService(BaseLLMService):
    """
    Groq — Zara Fast Provider.
    Produces concise, direct, low-latency responses.
    """

    def __init__(self):
        if settings.GROQ_API_KEY:
            self.client = Groq(api_key=settings.GROQ_API_KEY)
            self.model_name = "llama-3.3-70b-versatile"
            logger.info(f"GroqService initialized with model: {self.model_name}")
        else:
            self.client = None
            logger.warning("GROQ_API_KEY not found. Groq Service disabled.")

    def health_check(self) -> bool:
        return self.client is not None

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        context: Optional[Dict[str, Any]] = None,
        temperature: float = _FAST_TEMPERATURE,
    ) -> str:
        if not self.client:
            raise ValueError("Groq Service is not configured.")

        messages = [
            {"role": "system", "content": system_prompt},
        ]

        # Inject conversation history between system and current user message
        if context and context.get("history"):
            messages.extend(context["history"])

        messages.append({"role": "user", "content": user_prompt})

        last_error: Exception = RuntimeError(f"Groq: no attempts made for model {self.model_name}")

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=_FAST_MAX_TOKENS,
                    timeout=15,
                )
                content = response.choices[0].message.content
                if not content:
                    raise ValueError("Groq returned empty response")
                logger.info(f"Groq generation OK on attempt {attempt}")
                return content

            except Exception as e:
                last_error = e
                logger.warning(f"Groq attempt {attempt}/{_MAX_RETRIES} failed: {e}")
                if attempt < _MAX_RETRIES:
                    delay = _RETRY_DELAY_BASE ** attempt
                    logger.info(f"Retrying in {delay:.1f}s...")
                    time.sleep(delay)

        logger.error(f"Groq all {_MAX_RETRIES} attempts failed.")
        raise last_error
