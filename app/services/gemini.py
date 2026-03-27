import google.generativeai as genai
from app.core.config import settings

def get_gemini_response(prompt: str) -> str:
    if not settings.GEMINI_API_KEY:
        return "Gemini API Key not configured."
    
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        # Use a stable model
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini Error: {e}")
        return f"Error contacting Gemini: {str(e)}"
