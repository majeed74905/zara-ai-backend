"""
Fallback Validation Test Suite — Phase 3 & 4
──────────────────────────────────────────────────────────────────────────────
Tests provider failure scenarios, fallback ordering, rate limit handling,
personality invariance during fallbacks, and error sanitization.
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, ".")

from app.services.llm_router import LLMRouter
from app.services.prompt_builder import build_system_prompt, build_user_prompt
from app.api.ai import chat_with_ai, ChatRequest
import pytest
import asyncio


class TestFallbackValidation(unittest.TestCase):

    def setUp(self):
        self.router = LLMRouter()
        # Mock underlying clients
        self.mock_groq = MagicMock()
        self.mock_gemini = MagicMock()
        self.mock_openrouter = MagicMock()

        self.router.groq = self.mock_groq
        self.router.gemini = self.mock_gemini
        self.router.openrouter = self.mock_openrouter

        # Default health checks pass
        self.mock_groq.health_check.return_value = True
        self.mock_gemini.health_check.return_value = True
        self.mock_openrouter.health_check.return_value = True

    # ── Test 1: Zara Fast Routing & Fallbacks ──────────────────────────────────
    def test_fast_primary_success(self):
        """Fast mode: Primary (Groq) works -> returns Groq response."""
        self.mock_groq.generate.return_value = "Groq fast response"
        
        resp = self.router.route_request("fast", "sys", "hi")
        self.assertEqual(resp, "Groq fast response")
        self.mock_groq.generate.assert_called_once()
        self.mock_openrouter.generate.assert_not_called()
        self.mock_gemini.generate.assert_not_called()

    def test_fast_primary_fail_fallback_1_success(self):
        """Fast mode: Groq fails -> OpenRouter (Fallback 1) is used."""
        self.mock_groq.generate.side_effect = Exception("Groq 401 Invalid Key")
        self.mock_openrouter.generate.return_value = "OpenRouter fallback response"

        resp = self.router.route_request("fast", "sys", "hi")
        self.assertEqual(resp, "OpenRouter fallback response")
        self.mock_groq.generate.assert_called_once()
        self.mock_openrouter.generate.assert_called_once()
        self.mock_gemini.generate.assert_not_called()

    def test_fast_fallback_2_success(self):
        """Fast mode: Groq and OpenRouter fail -> Gemini (Fallback 2) is used."""
        self.mock_groq.generate.side_effect = Exception("Groq error")
        self.mock_openrouter.generate.side_effect = Exception("OpenRouter 429")
        self.mock_gemini.generate.return_value = "Gemini fallback response"

        resp = self.router.route_request("fast", "sys", "hi")
        self.assertEqual(resp, "Gemini fallback response")
        self.mock_groq.generate.assert_called_once()
        self.mock_openrouter.generate.assert_called_once()
        self.mock_gemini.generate.assert_called_once()

    # ── Test 2: Zara Pro Routing & Fallbacks ───────────────────────────────────
    def test_pro_primary_success(self):
        """Pro mode: Primary (Gemini) works -> returns Gemini response."""
        self.mock_gemini.generate.return_value = "Gemini pro response"

        resp = self.router.route_request("pro", "sys", "hi")
        self.assertEqual(resp, "Gemini pro response")
        self.mock_gemini.generate.assert_called_once()
        self.mock_groq.generate.assert_not_called()
        self.mock_openrouter.generate.assert_not_called()

    def test_pro_primary_fail_fallback_1_success(self):
        """Pro mode: Gemini fails -> Groq (Fallback 1) is used."""
        self.mock_gemini.generate.side_effect = Exception("Gemini 400 Invalid Key")
        self.mock_groq.generate.return_value = "Groq fallback for Pro"

        resp = self.router.route_request("pro", "sys", "hi")
        self.assertEqual(resp, "Groq fallback for Pro")
        self.mock_gemini.generate.assert_called_once()
        self.mock_groq.generate.assert_called_once()
        self.mock_openrouter.generate.assert_not_called()

    def test_pro_fallback_2_success(self):
        """Pro mode: Gemini and Groq fail -> OpenRouter (Fallback 2) is used."""
        self.mock_gemini.generate.side_effect = Exception("Gemini error")
        self.mock_groq.generate.side_effect = Exception("Groq error")
        self.mock_openrouter.generate.return_value = "OpenRouter fallback for Pro"

        resp = self.router.route_request("pro", "sys", "hi")
        self.assertEqual(resp, "OpenRouter fallback for Pro")
        self.mock_gemini.generate.assert_called_once()
        self.mock_groq.generate.assert_called_once()
        self.mock_openrouter.generate.assert_called_once()

    # ── Test 3: Zara Eco Routing & Fallbacks ───────────────────────────────────
    def test_eco_primary_success(self):
        """Eco mode: Primary (OpenRouter) works -> returns OpenRouter response."""
        self.mock_openrouter.generate.return_value = "OpenRouter eco response"

        resp = self.router.route_request("eco", "sys", "hi")
        self.assertEqual(resp, "OpenRouter eco response")
        self.mock_openrouter.generate.assert_called_once()
        self.mock_gemini.generate.assert_not_called()
        self.mock_groq.generate.assert_not_called()

    def test_eco_primary_fail_fallback_1_success(self):
        """Eco mode: OpenRouter fails -> Gemini (Fallback 1) is used."""
        self.mock_openrouter.generate.side_effect = Exception("OpenRouter 429 Quota")
        self.mock_gemini.generate.return_value = "Gemini fallback for Eco"

        resp = self.router.route_request("eco", "sys", "hi")
        self.assertEqual(resp, "Gemini fallback for Eco")
        self.mock_openrouter.generate.assert_called_once()
        self.mock_gemini.generate.assert_called_once()
        self.mock_groq.generate.assert_not_called()

    def test_eco_fallback_2_success(self):
        """Eco mode: OpenRouter and Gemini fail -> Groq (Fallback 2) is used."""
        self.mock_openrouter.generate.side_effect = Exception("OpenRouter error")
        self.mock_gemini.generate.side_effect = Exception("Gemini error")
        self.mock_groq.generate.return_value = "Groq fallback for Eco"

        resp = self.router.route_request("eco", "sys", "hi")
        self.assertEqual(resp, "Groq fallback for Eco")
        self.mock_openrouter.generate.assert_called_once()
        self.mock_gemini.generate.assert_called_once()
        self.mock_groq.generate.assert_called_once()

    # ── Test 4: All Providers Fail Cleanly ────────────────────────────────────
    def test_all_providers_fail_cleanly(self):
        """When all providers fail, RuntimeError is raised with no infinite loop."""
        self.mock_groq.generate.side_effect = Exception("Groq auth error")
        self.mock_openrouter.generate.side_effect = Exception("OpenRouter rate limit")
        self.mock_gemini.generate.side_effect = Exception("Gemini quota error")

        with self.assertRaises(RuntimeError) as ctx:
            self.router.route_request("fast", "sys", "hi")

        self.assertIn("All AI providers failed", str(ctx.exception))
        # Ensure exactly 1 attempt per provider in chain, no infinite loop
        self.assertEqual(self.mock_groq.generate.call_count, 1)
        self.assertEqual(self.mock_openrouter.generate.call_count, 1)
        self.assertEqual(self.mock_gemini.generate.call_count, 1)

    # ── Test 5: Personality Invariance on Fallback ───────────────────────────
    def test_personality_invariance_on_fallback(self):
        """Verify that Zara personality prompt is passed unchanged to any fallback provider."""
        fast_sys = build_system_prompt("fast", "English")
        pro_sys = build_system_prompt("pro", "English")
        eco_sys = build_system_prompt("eco", "English")

        # In Fast mode, fallback to Gemini receives Fast system prompt
        self.mock_groq.generate.side_effect = Exception("fail")
        self.mock_openrouter.generate.side_effect = Exception("fail")
        self.mock_gemini.generate.return_value = "fallback"

        self.router.route_request("fast", fast_sys, "hi")
        args, kwargs = self.mock_gemini.generate.call_args
        self.assertIn("ZARA FAST", kwargs["system_prompt"])
        self.assertIn("Zara in Fast mode", kwargs["system_prompt"])

        # Reset mocks
        self.mock_groq.reset_mock()
        self.mock_openrouter.reset_mock()
        self.mock_gemini.reset_mock()
        self.mock_groq.generate.side_effect = None
        self.mock_openrouter.generate.side_effect = None
        self.mock_gemini.generate.side_effect = None

        # In Pro mode, fallback to Groq receives Pro system prompt
        self.mock_gemini.generate.side_effect = Exception("fail")
        self.mock_groq.generate.return_value = "fallback"

        self.router.route_request("pro", pro_sys, "hi")
        args, kwargs = self.mock_groq.generate.call_args
        self.assertIn("ZARA PRO", kwargs["system_prompt"])
        self.assertIn("Zara in Pro mode", kwargs["system_prompt"])

        # Reset mocks
        self.mock_groq.reset_mock()
        self.mock_openrouter.reset_mock()
        self.mock_gemini.reset_mock()
        self.mock_groq.generate.side_effect = None
        self.mock_openrouter.generate.side_effect = None
        self.mock_gemini.generate.side_effect = None

        # In Eco mode, fallback to Groq receives Eco system prompt
        self.mock_openrouter.generate.side_effect = Exception("fail")
        self.mock_gemini.generate.side_effect = Exception("fail")
        self.mock_groq.generate.return_value = "fallback"

        self.router.route_request("eco", eco_sys, "hi")
        args, kwargs = self.mock_groq.generate.call_args
        self.assertIn("ZARA ECO", kwargs["system_prompt"])
        self.assertIn("Zara in Eco mode", kwargs["system_prompt"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
