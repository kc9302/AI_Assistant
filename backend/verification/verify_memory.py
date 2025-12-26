import requests
import json
import os

BASE_URL = "http://127.0.0.1:8000"

def test_chat_persistence():
    thread_id = "test_thread_123"
    payload = {
        "message": "안녕, 나는 오전 회의를 선호해. 오늘 내 일정 좀 알려줘.",
        "thread_id": thread_id
    }
    
    print(f"Sending request to {BASE_URL}/api/chat...")
    response = requests.post(f"{BASE_URL}/api/chat", json=payload)
    
    if response.status_code == 200:
        print("Response received successfully.")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        
        # Check if session file exists
        session_path = f"data/sessions/{thread_id}.json"
        if os.path.exists(session_path):
            print(f"PASS: Session file found at {session_path}")
        else:
            print(f"FAIL: Session file NOT found at {session_path}")
            
        # Check if user profile was initialized
        profile_path = "data/user_profile.json"
        if os.path.exists(profile_path):
            print(f"PASS: User profile found at {profile_path}")
        else:
            print(f"FAIL: User profile NOT found at {profile_path}")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_chat_persistence()
