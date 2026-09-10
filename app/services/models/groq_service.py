"""
Groq Service — primary provider for Zara Fast (fallback for Pro/Eco)
────────────────────────────────────
Tries several Groq models in order. Each Groq model has its OWN free-tier quota, so when
one hits its daily token limit (429) it is put on cooldown and the next model answers.
  - Generation settings (temperature, max tokens, reasoning effort) come from the
    Zara mode via the router, so personality does not depend on which model answers.
"""

from groq import Groq
from app.core.config import settings
from app.services.models.base_llm import (
    BaseLLMService, ModelCooldowns, is_auth_error, is_model_error, rate_limit_cooldown,
)
from typing import Dict, Any, Optional
import time
import logging

logger = logging.getLogger(__name__)

_DEFAULT_TEMPERATURE = 0.5
_DEFAULT_MAX_TOKENS = 1024
_MAX_RETRIES = 2
_RETRY_DELAY_BASE = 1.5
_TIMEOUT_SECONDS = 25

_cooldowns = ModelCooldowns()


class GroqService(BaseLLMService):
    """Groq — low-latency provider with per-model quota fallback."""

    AVAILABLE_MODELS = [
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "qwen/qwen3.8-27b",
        "qwen/qwen3.6-27b",
    ]

    def __init__(self):
        if settings.GROQ_API_KEY:
            self.client = Groq(api_key=settings.GROQ_API_KEY)
            self.model_name = self.AVAILABLE_MODELS[0]
            logger.info(f"GroqService initialized with models: {self.AVAILABLE_MODELS}")
        else:
            self.client = None
            logger.warning("GROQ_API_KEY not found. Groq Service disabled.")

    def health_check(self) -> bool:
        return self.client is not None

    @staticmethod
    def _model_params(model: str, reasoning_effort: Optional[str]) -> Dict[str, Any]:
        if "gpt-oss" in model:
            return {"reasoning_effort": reasoning_effort} if reasoning_effort else {}
        if "qwen" in model:
            return {"reasoning_format": "hidden"}  # never show chain-of-thought to users
        return {}

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
            raise ValueError("Groq Service is not configured.")

        messages = [{"role": "system", "content": system_prompt}]
        if context and context.get("history"):
            messages.extend(context["history"])
        messages.append({"role": "user", "content": user_prompt})

        last_error: Exception = RuntimeError("Groq: all models are rate-limited (cooling down)")

        for model in self.AVAILABLE_MODELS:
            if not _cooldowns.available(model):
                continue
            params: Dict[str, Any] = {
                "model": model,
                "messages": messages,
                "temperature": _DEFAULT_TEMPERATURE if temperature is None else temperature,
                "max_tokens": max_tokens or _DEFAULT_MAX_TOKENS,
                "timeout": _TIMEOUT_SECONDS,
                **self._model_params(model, reasoning_effort),
            }
            for attempt in range(1, _MAX_RETRIES + 1):
                try:
                    response = self.client.chat.completions.create(**params)
                    content = response.choices[0].message.content
                    if not content or not content.strip():
                        raise ValueError("Groq returned empty response")
                    self.model_name = model
                    logger.info(f"Groq generation OK with model '{model}' (attempt {attempt})")
                    return content

                except Exception as e:
                    last_error = e
                    logger.warning(f"Groq model '{model}' attempt {attempt} failed: {e}")
                    cooldown = rate_limit_cooldown(e)
                    if cooldown:
                        _cooldowns.block(model, cooldown)
                        logger.warning(f"Groq model '{model}' rate-limited; skipping it for {cooldown/60:.0f} min.")
                        break
                    if is_auth_error(e):
                        raise
                    if is_model_error(e):
                        _cooldowns.block(model, 3600)
                        break
                    if attempt < _MAX_RETRIES:
                        time.sleep(_RETRY_DELAY_BASE ** attempt)

        logger.error("Groq: no model could answer.")
        raise last_error
