import requests
import json

# Test the chat endpoint
url = "http://127.0.0.1:8000/api/v1/ai/chat"

payload = {
    "message": "Hello, can you help me?",
    "module": "chat",
    "task": "general"
}

headers = {
    "Content-Type": "application/json"
}

print("Testing /api/v1/ai/chat endpoint...")
print(f"Payload: {json.dumps(payload, indent=2)}")

try:
    response = requests.post(url, json=payload, headers=headers)
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")
