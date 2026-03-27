import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("GOOGLE_API_KEY") or os.getenv("API_KEY")
print(f"Using key: {key[:10]}...")

genai.configure(api_key=key)

model_name = "gemini-1.5-flash" # Trying 1.5 first
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

model_name_2 = "gemini-2.0-flash"
print(f"\nTesting model: {model_name_2}")
try:
    model = genai.GenerativeModel(
        model_name=model_name_2,
        system_instruction="You are a helpful assistant."
    )
    response = model.generate_content("Hello!")
    print("Response:", response.text)
except Exception as e:
    print("Error:", e)
