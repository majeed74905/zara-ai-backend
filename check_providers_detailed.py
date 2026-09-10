"""
Direct Provider Validation Script
════════════════════════════════════════════════════════════════════════════════
Validates Groq, Gemini, and OpenRouter independently without exposing secret values.
"""

import sys
import os
import json
import time

sys.path.insert(0, ".")

from dotenv import load_dotenv
load_dotenv(".env", override=True)

from app.core.config import settings
from app.services.models.groq_service import GroqService
from app.services.models.gemini_service import GeminiService
from app.services.models.openrouter_service import OpenRouterService

def test_groq():
    print("\n--- 1. TESTING GROQ SERVICE ---")
    configured = bool(settings.GROQ_API_KEY)
    print(f"Configured in settings: {configured}")
    if not configured:
        return {"configured": False, "valid": False, "error": "Missing key"}
    
    svc = GroqService()
    model = svc.model_name
    print(f"Configured Model: {model}")
    
    try:
        res = svc.generate(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say 'Groq online' in 2 words."
        )
        print(f"Generation Result: SUCCESS ({res.strip()[:60]})")
        return {"configured": True, "valid": True, "model": model, "status": "200 OK"}
    except Exception as e:
        err_msg = str(e)
        status = "Invalid Key" if "401" in err_msg or "invalid_api_key" in err_msg else f"Error: {err_msg[:60]}"
        print(f"Generation Result: FAILED ({status})")
        return {"configured": True, "valid": False, "model": model, "status": status}

def test_gemini():
    print("\n--- 2. TESTING GEMINI SERVICE ---")
    configured = bool(settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY)
    print(f"Configured in settings: {configured}")
    if not configured:
        return {"configured": False, "valid": False, "error": "Missing key"}
    
    svc = GeminiService()
    model = svc.model_name
    print(f"Configured Model: {model}")
    
    try:
        res = svc.generate(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say 'Gemini online' in 2 words."
        )
        print(f"Generation Result: SUCCESS ({res.strip()[:60]})")
        return {"configured": True, "valid": True, "model": model, "status": "200 OK"}
    except Exception as e:
        err_msg = str(e)
        status = "Invalid Key" if "400" in err_msg or "API_KEY_INVALID" in err_msg or "not valid" in err_msg else f"Error: {err_msg[:60]}"
        print(f"Generation Result: FAILED ({status})")
        return {"configured": True, "valid": False, "model": model, "status": status}

def test_openrouter():
    print("\n--- 3. TESTING OPENROUTER SERVICE ---")
    configured = bool(settings.OPENROUTER_API_KEY)
    print(f"Configured in settings: {configured}")
    if not configured:
        return {"configured": False, "valid": False, "error": "Missing key"}
    
    svc = OpenRouterService()
    model = svc.model_name
    print(f"Configured Primary Model: {model}")
    
    try:
        res = svc.generate(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say 'OpenRouter online' in 2 words."
        )
        print(f"Generation Result: SUCCESS ({res.strip()[:60]})")
        return {"configured": True, "valid": True, "model": model, "status": "200 OK"}
    except Exception as e:
        err_msg = str(e)
        if "429" in err_msg or "Rate limit" in err_msg:
            status = "Rate Limited (429)"
        elif "401" in err_msg or "403" in err_msg:
            status = "Unauthorized (401)"
        else:
            status = f"Error: {err_msg[:60]}"
        print(f"Generation Result: FAILED ({status})")
        return {"configured": True, "valid": False, "model": model, "status": status}

if __name__ == "__main__":
    results = {
        "groq": test_groq(),
        "gemini": test_gemini(),
        "openrouter": test_openrouter(),
    }
    with open("provider_validation_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print("\nResults saved to provider_validation_results.json")
