"""
LLM Router — Zara AI
──────────────────────────────────────────────────────────────────────────────
Mode-based routing with provider fallback. The Zara model identity (Fast / Pro /
Eco) owns the personality and generation settings; providers are only inference
backends, so a fallback provider produces the same Zara personality.

Primary + fallback chain per mode:
  Fast: Groq → OpenRouter → Gemini
  Pro:  Gemini → Groq → OpenRouter
  Eco:  OpenRouter → Gemini → Groq

Also includes:
  - Cost tracking (estimated tokens per call, bounded in memory)
  - Structured per-call logging (no message content)
  - A total routing deadline so a slow provider chain can't hang a request
"""

from collections import deque
from app.services.models.gemini_service import GeminiService
from app.services.models.openrouter_service import OpenRouterService
from app.services.models.groq_service import GroqService
from app.services.zara_identity import get_generation_config
from typing import Dict, Any, Optional, Tuple
import logging
import time

logger = logging.getLogger(__name__)

# ── Approximate token costs (USD per 1K tokens, input+output blended rough estimate)
_COST_PER_1K = {
    "groq": 0.0002,
    "gemini": 0.0005,
    "openrouter": 0.0006,
}

# Total time budget for one request across all providers
_ROUTE_DEADLINE_SECONDS = 75

# Cost tracker (in-session accumulator; bounded so it can't grow forever)
_cost_log: deque = deque(maxlen=2000)


class ProviderRoutingError(RuntimeError):
    """
    All providers failed. `kind` lets the API choose a user-facing message:
      rate_limited | timeout | not_configured | unavailable
    """

    def __init__(self, message: str, kind: str = "unavailable"):
        super().__init__(message)
        self.kind = kind


def log_cost(provider: str, approx_tokens: int) -> float:
    """Estimate and log the approximate cost of a call."""
    cost = (approx_tokens / 1000) * _COST_PER_1K.get(provider, 0.001)
    _cost_log.append({
        "provider": provider,
        "approx_tokens": approx_tokens,
        "estimated_cost_usd": round(cost, 6),
        "timestamp": time.time(),
    })
    logger.info(f"💰 Cost log: provider={provider}, ~{approx_tokens} tokens, ~${cost:.6f}")
    return cost


def get_cost_summary() -> dict:
    """Return total session cost tracking summary."""
    entries = list(_cost_log)
    total_cost = sum(e["estimated_cost_usd"] for e in entries)
    total_tokens = sum(e["approx_tokens"] for e in entries)
    by_provider: Dict[str, Dict[str, Any]] = {}
    for entry in entries:
        p = entry["provider"]
        by_provider.setdefault(p, {"calls": 0, "tokens": 0, "cost": 0.0})
        by_provider[p]["calls"] += 1
        by_provider[p]["tokens"] += entry["approx_tokens"]
        by_provider[p]["cost"] = round(by_provider[p]["cost"] + entry["estimated_cost_usd"], 6)
    return {
        "total_calls": len(entries),
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 6),
        "by_provider": by_provider,
    }


def _is_rate_limit(err: str) -> bool:
    e = err.lower()
    return "429" in e or "rate limit" in e or "resource_exhausted" in e or "quota" in e


def _classify_failure(errors: list) -> str:
    """Label the overall failure. 'rate_limited' only if EVERY attempted provider was rate-limited,
    so a different primary-provider failure isn't misreported as 'too many requests'."""
    if errors and all("not configured" in e for e in errors):
        return "not_configured"
    attempted = [e for e in errors if "not configured" not in e]
    if attempted and all(_is_rate_limit(e) for e in attempted):
        return "rate_limited"
    text = " ".join(attempted).lower()
    if "timeout" in text or "timed out" in text or "deadline" in text:
        return "timeout"
    return "unavailable"


class LLMRouter:
    """
    Central dispatcher that selects the right provider based on mode,
    with graceful fallback chains.
    """

    def __init__(self):
        self.gemini = GeminiService()
        self.groq = GroqService()
        self.openrouter = OpenRouterService()
        logger.info("LLMRouter initialized. Primary providers: Fast→Groq | Pro→Gemini | Eco→OpenRouter")

    def _get_routing_order(self, mode: str, user_prompt: str = "") -> list:
        m = (mode or "fast").lower()
        if m == "fast":
            return [("groq", self.groq), ("openrouter", self.openrouter), ("gemini", self.gemini)]
        elif m == "pro":
            return [("gemini", self.gemini), ("groq", self.groq), ("openrouter", self.openrouter)]
        else:
            return [("openrouter", self.openrouter), ("gemini", self.gemini), ("groq", self.groq)]

    def route_request_with_meta(
        self,
        mode: str,
        system_prompt: str,
        user_prompt: str,
        context: Optional[Dict[str, Any]] = None,
        module: str = "chat",
        task: str = "chat",
        deep_thinking: bool = False,
        max_tokens_cap: Optional[int] = None,
        temperature_boost: float = 0.0,
    ) -> Tuple[str, Dict[str, Any]]:
        """Route a request; returns (response_text, routing_metadata)."""
        start_ts = time.time()
        gen = get_generation_config(mode)
        if temperature_boost:
            # Social turns (greetings, thanks, check-ins) get a little more natural variation
            gen["temperature"] = min(1.0, gen["temperature"] + temperature_boost)
        if module != "chat":
            # Structured modules (exam JSON, repo analysis, code review) need room to finish
            gen["max_tokens"] = max(gen["max_tokens"], 3000)
        if deep_thinking:
            # User asked Zara to think harder: more reasoning and room, same personality
            gen["reasoning_effort"] = "high"
            gen["max_tokens"] = max(gen["max_tokens"], 3000)
        elif max_tokens_cap and module == "chat":
            # Short conversational turns (greetings, thanks, "ok") need a small budget → lower latency.
            # Floor keeps room for reasoning models' hidden tokens.
            gen["max_tokens"] = min(gen["max_tokens"], max(400, max_tokens_cap))

        providers = self._get_routing_order(mode, user_prompt)
        errors = []
        fallback_count = 0

        for provider_name, service in providers:
            if time.time() - start_ts > _ROUTE_DEADLINE_SECONDS:
                errors.append(f"{provider_name}: skipped, routing deadline exceeded")
                break

            if not service.health_check():
                errors.append(f"{provider_name}: not configured")
                fallback_count += 1
                continue

            try:
                logger.info(f"  → Calling {provider_name} (mode={mode}, module={module})")
                response = service.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    context=context,
                    temperature=gen["temperature"],
                    max_tokens=gen["max_tokens"],
                    reasoning_effort=gen.get("reasoning_effort"),
                )
                if not response or not response.strip():
                    raise ValueError("Provider returned empty response")

                latency_ms = float((time.time() - start_ts) * 1000)
                history_words = sum(len(str(m.get("content", "")).split()) for m in (context or {}).get("history", []))
                approx_tokens = int((len(system_prompt.split()) + history_words + len(user_prompt.split()) + len(response.split())) / 0.75)
                log_cost(provider_name, approx_tokens)
                _cost_log[-1].update({
                    "latency_ms": latency_ms,
                    "fallback_used": fallback_count > 0,
                    "fallbacks": fallback_count,
                    "mode": mode,
                    "task": task,
                })

                meta = {
                    "zara_model": f"zara-{mode}",
                    "provider": provider_name,
                    "fallback_used": fallback_count > 0,
                    "fallbacks": fallback_count,
                    "latency_ms": round(latency_ms, 1),
                }
                logger.info(f"  ✅ {provider_name} responded in {latency_ms/1000:.2f}s")
                return response, meta

            except Exception as e:
                logger.warning(f"  ❌ {provider_name} failed: {e}")
                errors.append(f"{provider_name}: {e}")
                fallback_count += 1
                continue

        error_summary = " | ".join(errors)
        kind = _classify_failure(errors)
        logger.error(f"All providers failed for mode={mode} (kind={kind}): {error_summary}")
        raise ProviderRoutingError(f"All AI providers failed. Details: {error_summary}", kind=kind)

    def route_request(
        self,
        mode: str,
        system_prompt: str,
        user_prompt: str,
        context: Optional[Dict[str, Any]] = None,
        module: str = "chat",
        task: str = "chat",
    ) -> str:
        """Backward-compatible wrapper returning only the response text."""
        text, _ = self.route_request_with_meta(mode, system_prompt, user_prompt, context, module, task)
        return text


# Singleton instance
llm_router = LLMRouter()
