"""
LLM Router — Zara AI Phase 2 & 3
──────────────────────────────────────────────────────────────────────────────
Mode-based intelligent routing:

  Zara Fast  → Groq           (low-latency, concise, temperature=0.5)
  Zara Pro   → Gemini         (deep, structured, temperature=0.7)
  Zara Eco   → OpenRouter     (thoughtful, calm, temperature=0.6)

Fallback chain per mode:
  Fast: Groq → OpenRouter → Gemini
  Pro:  Gemini → Groq → OpenRouter
  Eco:  OpenRouter → Gemini → Groq

Also includes:
  - Cost tracking (estimated tokens per call)
  - Structured per-call logging
  - Response validation (no empty/garbage outputs)
"""

from app.services.models.gemini_service import GeminiService
from app.services.models.openrouter_service import OpenRouterService
from app.services.models.groq_service import GroqService
from typing import Dict, Any, Optional
import logging
import time

logger = logging.getLogger(__name__)

# ── Approximate token costs (USD per 1K tokens, input+output blended rough estimate)
_COST_PER_1K = {
    "groq": 0.0002,        # Groq is extremely cheap
    "gemini": 0.0005,      # Gemini 1.5-flash
    "openrouter": 0.0006,  # Mixtral on OpenRouter
}

# Cost tracker (in-session accumulator; reset on restart)
_cost_log: list = []


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
    total_cost = sum(e["estimated_cost_usd"] for e in _cost_log)
    total_tokens = sum(e["approx_tokens"] for e in _cost_log)
    by_provider = {}
    for entry in _cost_log:
        p = entry["provider"]
        by_provider.setdefault(p, {"calls": 0, "tokens": 0, "cost": 0.0})
        by_provider[p]["calls"] += 1
        by_provider[p]["tokens"] += entry["approx_tokens"]
        by_provider[p]["cost"] = round(by_provider[p]["cost"] + entry["estimated_cost_usd"], 6)
    return {
        "total_calls": len(_cost_log),
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 6),
        "by_provider": by_provider,
    }


class LLMRouter:
    """
    Central dispatcher that selects the right provider based on mode,
    with graceful fallback chains.
    """

    def __init__(self):
        self.gemini = GeminiService()       # Pro mode provider
        self.groq = GroqService()           # Fast mode provider
        self.openrouter = OpenRouterService()  # Eco mode provider
        logger.info("LLMRouter initialized. Providers: Groq(Fast) | Gemini(Pro) | OpenRouter(Eco)")

    def _get_routing_order(self, mode: str, user_prompt: str) -> list:
        """
        Smart Routing: Task-aware model selection.
        Picks the best provider based on mode BUT overrides for specific tasks like coding.
        """
        user_prompt_low = user_prompt.lower()
        
        # 💻 CODE TASKS -> Prefer Groq (fastest/great with Llama-3) or Gemini
        is_code = any(kw in user_prompt_low for kw in ["code", "python", "js", "react", "html", "debug", "sql", "css"])
        
        # 🏛️ EXPLAIN/RESEARCH -> Prefer Gemini (Pro)
        is_research = any(kw in user_prompt_low for kw in ["explain", "research", "summarize", "detail", "compare", "deep"])

        if is_code:
            logger.info("👨‍💻 Task detected: Coding. Prioritizing Groq/Gemini.")
            return [("groq", self.groq), ("gemini", self.gemini), ("openrouter", self.openrouter)]
            
        if is_research and mode == "pro":
            logger.info("🏛️ Task detected: Research. Prioritizing Gemini.")
            return [("gemini", self.gemini), ("groq", self.groq), ("openrouter", self.openrouter)]

        # --- MODE-BASED DEFAULTS ---
        if mode == "fast":
            return [("groq", self.groq), ("openrouter", self.openrouter), ("gemini", self.gemini)]
        elif mode == "pro":
            return [("gemini", self.gemini), ("groq", self.groq), ("openrouter", self.openrouter)]
        else:
            return [("openrouter", self.openrouter), ("gemini", self.gemini), ("groq", self.groq)]

    def route_request(
        self,
        mode: str,
        system_prompt: str,
        user_prompt: str,
        context: Optional[Dict[str, Any]] = None,
        module: str = "chat",
        task: str = "chat",
    ) -> str:
        """
        Route a request with enhanced analytics and fallback tracking.
        """
        logger.info(f"🚦 Routing: mode={mode}, module={module}, task={task}")
        start_ts = time.time()
        
        # Dynamic routing order based on task awareness
        providers = self._get_routing_order(mode, user_prompt)
        
        errors = []
        fallback_count = 0

        for provider_name, service in providers:
            if not service.health_check():
                logger.warning(f"  ⚠️  {provider_name} health check failed, skipping.")
                errors.append(f"{provider_name}: not configured")
                fallback_count += 1
                continue

            try:
                logger.info(f"  → Calling {provider_name} (mode={mode})")
                response = service.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    context=context
                )

                if not response or not response.strip():
                    raise ValueError("Provider returned empty response")

                # Success! Log detailed analytics
                latency_ms = float((time.time() - start_ts) * 1000)
                approx_tokens = (len(system_prompt.split()) + len(user_prompt.split()) + len(response.split())) // 0.75
                
                log_cost(provider_name, int(approx_tokens))
                if _cost_log:
                    _cost_log[-1]["latency_ms"] = latency_ms
                    _cost_log[-1]["fallback_used"] = fallback_count > 0
                    _cost_log[-1]["fallbacks"] = fallback_count
                    _cost_log[-1]["mode"] = mode
                    _cost_log[-1]["task"] = task
                
                logger.info(f"  ✅ {provider_name} responded in {latency_ms/1000:.2f}s")
                return response

            except Exception as e:
                logger.warning(f"  ❌ {provider_name} failed: {e}")
                errors.append(f"{provider_name}: {e}")
                fallback_count += 1
                continue

        # If all providers fail
        error_summary = " | ".join(errors)
        logger.error(f"All providers failed for mode={mode}: {error_summary}")
        raise RuntimeError(f"All AI providers failed. Details: {error_summary}")


# Singleton instance
llm_router = LLMRouter()
