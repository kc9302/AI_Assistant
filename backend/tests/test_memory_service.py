import sys
import os
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.memory import MemoryService

def test_memory_service():
    ms = MemoryService()
    test_thread_id = "test_session_123"
    messages = [
        HumanMessage(content="Hello"),
        AIMessage(content="Hi there!")
    ]

    print("--- Test 1: Save Session ---")
    ms.save_session(test_thread_id, messages)
    date_str = datetime.now().strftime("%Y-%m-%d")
    expected_path = os.path.join("data", "sessions", date_str, f"{test_thread_id}.json")
    if os.path.exists(expected_path):
        print(f"✅ Created: {expected_path}")
    else:
        print(f"❌ Failed to create: {expected_path}")

    print("\n--- Test 2: Load Session (New Format) ---")
    loaded = ms.load_session(test_thread_id)
    if len(loaded) == 2 and loaded[0].content == "Hello":
        print("✅ Session correctly loaded.")
    else:
        print(f"❌ Load failed. Count: {len(loaded)}")

    print("\n--- Test 3: List Dates and Sessions ---")
    dates = ms.list_all_dates()
    print(f"All dates: {dates}")
    if date_str in dates:
        print(f"✅ Today's date {date_str} in list.")
        
    sessions = ms.list_sessions_by_date(date_str)
    print(f"Sessions for {date_str}: {sessions}")
    if test_thread_id in sessions:
        print(f"✅ Thread {test_thread_id} in list.")

    print("\n--- Test 4: Backward Compatibility ---")
    # Simulate an old file
    old_file_name = f"old_thread_2024-01-01.json"
    old_path = os.path.join("data", "sessions", old_file_name)
    
    # Use save_session logic but with old filename to simulate
    temp_messages = [HumanMessage(content="Old message")]
    # Note: save_session now creates directories, so we manually create a file in SESSIONS_DIR
    from langchain_core.messages import message_to_dict
    import json
    data = [message_to_dict(m) for m in temp_messages]
    with open(old_path, "w", encoding="utf-8") as f:
        json.dump({"messages": data}, f)
    
    loaded_old = ms.load_session("old_thread")
    if len(loaded_old) == 1 and loaded_old[0].content == "Old message":
        print("✅ Old format session correctly loaded.")
    else:
        print(f"❌ Old format load failed.")
    
    # Cleanup old test file
    os.remove(old_path)

if __name__ == "__main__":
    test_memory_service()
