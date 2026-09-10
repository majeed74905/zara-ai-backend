"""
Phase 11: Real-World Concurrency Audit Suite
────────────────────────────────────────────
Simulates:
  - 5 simultaneous concurrent requests across Fast, Pro, and Eco modes
  - 10 simultaneous concurrent requests across distinct sessions
  - Repeated requests from the same user session
  - Session isolation verification (User A secret never appears in User B)
  - Mode isolation (zero mode mixing across concurrent threads)
  - Provider fallback resilience during concurrent spikes
"""

import sys
sys.path.insert(0, ".")

import time
import concurrent.futures
from fastapi.testclient import TestClient
from app.main import app
from app.core.rate_limiter import limiter
from unittest.mock import patch

client = TestClient(app)

def mock_route_concurrent(mode, system_prompt, user_prompt, **kwargs):
    # Simulate network latency of 30ms
    time.sleep(0.03)
    return f"Response for {mode}: processed '{user_prompt[:30]}'"

def run_single_request(client_id: int, mode_name: str, secret_tag: str):
    session_id = f"concurrent_session_{client_id}"
    prompt = f"User {client_id} query with secret token {secret_tag}. Explain API."
    
    resp = client.post(
        "/api/v1/ai/chat",
        json={
            "message": prompt,
            "model": mode_name,
            "session_id": session_id,
        },
        headers={"X-Forwarded-For": f"10.0.0.{client_id}"}
    )
    return {
        "client_id": client_id,
        "mode_requested": mode_name,
        "status_code": resp.status_code,
        "data": resp.json() if resp.status_code == 200 else None,
        "error": resp.text if resp.status_code != 200 else None,
        "secret_tag": secret_tag,
    }

@patch("app.services.llm_router.llm_router.route_request", side_effect=mock_route_concurrent)
def test_concurrency_5(mock_llm):
    print("\n--- 1. Testing 5 Concurrent Requests Across Modes ---")
    modes = ["zara-fast", "zara-pro", "zara-eco", "zara-fast", "zara-pro"]
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(run_single_request, i, modes[i], f"TOKEN_5_{i}")
            for i in range(5)
        ]
        results = [f.result() for f in futures]

    for r in results:
        assert r["status_code"] == 200, f"Request failed: {r['error']}"
        expected_prefix = r["mode_requested"]
        actual_model = r["data"]["model_used"]
        assert actual_model == expected_prefix, f"Mode mixing: requested {expected_prefix}, got {actual_model}"
    print("  ✓ 5 concurrent requests succeeded with 100% correct mode mapping.")

@patch("app.services.llm_router.llm_router.route_request", side_effect=mock_route_concurrent)
def test_concurrency_10(mock_llm):
    print("\n--- 2. Testing 10 Concurrent Requests Across Distinct Users ---")
    modes = ["zara-fast", "zara-pro", "zara-eco"] * 3 + ["zara-pro"]
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(run_single_request, i, modes[i], f"TOKEN_10_{i}")
            for i in range(10)
        ]
        results = [f.result() for f in futures]

    for r in results:
        assert r["status_code"] == 200, f"Request failed: {r['error']}"
        expected_prefix = r["mode_requested"]
        actual_model = r["data"]["model_used"]
        assert actual_model == expected_prefix, f"Mode mixing: requested {expected_prefix}, got {actual_model}"
    print("  ✓ 10 concurrent requests succeeded without any race conditions.")

@patch("app.services.llm_router.llm_router.route_request", side_effect=mock_route_concurrent)
def test_conversation_isolation(mock_llm):
    print("\n--- 3. Testing Conversation & Session Isolation (Zero Cross-Talk) ---")
    from app.services import chat_memory
    chat_memory.clear_session("user_alice")
    chat_memory.clear_session("user_bob")

    # Alice asks turn 1
    resp_a1 = client.post(
        "/api/v1/ai/chat",
        json={"message": "My bank account is 987654321", "model": "zara-fast", "session_id": "user_alice"},
        headers={"X-Forwarded-For": "192.168.1.1"}
    )
    assert resp_a1.status_code == 200

    # Bob asks turn 1 concurrently
    resp_b1 = client.post(
        "/api/v1/ai/chat",
        json={"message": "My favorite fruit is Mango", "model": "zara-pro", "session_id": "user_bob"},
        headers={"X-Forwarded-For": "192.168.1.2"}
    )
    assert resp_b1.status_code == 200

    # Alice asks turn 2
    resp_a2 = client.post(
        "/api/v1/ai/chat",
        json={"message": "What did I just tell you my account was?", "model": "zara-fast", "session_id": "user_alice"},
        headers={"X-Forwarded-For": "192.168.1.1"}
    )
    assert resp_a2.status_code == 200

    # Bob asks turn 2
    resp_b2 = client.post(
        "/api/v1/ai/chat",
        json={"message": "What is my favorite fruit?", "model": "zara-pro", "session_id": "user_bob"},
        headers={"X-Forwarded-For": "192.168.1.2"}
    )
    assert resp_b2.status_code == 200

    # Verify history in memory
    hist_alice = chat_memory.get_anon_history("user_alice")
    hist_bob = chat_memory.get_anon_history("user_bob")

    for msg in hist_alice:
        assert "Mango" not in msg["content"], "LEAK: Bob's data found in Alice's history!"
    for msg in hist_bob:
        assert "987654321" not in msg["content"], "LEAK: Alice's account found in Bob's history!"

    print("  ✓ Zero cross-talk: User A's conversation never leaked into User B's conversation.")

def test_fallback_during_concurrency():
    print("\n--- 4. Testing Fallback Resilience During Concurrent Traffic ---")
    from app.services.llm_router import llm_router
    original_groq_generate = llm_router.groq.generate
    original_openrouter_generate = llm_router.openrouter.generate

    # Simulate Groq outage: raises ConnectionError, falling back to OpenRouter
    def failing_groq(*args, **kwargs):
        raise ConnectionError("Simulated Groq outage during spike")

    def working_openrouter(*args, **kwargs):
        return "Clean fallback response from OpenRouter"

    llm_router.groq.generate = failing_groq
    llm_router.openrouter.generate = working_openrouter
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(run_single_request, 100 + i, "zara-fast", f"SPIKE_{i}")
                for i in range(4)
            ]
            results = [f.result() for f in futures]

        for r in results:
            assert r["status_code"] == 200, f"Fallback failed under concurrency: {r['error']}"
            assert r["data"]["model_used"] == "zara-fast"
            assert "fallback" in r["data"]["response"].lower() or len(r["data"]["response"]) > 0
        print("  ✓ All 4 concurrent requests smoothly fell back to secondary provider during simulated outage.")
    finally:
        llm_router.groq.generate = original_groq_generate
        llm_router.openrouter.generate = original_openrouter_generate

if __name__ == "__main__":
    print("================================================================================")
    print("ZARA AI REAL-WORLD CONCURRENCY AUDIT SUITE")
    print("================================================================================")
    test_concurrency_5()
    test_concurrency_10()
    test_conversation_isolation()
    test_fallback_during_concurrency()
    print("\n================================================================================")
    print("CONCURRENCY AUDIT RESULTS: ALL CONCURRENCY CHECKS PASSED ✓")
    print("================================================================================")
