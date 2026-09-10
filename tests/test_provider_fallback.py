"""Per-model quota fallback inside providers + cooldown parsing (fake clients, no network)."""

import time
from types import SimpleNamespace

import pytest

from app.services.models import base_llm, groq_service, gemini_service, openrouter_service
from app.services.models.base_llm import rate_limit_cooldown


@pytest.fixture(autouse=True)
def _reset_cooldowns():
    for mod in (groq_service, gemini_service, openrouter_service):
        mod._cooldowns.clear()
    yield
    for mod in (groq_service, gemini_service, openrouter_service):
        mod._cooldowns.clear()


GROQ_TPD = Exception(
    "Error code: 429 - {'error': {'message': 'Rate limit reached for model `openai/gpt-oss-120b` ... "
    "on tokens per day (TPD): Limit 200000, Used 198905, Requested 2733. Please try again in 11m47.616s.'}}"
)
GEMINI_RPD = Exception(
    "429 RESOURCE_EXHAUSTED. Quota exceeded for metric: generate_content_free_tier_requests, limit: 20 "
    "'quotaId': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier' Please retry in 40.16s."
)
OPENROUTER_DAILY = Exception(
    "Error code: 429 - {'error': {'message': 'Rate limit exceeded: free-models-per-day.', "
    f"'metadata': {{'headers': {{'X-RateLimit-Limit': '50', 'X-RateLimit-Reset': '{int((time.time() + 7200) * 1000)}'}}}}}}}}"
)


def test_cooldown_parsing():
    assert 700 < rate_limit_cooldown(GROQ_TPD) < 710          # 11m47s
    assert rate_limit_cooldown(GEMINI_RPD) == 1800.0           # daily cap, not the misleading 40s
    assert 7000 < rate_limit_cooldown(OPENROUTER_DAILY) < 7300 # until reported reset
    assert rate_limit_cooldown(Exception("Connection error.")) is None


def _groq_with(behaviour):
    svc = groq_service.GroqService.__new__(groq_service.GroqService)
    calls = []

    def create(**params):
        calls.append(params)
        outcome = behaviour(params["model"])
        if isinstance(outcome, Exception):
            raise outcome
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=outcome))])

    svc.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    svc.model_name = svc.AVAILABLE_MODELS[0]
    return svc, calls


def test_groq_falls_back_to_next_model_on_daily_limit_and_remembers():
    svc, calls = _groq_with(lambda m: GROQ_TPD if m == "openai/gpt-oss-120b" else f"hi from {m}")
    assert svc.generate("sys", "hi", reasoning_effort="low") == "hi from openai/gpt-oss-20b"
    assert [c["model"] for c in calls] == ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]
    # Second request skips the exhausted model entirely (no wasted call)
    calls.clear()
    svc.generate("sys", "hi again")
    assert [c["model"] for c in calls] == ["openai/gpt-oss-20b"]


def test_groq_qwen_hides_reasoning_and_gpt_oss_gets_effort():
    svc, calls = _groq_with(lambda m: "ok" if "qwen" in m else GROQ_TPD)
    svc.generate("sys", "hi", reasoning_effort="low")
    assert calls[0]["reasoning_effort"] == "low"
    qwen = [c for c in calls if "qwen" in c["model"]][0]
    assert qwen["reasoning_format"] == "hidden" and "reasoning_effort" not in qwen


def test_groq_all_models_exhausted_raises_rate_limit():
    svc, _ = _groq_with(lambda m: GROQ_TPD)
    with pytest.raises(Exception) as e1:
        svc.generate("sys", "hi")
    assert "429" in str(e1.value)
    with pytest.raises(Exception) as e2:  # now everything is cooling down → instant failure
        svc.generate("sys", "hi")
    assert "rate-limited" in str(e2.value)


def test_gemini_falls_back_across_models():
    svc = gemini_service.GeminiService.__new__(gemini_service.GeminiService)
    tried = []

    def generate_content(model, contents, config):
        tried.append(model)
        if model == "gemini-3.5-flash":
            raise GEMINI_RPD
        return SimpleNamespace(text=f"hello from {model}")

    svc.client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
    svc.model_name = svc.AVAILABLE_MODELS[0]
    second = svc.AVAILABLE_MODELS[1]
    assert svc.generate("sys", "hi") == f"hello from {second}"
    assert tried == ["gemini-3.5-flash", second]


def test_openrouter_daily_cap_skips_provider_without_calling():
    svc = openrouter_service.OpenRouterService.__new__(openrouter_service.OpenRouterService)
    count = {"n": 0}

    def create(**kw):
        count["n"] += 1
        raise OPENROUTER_DAILY

    svc.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    svc.extra_headers = {}
    svc.model_name = svc.AVAILABLE_MODELS[0]
    with pytest.raises(Exception):
        svc.generate("sys", "hi")
    with pytest.raises(RuntimeError) as e:
        svc.generate("sys", "hi")
    assert count["n"] == 1 and "rate limit" in str(e.value).lower()


def test_auth_error_does_not_try_other_models():
    svc, calls = _groq_with(lambda m: Exception("Error code: 401 - invalid_api_key"))
    with pytest.raises(Exception):
        svc.generate("sys", "hi")
    assert len(calls) == 1
    assert base_llm.is_auth_error(Exception("401 unauthorized"))
