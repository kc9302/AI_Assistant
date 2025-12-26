import requests
import json
from datetime import datetime, timedelta, timezone

BASE_URL = "http://127.0.0.1:8000"

def test_temporal_and_language():
    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst)
    print(f"Current KST Time: {now.strftime('%Y-%m-%d %H:%M:%S %A')}")
    
    scenarios = [
        {
            "name": "Korean - Tomorrow",
            "message": "내일 일정 알려줘",
            "expected_lang": "ko",
            "check_content": ["내일", "일정"]
        },
        {
            "name": "English - Today",
            "message": "Tell me my schedule today",
            "expected_lang": "en",
            "check_content": ["today", "schedule"]
        }
    ]
    
    for scenario in scenarios:
        print(f"\n--- Testing Scenario: {scenario['name']} ---")
        payload = {
            "message": scenario["message"],
            "thread_id": f"temp_test_{scenario['name'].replace(' ', '_')}"
        }
        
        response = requests.post(f"{BASE_URL}/api/chat", json=payload)
        
        if response.status_code == 200:
            result = response.json()
            ai_msg = result.get("response", "")
            print(f"AI Response: {ai_msg}")
            
            # Improved language detection: check ratio of Korean characters
            korean_chars = sum(1 for char in ai_msg if ord(char) > 0x1100)
            is_mainly_korean = korean_chars / len(ai_msg) > 0.3 if ai_msg else False
            
            if scenario["expected_lang"] == "ko":
                if is_mainly_korean:
                    print("PASS: Language is Korean as expected.")
                else:
                    print("FAIL: Expected Korean but got something else.")
            else:
                if not is_mainly_korean:
                    print("PASS: Language is English as expected.")
                else:
                    print("FAIL: Expected English but got Korean.")
        else:
            print(f"Error: {response.status_code}")
            print(response.text)

if __name__ == "__main__":
    test_temporal_and_language()
