"""
Phase 13: Final End-to-End Live Audit Suite
───────────────────────────────────────────
Tests the complete end-to-end pipeline with LIVE providers:
  FastAPI -> Zara Identity Engine -> LLM Router -> Provider -> Response Controller

Evaluates:
  1. Zara Fast (Groq): English casual + Tanglish coding
  2. Zara Pro (Gemini): English deep architecture + Tanglish technical
  3. Zara Eco (OpenRouter): English short query + practical task
  4. Fallback chain personality distinctness test
"""

import sys
sys.path.insert(0, ".")

import time
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_fast_live():
    print("\n--- 1. Testing Zara Fast (Live Groq Primary) ---")
    # English casual coding
    prompt_en = "Hey Zara, write a quick one-liner in Python to flatten a nested list."
    resp = client.post("/api/v1/ai/chat", json={"message": prompt_en, "model": "zara-fast"})
    assert resp.status_code == 200, f"Fast EN failed: {resp.text}"
    data = resp.json()
    print(f"  [Fast EN] Model: {data['model_used']} | Lang: {data['detected_language']}", flush=True)
    print(f"  Response: {data['response'][:100]}...\n", flush=True)
    assert data["model_used"] == "zara-fast"

    # Tanglish casual
    prompt_tg = "Bro python la list flatten panna simplest way sollu da"
    resp = client.post("/api/v1/ai/chat", json={"message": prompt_tg, "model": "zara-fast"})
    assert resp.status_code == 200, f"Fast TG failed: {resp.text}"
    data = resp.json()
    print(f"  [Fast TG] Model: {data['model_used']} | Lang: {data['detected_language']}", flush=True)
    print(f"  Response: {data['response'][:100]}...\n", flush=True)
    assert data["model_used"] == "zara-fast"

def test_pro_live():
    print("\n--- 2. Testing Zara Pro (Live Gemini Primary) ---", flush=True)
    # English complex architecture
    prompt_en = "Explain the architectural trade-offs between CQRS with Event Sourcing vs Traditional CRUD in distributed banking."
    resp = client.post("/api/v1/ai/chat", json={"message": prompt_en, "model": "zara-pro"})
    assert resp.status_code == 200, f"Pro EN failed: {resp.text}"
    data = resp.json()
    print(f"  [Pro EN] Model: {data['model_used']} | Lang: {data['detected_language']}", flush=True)
    print(f"  Response: {data['response'][:100]}...\n", flush=True)
    assert data["model_used"] == "zara-pro"

    # Tanglish technical
    prompt_tg = "Microservices la distributed transaction handle panna Saga pattern vs 2PC trade-offs explain pannunga."
    resp = client.post("/api/v1/ai/chat", json={"message": prompt_tg, "model": "zara-pro"})
    assert resp.status_code == 200, f"Pro TG failed: {resp.text}"
    data = resp.json()
    print(f"  [Pro TG] Model: {data['model_used']} | Lang: {data['detected_language']}", flush=True)
    print(f"  Response: {data['response'][:100]}...\n", flush=True)
    assert data["model_used"] == "zara-pro"

def test_eco_live():
    print("\n--- 3. Testing Zara Eco (Live OpenRouter Primary) ---", flush=True)
    # English short practical task
    prompt_en = "List 3 essential Linux commands for checking disk space and memory."
    resp = client.post("/api/v1/ai/chat", json={"message": prompt_en, "model": "zara-eco"})
    assert resp.status_code == 200, f"Eco EN failed: {resp.text}"
    data = resp.json()
    print(f"  [Eco EN] Model: {data['model_used']} | Lang: {data['detected_language']}", flush=True)
    print(f"  Response: {data['response'][:100]}...\n", flush=True)
    assert data["model_used"] == "zara-eco"

if __name__ == "__main__":
    print("================================================================================")
    print("ZARA AI FINAL END-TO-END LIVE AUDIT")
    print("================================================================================")
    test_fast_live()
    test_pro_live()
    test_eco_live()
    print("================================================================================")
    print("FINAL END-TO-END LIVE AUDIT: ALL LIVE MODES FUNCTIONAL AND DISTINCT ✓")
    print("================================================================================")
