"""
OpenRouter Service — primary provider for Zara Eco & universal fallback
───────────────────────────────────────────────────────────
Routes requests to OpenRouter with automatic model fallback.
Generation settings come from the Zara mode via the router.
The free-tier daily cap is account-wide: once hit, the whole provider is skipped
(no wasted call per message) until the reset time OpenRouter reports.
"""

from openai import OpenAI
from app.core.config import settings
from app.services.models.base_llm import (
    BaseLLMService, ModelCooldowns, is_fail_fast_error, rate_limit_cooldown,
)
from typing import Dict, Any, Optional
import time
import logging
import re

logger = logging.getLogger(__name__)

_DEFAULT_TEMPERATURE = 0.6
_DEFAULT_MAX_TOKENS = 1024
_MAX_RETRIES = 2
_RETRY_DELAY_BASE = 1.2
_TIMEOUT_SECONDS = 30
_ACCOUNT = "__account__"

_cooldowns = ModelCooldowns()


class OpenRouterService(BaseLLMService):
    """OpenRouter provider with per-model fallback."""

    AVAILABLE_MODELS = [
        "nex-agi/nex-n2.5-mini:free",
        "nex-agi/nex-n2.5-pro:free",
    ]

    def __init__(self):
        if settings.OPENROUTER_API_KEY:
            self.client = OpenAI(
                api_key=settings.OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1",
            )
            self.model_name = self.AVAILABLE_MODELS[0]
            self.extra_headers = {
                "HTTP-Referer": "https://zara.ai",
                "X-Title": "ZARA AI",
            }
            logger.info(f"OpenRouterService initialized with models: {self.AVAILABLE_MODELS}")
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
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        reasoning_effort: Optional[str] = None,
    ) -> str:
        if not self.client:
            raise ValueError("OpenRouter Service is not configured.")
        if not _cooldowns.available(_ACCOUNT):
            wait_min = _cooldowns.remaining(_ACCOUNT) / 60
            raise RuntimeError(f"OpenRouter rate limit reached (free daily cap); skipping for {wait_min:.0f} more min")

        messages = [{"role": "system", "content": system_prompt}]
        if context and context.get("history"):
            messages.extend(context["history"])
        messages.append({"role": "user", "content": user_prompt})

        last_error: Exception = RuntimeError("OpenRouter: no attempts made")

        for model in self.AVAILABLE_MODELS:
            if not _cooldowns.available(model):
                continue
            self.model_name = model
            for attempt in range(1, _MAX_RETRIES + 1):
                try:
                    logger.info(f"OpenRouter calling model '{model}' (attempt {attempt})...")
                    response = self.client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=_DEFAULT_TEMPERATURE if temperature is None else temperature,
                        max_tokens=max_tokens or _DEFAULT_MAX_TOKENS,
                        top_p=0.85,
                        extra_headers=self.extra_headers,
                        timeout=_TIMEOUT_SECONDS,
                    )
                    msg = response.choices[0].message
                    content = msg.content
                    if not content or not content.strip():
                        # If content is empty, check if reasoning has a final answer or code snippet
                        reasoning = getattr(msg, "reasoning", None)
                        code_match = re.search(r'(```[\s\S]+?```)', reasoning) if reasoning else None
                        if code_match:
                            content = code_match.group(1)
                        else:
                            # Do not dump raw chain-of-thought as the assistant reply
                            raise ValueError("OpenRouter returned no user-facing content")

                    logger.info(f"OpenRouter generation OK with model '{model}'")
                    return content

                except Exception as e:
                    last_error = e
                    err_str = str(e).lower()
                    logger.warning(f"OpenRouter model '{model}' attempt {attempt} failed: {e}")

                    cooldown = rate_limit_cooldown(e)
                    if cooldown:
                        # Free-tier limits are account-wide: skip the whole provider until reset
                        _cooldowns.block(_ACCOUNT, cooldown)
                        logger.warning(f"OpenRouter rate-limited; skipping provider for {cooldown/60:.0f} min.")
                        raise

                    # Model unusable (missing endpoint, auth, bad request) → next model
                    if is_fail_fast_error(e) or "404" in err_str or "no endpoints" in err_str:
                        _cooldowns.block(model, 3600)
                        break

                    if attempt < _MAX_RETRIES:
                        time.sleep(_RETRY_DELAY_BASE ** attempt)

        logger.error("OpenRouter all models and attempts failed.")
        raise last_error
