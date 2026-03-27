import requests
import json
import time

url = "http://localhost:8000/api/v1/ai/chat"
headers = {"Content-Type": "application/json"}

# Give reload a moment
time.sleep(2)

data = {
    "message": "hi",
    "model": "zara-fast" # Using fast model to test the base instruction
}

print("Testing greeting response...")
try:
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        reply = response.json()['response']
        print(f"AI: {reply}")
        expected = "Hi! How can I help you today? 😊"
        if expected in reply:
            print("Verfication PASSED ✅")
        else:
            print("Verification FAILED ❌ - Response did not match exactly, checking for semantic similarity or cache issues.")
    else:
        print(f"Error: {response.status_code}")
except Exception as e:
    print(f"Request Failed: {e}")
