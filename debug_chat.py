import requests
import json

url = "http://localhost:8000/api/v1/ai/chat"
headers = {"Content-Type": "application/json"}
data = {
    "message": "Hello",
    "model": "zara-fast"
}

try:
    response = requests.post(url, headers=headers, json=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response Text: {response.text}")
except Exception as e:
    print(f"Request Failed: {e}")
