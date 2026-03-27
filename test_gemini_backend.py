import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("API_KEY")
print(f"Testing with key: {api_key[:10]}...")

genai.configure(api_key=api_key)

try:
    print("Listing models in Python SDK...")
    for m in genai.list_models():
        print(f"Model: {m.name}")
except Exception as e:
    print(f"Error listing: {e}")

try:
    print("Generating content with gemini-1.5-flash...")
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content("Hi")
    print(f"Success: {response.text}")
except Exception as e:
    print(f"Error generating: {e}")
