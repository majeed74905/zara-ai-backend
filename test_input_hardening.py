"""
Test Suite: Input Hardening, Rate Limiting, and Session Isolation
─────────────────────────────────────────────────────────────────
Verifies that:
  - Empty or whitespace messages return HTTP 400
  - Oversized messages (>15k chars) return HTTP 413
  - Rate limiting triggers HTTP 429 after threshold
  - Anonymous session history is properly isolated per session_id
  - Health check includes database connectivity
  - X-Request-ID is generated and returned
"""

import sys
sys.path.insert(0, ".")

from fastapi.testclient import TestClient
from app.main import app
from app.core.rate_limiter import limiter
from unittest.mock import patch
import unittest

client = TestClient(app)

class TestInputHardening(unittest.TestCase):

    def setUp(self):
        # Reset limiter for test runs
        with limiter._lock:
            limiter._records.clear()

    def test_health_check_with_db(self):
        resp = client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("database", data)
        self.assertTrue("x-request-id" in resp.headers)
        print("  ✓ /health returns 200 with database status and X-Request-ID")

    def test_empty_message_rejected(self):
        resp = client.post("/api/v1/ai/chat", json={"message": "", "model": "zara-fast"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("cannot be empty", resp.json()["detail"])
        print("  ✓ Empty message rejected with 400")

    def test_whitespace_message_rejected(self):
        resp = client.post("/api/v1/ai/chat", json={"message": "    \n\t  ", "model": "zara-fast"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("cannot be empty", resp.json()["detail"])
        print("  ✓ Whitespace-only message rejected with 400")

    def test_oversized_message_rejected(self):
        huge_message = "A" * 16000
        resp = client.post("/api/v1/ai/chat", json={"message": huge_message, "model": "zara-fast"})
        self.assertEqual(resp.status_code, 413)
        self.assertIn("exceeds maximum allowed length", resp.json()["detail"])
        print("  ✓ 16,000 char message rejected with 413")

    @patch("app.services.llm_router.llm_router.route_request", return_value="Mocked response")
    def test_rate_limiting_triggers_429(self, mock_route):
        # We simulate rapid requests to trigger 429 (limit is 30/min)
        triggered_429 = False
        for i in range(35):
            resp = client.post("/api/v1/ai/chat", json={"message": f"ping {i}", "model": "zara-fast"})
            if resp.status_code == 429:
                triggered_429 = True
                self.assertIn("Retry-After", resp.headers)
                self.assertIn("Too many requests", resp.json()["detail"])
                break

        self.assertTrue(triggered_429, "Rate limiter did not trigger 429")
        print("  ✓ Rate limiter triggers HTTP 429 with Retry-After header")

    def test_session_isolation(self):
        from app.services import chat_memory
        # Verify Session A and Session B never share history
        chat_memory.clear_session("session_user_A")
        chat_memory.clear_session("session_user_B")

        chat_memory.save_anon_history("session_user_A", "My secret is Alpha", "Understood Alpha")
        chat_memory.save_anon_history("session_user_B", "My secret is Beta", "Understood Beta")

        hist_a = chat_memory.get_anon_history("session_user_A")
        hist_b = chat_memory.get_anon_history("session_user_B")

        self.assertEqual(len(hist_a), 2)
        self.assertEqual(len(hist_b), 2)
        self.assertIn("Alpha", hist_a[0]["content"])
        self.assertNotIn("Beta", hist_a[0]["content"])
        self.assertIn("Beta", hist_b[0]["content"])
        self.assertNotIn("Alpha", hist_b[0]["content"])
        print("  ✓ Anonymous session memory strictly isolated between users")

if __name__ == "__main__":
    unittest.main()
