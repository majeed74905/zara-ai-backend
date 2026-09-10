"""
Gemini Service — primary provider for Zara Pro (fallback for Fast/Eco)
────────────────────────────────────
Tries several Gemini models in order. Free-tier quotas are PER MODEL, so when one model's
daily quota is exhausted (429) it goes on cooldown and the next model answers.
  - Conversation history is sent as real multi-turn contents (user/model roles).
  - Generation settings come from the Zara mode via the router.
  - 30s request timeout; retries only transient failures.
"""

from google import genai
from google.genai import types
from app.core.config import settings
from app.services.models.base_llm import (
    BaseLLMService, ModelCooldowns, is_auth_error, is_model_error, rate_limit_cooldown,
)
from typing import Dict, Any, List, Optional
import time
import logging

logger = logging.getLogger(__name__)

_DEFAULT_TEMPERATURE = 0.7
_DEFAULT_MAX_TOKENS = 2048
_MAX_RETRIES = 2
_RETRY_DELAY_BASE = 1.5
_TIMEOUT_MS = 30_000

_cooldowns = ModelCooldowns()


class GeminiService(BaseLLMService):
    """Google Gemini provider with per-model quota fallback."""

    # Each has its own free-tier quota. (gemini-2.5-* return 404 "no longer available to new users".)
    AVAILABLE_MODELS = [
        "gemini-3.5-flash",
        "gemini-3.1-flash-lite",
        "gemini-3-flash-preview",
        "gemini-3.5-flash-lite",
        "gemini-flash-latest",
    ]

    def __init__(self):
        if settings.GEMINI_API_KEY:
            self.client = genai.Client(
                api_key=settings.GEMINI_API_KEY,
                http_options=types.HttpOptions(timeout=_TIMEOUT_MS),
            )
            self.model_name = self.AVAILABLE_MODELS[0]
            logger.info(f"GeminiService initialized with models: {self.AVAILABLE_MODELS}")
        else:
            self.client = None
            logger.warning("GEMINI_API_KEY not found. Gemini Service disabled.")

    def health_check(self) -> bool:
        return self.client is not None

    @staticmethod
    def _build_contents(user_prompt: str, history: Optional[List[Dict[str, str]]]) -> List[types.Content]:
        contents: List[types.Content] = []
        for msg in history or []:
            text = msg.get("content")
            if not text:
                continue
            role = "model" if msg.get("role") == "assistant" else "user"
            contents.append(types.Content(role=role, parts=[types.Part(text=text)]))
        contents.append(types.Content(role="user", parts=[types.Part(text=user_prompt)]))
        return contents

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        context: Optional[Dict[str, Any]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        reasoning_effort: Optional[str] = None,
    ) -> str:
        if not self.client:
            raise ValueError("Gemini Service is not configured.")

        contents = self._build_contents(user_prompt, (context or {}).get("history"))
        # Thinking tokens count toward max_output_tokens on thinking models; leave headroom
        output_budget = max(_DEFAULT_MAX_TOKENS, (max_tokens or _DEFAULT_MAX_TOKENS) * 2)
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=_DEFAULT_TEMPERATURE if temperature is None else temperature,
            max_output_tokens=output_budget,
        )

        last_error: Exception = RuntimeError("Gemini: all models are rate-limited (quota exhausted, cooling down)")

        for model in self.AVAILABLE_MODELS:
            if not _cooldowns.available(model):
                continue
            for attempt in range(1, _MAX_RETRIES + 1):
                try:
                    response = self.client.models.generate_content(model=model, contents=contents, config=config)
                    if not response.text:
                        raise ValueError("Gemini returned empty response (safety filter or quota issue)")
                    self.model_name = model
                    logger.info(f"Gemini generation OK with model '{model}' (attempt {attempt})")
                    return response.text

                except Exception as e:
                    last_error = e
                    logger.warning(f"Gemini model '{model}' attempt {attempt} failed: {e}")
                    cooldown = rate_limit_cooldown(e)
                    if cooldown:
                        _cooldowns.block(model, cooldown)
                        logger.warning(f"Gemini model '{model}' quota hit; skipping it for {cooldown/60:.0f} min.")
                        break
                    if is_auth_error(e):
                        raise
                    if is_model_error(e):
                        _cooldowns.block(model, 3600)
                        break
                    if attempt < _MAX_RETRIES:
                        time.sleep(_RETRY_DELAY_BASE ** attempt)

        logger.error("Gemini: no model could answer.")
        raise last_error
