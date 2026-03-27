import requests
import time

def check_url(url, retries=5):
    for i in range(retries):
        try:
            print(f"Checking {url}...")
            r = requests.get(url)
            print(f"Success! Status: {r.status_code}")
            return True
        except Exception as e:
            print(f"Attempt {i+1} failed: {e}")
            time.sleep(2)
    return False

check_url("http://127.0.0.1:5173/")
check_url("http://localhost:5173/")
