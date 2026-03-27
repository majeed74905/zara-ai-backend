
import sys
import os
import google.generativeai as genai
from app.core.config import settings

def check_gemini_models():
    try:
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            print("No GEMINI_API_KEY found in settings.")
            return

        genai.configure(api_key=api_key)
        print("Listing available Gemini models...")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(m.name)
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    check_gemini_models()
