import requests
import uuid
import sys

BASE_URL = "http://localhost:8000/api/v1"
EMAIL = f"e2e_test_{uuid.uuid4().hex[:8]}@example.com"
PASSWORD = "TestPassword123!"
NEW_PASSWORD = "NewPassword456!"

def main():
    print("Starting E2E Test (API Response Mode)...")
    
    # 1. Register
    print("\n--- 1. Registering User ---")
    reg_data = {"email": EMAIL, "password": PASSWORD, "full_name": "E2E Test User"}
    r = requests.post(f"{BASE_URL}/auth/register", json=reg_data)
    if r.status_code != 200:
        print(f"Registration Failed: {r.text}")
        sys.exit(1)
    
    resp_data = r.json()
    token = resp_data.get("token")
    if not token:
        print("FATAL: Token not found in registration response.")
        sys.exit(1)
    
    print(f"Registration Success. Token: {token[:10]}...")

    # 3. Verify Email
    print("\n--- 3. Verifying Email ---")
    r = requests.post(f"{BASE_URL}/auth/verify-email", json={"token": token})
    print(f"Verification Response: {r.status_code} {r.text}")
    if r.status_code != 200:
        print("Verification Failed.")
        sys.exit(1)

    # 4. Login
    print("\n--- 4. Logging In ---")
    login_data = {"username": EMAIL, "password": PASSWORD}
    r = requests.post(f"{BASE_URL}/auth/login", data=login_data)
    print(f"Login Response: {r.status_code}")
    if r.status_code != 200:
        print(f"Login Failed: {r.text}")
        sys.exit(1)
    print("Login Successful.")

    # 5. Forgot Password
    print("\n--- 5. Forgot Password ---")
    r = requests.post(f"{BASE_URL}/auth/forgot-password", json={"email": EMAIL})
    if r.status_code != 200:
        print(f"Forgot Password Failed: {r.text}")
        sys.exit(1)
        
    resp_data = r.json()
    reset_token = resp_data.get("token")
    if not reset_token:
        print("FATAL: Reset token not found in response.")
        sys.exit(1)
    print(f"Reset Token Found: {reset_token[:10]}...")

    # 7. Reset Password
    print("\n--- 7. Resetting Password ---")
    r = requests.post(f"{BASE_URL}/auth/reset-password", json={"token": reset_token, "new_password": NEW_PASSWORD})
    print(f"Reset Response: {r.status_code} {r.text}")
    if r.status_code != 200:
        print("Reset Failed.")
        sys.exit(1)

    # 8. Login with New Password
    print("\n--- 8. Logging In with New Password ---")
    login_data = {"username": EMAIL, "password": NEW_PASSWORD}
    r = requests.post(f"{BASE_URL}/auth/login", data=login_data)
    if r.status_code == 200:
        print("SUCCESS: End-to-End Test Passed!")
    else:
        print(f"Login with new password Failed: {r.text}")
        sys.exit(1)

if __name__ == "__main__":
    main()
