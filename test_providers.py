from app.services.models.gemini_service import GeminiService
from app.services.models.deepseek_service import DeepSeekService
from app.services.models.groq_service import GroqService
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_providers():
    print("----------------------------------------------------------------")
    print("Testing AI Providers...")
    print("----------------------------------------------------------------")

    # 1. Test Groq
    print("\n[1] Testing Groq (Zara Fast)...")
    try:
        groq = GroqService()
        if groq.health_check():
            res = groq.generate("System: Be concise.", "User: Say 'Groq OK'")
            print(f"SUCCESS: {res}")
        else:
            print("SKIPPED: Groq not configured.")
    except Exception as e:
        print(f"FAILED: {e}")

    # 2. Test DeepSeek
    print("\n[2] Testing DeepSeek (Zara Eco)...")
    try:
        ds = DeepSeekService()
        if ds.health_check():
            res = ds.generate("System: Be concise.", "User: Say 'DeepSeek OK'")
            print(f"SUCCESS: {res}")
        else:
            print("SKIPPED: DeepSeek not configured.")
    except Exception as e:
        print(f"FAILED: {e}")

    # 3. Test Gemini
    print("\n[3] Testing Gemini (Zara Pro)...")
    try:
        gemini = GeminiService()
        if gemini.health_check():
            res = gemini.generate("System: Be concise.", "User: Say 'Gemini OK'")
            print(f"SUCCESS: {res}")
        else:
            print("SKIPPED: Gemini not configured.")
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    test_providers()
