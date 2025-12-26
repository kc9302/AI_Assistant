import os
import sys
import time

# Add parent directory to sys.path
sys.path.append(os.getcwd())

from app.services.context_manager import context_manager

def test_context_manager():
    print("=== Testing Context Manager (SQLite) ===")
    
    thread_id = f"test_thread_{int(time.time())}"
    event_id = "evt_12345"
    summary = "Test Meeting Integration"
    
    print(f"1. Adding event: {summary} ({event_id}) to thread {thread_id}")
    context_manager.add_event(thread_id, event_id, summary)
    
    print("2. Retrieving recent events...")
    events = context_manager.get_recent_events(thread_id)
    
    if len(events) == 1:
        e = events[0]
        if e["event_id"] == event_id and e["summary"] == summary:
            print("✅ PASS: Event correctly saved and retrieved.")
        else:
            print(f"❌ FAIL: Data mismatch. Got: {e}")
    else:
        print(f"❌ FAIL: Expected 1 event, got {len(events)}")

if __name__ == "__main__":
    test_context_manager()
