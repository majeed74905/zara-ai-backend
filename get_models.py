import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("API_KEY")
genai.configure(api_key=api_key)

with open("models_list.txt", "w") as f:
    try:
        f.write("Listing models:\n")
        for m in genai.list_models():
            f.write(f"Model: {m.name}, Methods: {m.supported_generation_methods}\n")
    except Exception as e:
        f.write(f"Error: {e}\n")
