
import sys
import os
import asyncio

# Add current directory to path so we can import app modules
sys.path.append(os.getcwd())

from app.services.models.gemini_service import GeminiService
from app.services.models.groq_service import GroqService

def test_services():
    print("Testing Gemini Service...")
    try:
        gemini = GeminiService()
        if gemini.health_check():
            print(f"Gemini using model: {gemini.model_name}")
            response = gemini.generate("System", "Hello")
            print(f"Gemini Response: {response[:50]}...")
        else:
            print("Gemini Service disabled (no API key).")
    except Exception as e:
        print(f"Gemini Test Failed: {e}")

    print("\nTesting Groq Service...")
    try:
        groq = GroqService()
        if groq.health_check():
            print(f"Groq using model: {groq.model_name}")
            response = groq.generate("System", "Hello")
            print(f"Groq Response: {response[:50]}...")
        else:
            print("Groq Service disabled (no API key).")
    except Exception as e:
        print(f"Groq Test Failed: {e}")

if __name__ == "__main__":
    test_services()
