from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import re
import threading
import time


def is_fail_fast_error(err: Exception) -> bool:
    """
    True for errors that retrying the same provider cannot fix: authentication,
    quota/rate limits and malformed requests. The router should fail over instead.
    """
    s = str(err).lower()
    markers = (
        "401", "403", "unauthorized", "forbidden", "invalid_api_key", "api key not valid",
        "api_key_invalid", "permission", "429", "rate limit", "rate_limit", "resource_exhausted",
        "quota", "400 ", "400:", "invalid_argument", "bad request",
    )
    return any(m in s for m in markers)


def is_auth_error(err: Exception) -> bool:
    """Bad/invalid API key — every model of this provider will fail the same way."""
    s = str(err).lower()
    return any(m in s for m in ("401", "unauthorized", "invalid_api_key", "api key not valid", "api_key_invalid"))


def is_model_error(err: Exception) -> bool:
    """This specific model can't serve the request (missing, decommissioned, unsupported params)."""
    s = str(err).lower()
    return any(m in s for m in (
        "404", "not found", "does not exist", "decommissioned", "no endpoints", "400 ", "400:",
        "invalid_argument", "bad request", "403", "permission", "not supported",
    ))


def rate_limit_cooldown(err: Exception) -> Optional[float]:
    """
    If `err` is a rate-limit/quota error, return how many seconds to stop using that model
    (parsed from the provider's message when possible). Otherwise None.
    """
    s = str(err)
    low = s.lower()
    if not ("429" in low or "rate limit" in low or "rate_limit" in low or "resource_exhausted" in low or "quota" in low):
        return None

    # OpenRouter: X-RateLimit-Reset is an epoch timestamp in milliseconds
    m = re.search(r"x-ratelimit-reset'?\"?:\s*'?\"?(\d{12,13})", s, re.IGNORECASE)
    if m:
        return max(60.0, int(m.group(1)) / 1000 - time.time())

    # Groq: "Please try again in 11m47.616s" / "in 2h3m" / "in 12.5s"
    m = re.search(r"try again in (?:(\d+)h)?(?:(\d+)m)?(?:([\d.]+)s)?", low)
    if m and any(m.groups()):
        h, mi, se = m.groups()
        return max(30.0, int(h or 0) * 3600 + int(mi or 0) * 60 + float(se or 0))

    # Gemini daily quota ("GenerateRequestsPerDay…") — its "retry in 40s" hint is misleading for daily caps
    if "perday" in low or "per day" in low or "per_day" in low:
        return 1800.0

    m = re.search(r"retry in ([\d.]+)s", low)
    if m:
        return max(30.0, float(m.group(1)))
    return 60.0


class ModelCooldowns:
    """Remembers which models are rate-limited so we skip them instead of wasting a call."""

    def __init__(self):
        self._until: Dict[str, float] = {}
        self._lock = threading.Lock()

    def available(self, key: str) -> bool:
        with self._lock:
            return time.time() >= self._until.get(key, 0.0)

    def block(self, key: str, seconds: float) -> None:
        with self._lock:
            self._until[key] = time.time() + seconds

    def remaining(self, key: str) -> float:
        with self._lock:
            return max(0.0, self._until.get(key, 0.0) - time.time())

    def clear(self) -> None:
        with self._lock:
            self._until.clear()


class BaseLLMService(ABC):
    """
    Abstract Base Class for all LLM Service Implementations.
    Enforces a consistent interface for the Router.
    """

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        context: Optional[Dict[str, Any]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        reasoning_effort: Optional[str] = None,
    ) -> str:
        """
        Generates a response from the LLM.

        Args:
            system_prompt: The system identity/instructions.
            user_prompt: The user's current message.
            context: Optional context; context["history"] is a list of
                     {"role": "user"|"assistant", "content": str} turns.
            temperature / max_tokens / reasoning_effort: Zara-mode generation settings.
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Checks if the service is configured and reachable."""
        pass
