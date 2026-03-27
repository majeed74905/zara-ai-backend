import sys
import os
sys.path.append(os.getcwd())

from app.services.models.gemini_service import GeminiService
from app.services.models.groq_service import GroqService
from app.services.models.deepseek_service import DeepSeekService

print("=" * 60)
print("TESTING ALL AI SERVICES")
print("=" * 60)

# Test Groq
print("\n1. GROQ SERVICE")
print("-" * 60)
try:
    groq = GroqService()
    if groq.health_check():
        print(f"✅ Model: {groq.model_name}")
        response = groq.generate("You are a helpful assistant.", "Say 'Hello' in one word.")
        print(f"✅ Response: {response}")
    else:
        print("❌ Service disabled (no API key)")
except Exception as e:
    print(f"❌ Error: {e}")

# Test DeepSeek
print("\n2. DEEPSEEK SERVICE")
print("-" * 60)
try:
    deepseek = DeepSeekService()
    if deepseek.health_check():
        print(f"✅ Model: {deepseek.model_name}")
        response = deepseek.generate("You are a helpful assistant.", "Say 'Hello' in one word.")
        print(f"✅ Response: {response}")
    else:
        print("❌ Service disabled (no API key)")
except Exception as e:
    print(f"❌ Error: {e}")

# Test Gemini
print("\n3. GEMINI SERVICE")
print("-" * 60)
try:
    gemini = GeminiService()
    if gemini.health_check():
        print(f"✅ Model: {gemini.model_name}")
        response = gemini.generate("You are a helpful assistant.", "Say 'Hello' in one word.")
        print(f"✅ Response: {response}")
    else:
        print("❌ Service disabled (no API key)")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
