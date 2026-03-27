import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("GOOGLE_API_KEY") or os.getenv("API_KEY")
genai.configure(api_key=key)

model_name = "models/gemini-1.5-flash"
print(f"Testing model: {model_name}")

try:
    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction="You are a helpful assistant."
    )
    response = model.generate_content("Hello!")
    print("Response:", response.text)
except Exception as e:
    print("Error:", e)
