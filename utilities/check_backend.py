import requests
try:
    r = requests.get("http://localhost:8000/")
    print(f"Backend Status: {r.status_code}")
except Exception as e:
    print(f"Backend Failed: {e}")
