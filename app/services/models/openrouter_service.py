"""
OpenRouter Service — Zara Eco Provider
───────────────────────────────────────
Routes Zara Eco requests to OpenRouter (Mixtral).
  - Temperature: 0.6 (calm, thoughtful, human-like)
  - Max tokens: 768 (moderate depth for Eco mode)
  - Retry: 3 attempts with exponential backoff
  - Model: mistralai/mixtral-8x7b-instruct (efficient + quality)
"""

from openai import OpenAI
from app.core.config import settings
from app.services.models.base_llm import BaseLLMService
from typing import Dict, Any, Optional
import time
import logging

logger = logging.getLogger(__name__)

_ECO_TEMPERATURE = 0.6
_ECO_MAX_TOKENS = 768
_MAX_RETRIES = 3
_RETRY_DELAY_BASE = 1.5


class OpenRouterService(BaseLLMService):
    """
    OpenRouter — Zara Eco Provider.
    Produces thoughtful, safe, human-like conversational responses.
    """

    def __init__(self):
        if settings.OPENROUTER_API_KEY:
            self.client = OpenAI(
                api_key=settings.OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1",
            )
            self.model_name = "mistralai/mixtral-8x7b-instruct"
            self.extra_headers = {
                "HTTP-Referer": "https://zara.ai",
                "X-Title": "ZARA AI",
            }
            logger.info(f"OpenRouterService initialized with model: {self.model_name}")
        else:
            self.client = None
            logger.warning("OPENROUTER_API_KEY not found. OpenRouter Service disabled.")

    def health_check(self) -> bool:
        return self.client is not None

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        context: Optional[Dict[str, Any]] = None,
        temperature: float = _ECO_TEMPERATURE,
    ) -> str:
        if not self.client:
            raise ValueError("OpenRouter Service is not configured.")

        messages = [
            {"role": "system", "content": system_prompt},
        ]

        if context and context.get("history"):
            messages.extend(context["history"])

        messages.append({"role": "user", "content": user_prompt})

        last_error: Exception = RuntimeError(f"OpenRouter: no attempts made for model {self.model_name}")

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=_ECO_MAX_TOKENS,
                    top_p=0.85,
                    extra_headers=self.extra_headers,
                    timeout=25,
                )
                content = response.choices[0].message.content
                if not content:
                    raise ValueError("OpenRouter returned empty response")
                logger.info(f"OpenRouter generation OK on attempt {attempt}")
                return content

            except Exception as e:
                last_error = e
                logger.warning(f"OpenRouter attempt {attempt}/{_MAX_RETRIES} failed: {e}")
                if attempt < _MAX_RETRIES:
                    delay = _RETRY_DELAY_BASE ** attempt
                    logger.info(f"Retrying in {delay:.1f}s...")
                    time.sleep(delay)

        logger.error(f"OpenRouter all {_MAX_RETRIES} attempts failed.")
        raise last_error
