import requests
import time
import sys

BASE_URL = "http://localhost:8000"

def check_status():
    try:
        response = requests.get(f"{BASE_URL}/status")
        if response.status_code == 200:
            data = response.json()
            print(f"Server Status: {data}")
            if "version" in data and data["version"] == "debug-1-check":
                return True
            else:
                print("Server is running but not the latest version (missing 'debug-1-check').")
                return False
        else:
            print(f"Server returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("Server not reachable yet...")
        return False

def test_chat():
    print("\nTesting /api/chat endpoint...")
    payload = {
        "message": "내일 일정 알려줘",
        "thread_id": "verify-session-1"
    }
    try:
        response = requests.post(f"{BASE_URL}/api/chat", json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        if response.status_code == 200:
            print("✅ API Test Passed!")
        else:
            print("❌ API Test Failed.")
    except Exception as e:
        print(f"Error testing chat: {e}")

if __name__ == "__main__":
    print("Checking backend server status...")
    # Try 5 times
    for i in range(5):
        if check_status():
            print("✅ Server is up and running latest code.")
            test_chat()
            sys.exit(0)
        time.sleep(2)
    
    print("\n⚠️ Server is not running the latest code. Please RESTART the backend server.")
