import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_admin_login():
    print("\nTesting Admin Login...")
    login_data = {
        "username": "admin",
        "password": "admin"
    }
    response = requests.post(f"{BASE_URL}/login", json=login_data)
    if response.statusCode == 200:
        token = response.json()["access_token"]
        print(f"Login successful. Token: {token[:20]}...")
        return token
    else:
        print(f"Login failed: {response.status_code} - {response.text}")
        return None

def test_endpoints(token):
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test /me
    print("\nTesting /me...")
    response = requests.get(f"{BASE_URL}/me", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    # Test /vehicles
    print("\nTesting /vehicles (GET)...")
    response = requests.get(f"{BASE_URL}/vehicles", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    # Test /vehicles (POST)
    print("\nTesting /vehicles (POST)...")
    vehicle_data = {"plate_number": "TEST 1234"}
    response = requests.post(f"{BASE_URL}/vehicles", json=vehicle_data, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    # Test /violations
    print("\nTesting /violations (GET)...")
    response = requests.get(f"{BASE_URL}/violations", headers=headers)
    print(f"Status: {response.status_code}")
    # print(f"Response: {json.dumps(response.json(), indent=2)}")

if __name__ == "__main__":
    # Note: This script assumes the server is running on localhost:8000
    # Since I cannot guarantee the server state, I'll just check if's reachable
    try:
        token = test_admin_login()
        if token:
            test_endpoints(token)
    except Exception as e:
        print(f"Error connecting to server: {e}")
