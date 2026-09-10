"""
Shared pytest fixtures.

Tests are hermetic: no real LLM provider is ever called. `fake_llm` replaces the
provider chain inside the router and records every system/user prompt it receives.
"""

import os
import sys

# Allow `pytest tests/` from the backend root without installing the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("SECRET_KEY", "test_secret_key")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

import pytest  # noqa: E402

from app.services import response_cache  # noqa: E402
from app.core.rate_limiter import limiter  # noqa: E402


class FakeProvider:
    def __init__(self, name, reply="Hey! 😊", fail_with=None):
        self.name = name
        self.reply = reply
        self.fail_with = fail_with
        self.calls = []

    def health_check(self):
        return True

    def generate(self, system_prompt, user_prompt, context=None, temperature=None, max_tokens=None, reasoning_effort=None):
        self.calls.append({
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "history": list((context or {}).get("history", [])),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "reasoning_effort": reasoning_effort,
        })
        if self.fail_with:
            raise self.fail_with
        return self.reply(system_prompt, user_prompt) if callable(self.reply) else self.reply


@pytest.fixture(autouse=True)
def _clean_state():
    response_cache.clear_cache()
    limiter._records.clear()
    yield
    response_cache.clear_cache()
    limiter._records.clear()


@pytest.fixture
def fake_llm(monkeypatch):
    """Replace all three providers with one recording fake; returns the fake."""
    from app.services import llm_router as router_module

    fake = FakeProvider("fake")
    router = router_module.llm_router
    monkeypatch.setattr(router, "_get_routing_order", lambda mode, user_prompt="": [("fake", fake)])
    return fake


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)
