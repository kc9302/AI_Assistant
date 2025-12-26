import asyncio
from fastapi.testclient import TestClient
from app.main import app
import json

client = TestClient(app)

def test_planner_execute_flow():
    print("Testing End-to-End Planner/Executor Flow...")
    payload = {
        "message": "내일 오후 3시에 팀 회의 잡아줘",
        "thread_id": "test-refactor-1"
    }
    
    try:
        response = client.post("/api/chat", json=payload)
        print(f"Status Code: {response.status_code}")
        data = response.json()
        
        print("\nResponse Data:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        # We expect mode to be 'execute' or 'plan' 
        # Since it's a clear request, it should probably be 'execute' or asking for confirmation
        if "response" in data:
            print(f"\nSUCCESS: Received response: {data['response']}")
        else:
            print("\nFAILURE: Missing 'response' in output.")
            
    except Exception as e:
        print(f"\nFAILURE: Test crashed: {e}")

def test_planner_question_flow():
    print("\nTesting Planner Question Flow (Ambiguous Request)...")
    payload = {
        "message": "회의 하나 잡아줘", # No time provided
        "thread_id": "test-refactor-2"
    }
    
    try:
        response = client.post("/api/chat", json=payload)
        data = response.json()
        print(f"Status Code: {response.status_code}")
        print(f"Mode: {data.get('mode')}")
        print(f"Response: {data.get('response')}")
        
        if data.get('mode') == 'plan':
            print("SUCCESS: Planner correctly identified missing information.")
        else:
            print("WARNING: Planner did not return 'plan' mode for ambiguous request.")
            
    except Exception as e:
        print(f"FAILURE: Test crashed: {e}")

if __name__ == "__main__":
    test_planner_execute_flow()
    test_planner_question_flow()
