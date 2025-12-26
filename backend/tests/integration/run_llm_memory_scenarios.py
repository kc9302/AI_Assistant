import os
import sys
import time
import re
import json
from datetime import datetime, timedelta

# Add parent directory to sys.path to allow importing 'app'
current_dir = os.path.dirname(os.path.abspath(__file__))
tests_dir = os.path.dirname(current_dir)  # tests/
backend_dir = os.path.dirname(tests_dir)  # backend/
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from app.agent.graph import get_graph
from langgraph.graph import END
from langchain_core.messages import HumanMessage, AIMessage

# Import calendar tools directly for setup/verification if needed
from app.tools.calendar import list_calendars, _get_selected_calendars
from app.core.google_auth import get_calendar_service
# Import Context Manager for verification logic
from app.services.context_manager import context_manager

def verify_event_existence(calendar_id, date_str, target_title):
    """
    Directly checks Google Calendar API to see if an event with 'target_title' exists on 'date_str'.
    Returns True if found, False otherwise.
    """
    service = get_calendar_service()
    if not service:
        print("  [Verification Error] Could not get calendar service.")
        return False
        
    try:
        # date_str is expected to be 'YYYY-MM-DD'
        # Parse to datetime to get day range
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        time_min = dt.replace(hour=0, minute=0, second=0).isoformat() + "Z"
        time_max = dt.replace(hour=23, minute=59, second=59).isoformat() + "Z"
        
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        items = events_result.get('items', [])
        for item in items:
            if target_title in item.get('summary', ''):
                return True
        return False
    except Exception as e:
        print(f"  [Verification Error] API Call failed: {e}")
        return False

def get_test_calendars():
    """Finds calendars containing 'WS' or '나만보여'."""
    service = get_calendar_service()
    if not service:
        print("Failed to authenticate Google Calendar.")
        return []
    
    all_calendars = _get_selected_calendars(service)
    test_cals = []
    for cal in all_calendars:
        name = cal['summary']
        if 'WS' in name or '나만보여' in name:
            test_cals.append(cal)
    return test_cals

def run_agent(graph, user_input, thread_id):
    """Runs the agent with the given input and returns the final response messsage."""
    config = {"configurable": {"thread_id": thread_id}}
    
    print(f"\n[User]: {user_input}")
    
    # Initialize state with the user message
    initial_state = {"messages": [HumanMessage(content=user_input)]}
    
    # Run the graph
    final_output = None
    
    for event in graph.stream(initial_state, config=config, recursion_limit=20):
        for key, value in event.items():
            if key == "executor":
                messages = value.get("messages", [])
                if messages:
                    last_msg = messages[-1]
                    if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
                         for tc in last_msg.tool_calls:
                             print(f"  [Agent Action] Call Tool: {tc['name']} args={tc['args']}")
            
            elif key == "planner":
                 messages = value.get("messages", [])
                 if messages:
                     last_msg = messages[-1]
                     if isinstance(last_msg, AIMessage):
                         final_output = last_msg.content
                         print(f"  [Agent Response]: {final_output}")

    return final_output

def main():
    print("=== Starting LLM Memory Scenarios ===")
    
    test_calendars = get_test_calendars()
    if not test_calendars:
        print("No test calendars found ('WS' or '나만보여'). Exiting.")
        return
    
    print(f"Found {len(test_calendars)} test calendars: {[c['summary'] for c in test_calendars]}")
    
    graph = get_graph()
    
    for idx, cal in enumerate(test_calendars, start=1):
        cal_name = cal['summary']
        cal_id = cal['id']
        thread_id = f"test-mem-{idx}-{int(time.time())}"
        
        print(f"\n\n################################################")
        print(f"### Testing Calendar: {cal_name}")
        print(f"################################################")

        # ---------------------------------------------------------
        # Scenario 1: Retrieve Today's Events
        # ---------------------------------------------------------
        print(f"\n--- Scenario 1: Retrieve Today's Events on '{cal_name}' ---")
        prompt = f"'{cal_name}'(ID: {cal_id}) 캘린더의 오늘 일정 알려줘."
        run_agent(graph, prompt, thread_id)
        
        # ---------------------------------------------------------
        # Scenario 2: Create Event
        # ---------------------------------------------------------
        print(f"\n--- Scenario 2: Create Event on '{cal_name}' ---")
        unique_title = f"MEM_Test_Meeting_{int(time.time())}"
        start_time_str = "내일 오후 2시"
        
        prompt = f"'{cal_name}'(ID: {cal_id}) 캘린더에 {start_time_str}에 '{unique_title}' 일정 잡아줘."
        run_agent(graph, prompt, thread_id)
        
        # --- VERIFICATION Using Context Manager ---
        # Instead of Regex, we use context_manager to get the ID
        created_event_id = None
        
        # Allow a brief moment for async write if any (sqlite is sync here, but good practice)
        time.sleep(1) 
        
        recent_events = context_manager.get_recent_events(thread_id)
        # Look for our event in recent events
        for evt in recent_events:
            if evt['summary'] == unique_title:
                created_event_id = evt['event_id']
                print(f"  [Test Logic] Validated via ContextManager: Found ID {created_event_id}")
                break
        
        if not created_event_id:
             print("  [Test Logic] WARNING: Event not found in ContextManager!")

        # ---------------------------------------------------------
        # Scenario 3: Verify Creation (Retrieval)
        # ---------------------------------------------------------
        print(f"\n--- Scenario 3: Verify Creation on '{cal_name}' ---")
        # Direct API Verification
        is_found = verify_event_existence(cal_id, "2025-12-27", unique_title)
        
        if is_found:
            print(f"✅ PASS: API confirmed event '{unique_title}' exists.")
        else:
            print(f"❌ FAIL: API could not find event '{unique_title}'.")

        # ---------------------------------------------------------
        # Scenario 4: Delete Event
        # ---------------------------------------------------------
        print(f"\n--- Scenario 4: Delete Event on '{cal_name}' ---")
        
        if created_event_id:
            # If we found it in context, we use the ID explicitly to confirm the loop works
            prompt = f"'{cal_name}'(ID: {cal_id}) 캘린더에서 ID가 '{created_event_id}'인 일정을 취소해줘."
        else:
            # Fallback
            prompt = f"'{cal_name}'(ID: {cal_id}) 캘린더의 내일 '{unique_title}' 일정 취소해줘."
            
        run_agent(graph, prompt, thread_id)

        # ---------------------------------------------------------
        # Scenario 5: Verify Deletion
        # ---------------------------------------------------------
        print(f"\n--- Scenario 5: Verify Deletion on '{cal_name}' ---")
        # Direct API Verification
        # Give a small buffer for propagation if needed
        time.sleep(1)
        is_found = verify_event_existence(cal_id, "2025-12-27", unique_title)
        
        if not is_found:
             print(f"✅ PASS: API confirmed event '{unique_title}' is GONE.")
        else:
             print(f"❌ FAIL: API still found event '{unique_title}'.")

    print("\n=== All Scenarios Completed ===")

if __name__ == "__main__":
    # Redirect stdout to a file
    original_stdout = sys.stdout
    output_file_path = current_dir + '/test_llm_memory_output.txt' 
    
    with open(output_file_path, 'w', encoding='utf-8') as f:
        sys.stdout = f
        try:
            main()
        finally:
            sys.stdout = original_stdout
    
    print(f"Script output saved to {os.path.abspath(output_file_path)}")
