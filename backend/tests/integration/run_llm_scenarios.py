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

# Import calendar tools directly for setup/verification if needed, 
# but the test mainly relies on the agent.
from app.tools.calendar import list_calendars, _get_selected_calendars
from app.core.google_auth import get_calendar_service

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
    # We use stream to capture the process, but for this test we just want the final result
    # However, printing intermediate steps helps debugging
    final_output = None
    
    # Recursion limit might need adjustment for complex chains
    for event in graph.stream(initial_state, config=config, recursion_limit=20):
        for key, value in event.items():
            if key == "executor":
                # Check for tool calls
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
    print("=== Starting LLM Calendar Scenarios ===")
    
    test_calendars = get_test_calendars()
    if not test_calendars:
        print("No test calendars found ('WS' or '나만보여'). Exiting.")
        return

    print(f"Found {len(test_calendars)} test calendars: {[c['summary'] for c in test_calendars]}")
    
    graph = get_graph()
    
    for idx, cal in enumerate(test_calendars, start=1):
        cal_name = cal['summary']
        cal_id = cal['id']
        thread_id = f"test-llm-{idx}-{int(time.time())}"
        
        print(f"\n\n################################################")
        print(f"### Testing Calendar: {cal_name}")
        print(f"################################################")

        # ---------------------------------------------------------
        # Scenario 1: Simple Retrieval (Today's events)
        # ---------------------------------------------------------
        print(f"\n--- Scenario 1: Retrieve Today's Events on '{cal_name}' ---")
        prompt = f"'{cal_name}'(ID: {cal_id}) 캘린더의 오늘 일정 알려줘."
        run_agent(graph, prompt, thread_id)
        
        # ---------------------------------------------------------
        # Scenario 2: Create Event
        # ---------------------------------------------------------
        print(f"\n--- Scenario 2: Create Event on '{cal_name}' ---")
        # Ensure unique title to avoid confusion
        unique_title = f"LLM_Test_Meeting_{int(time.time())}"
        start_time_str = "내일 오후 2시"
        
        prompt = f"'{cal_name}'(ID: {cal_id}) 캘린더에 {start_time_str}에 '{unique_title}' 일정 잡아줘."
        creation_response = run_agent(graph, prompt, thread_id)
        
        # Extract event ID from response if possible
        created_event_id = None
        if creation_response:
             # Look for pattern like "이벤트 ID는 XXXXX 입니다" or similar
             # Adjust regex based on Agent's actual output format in test_llm_scenarios_output.txt
             # "이벤트 ID는 4cr33dnjl1blbk0tp307igrs7c 입니다."
             match = re.search(r"이벤트 ID는\s+([a-zA-Z0-9]+)\s+입니다", creation_response)
             if match:
                 created_event_id = match.group(1)
                 print(f"  [Test Logic] Extracted Event ID: {created_event_id}")
             else:
                 print("  [Test Logic] Could not extract Event ID from response.")

        # ---------------------------------------------------------
        # Scenario 3: Verify Creation (Retrieval)
        # ---------------------------------------------------------
        print(f"\n--- Scenario 3: Verify Creation on '{cal_name}' ---")
        prompt = f"'{cal_name}'(ID: {cal_id}) 캘린더의 내일 일정 다시 보여줘."
        response = run_agent(graph, prompt, thread_id)
        
        if response and unique_title in response:
            print(f"✅ PASS: Found created event '{unique_title}' in response.")
        else:
            print(f"❌ FAIL: Could not find '{unique_title}' in response: {response}")

        # ---------------------------------------------------------
        # Scenario 4: Delete Event
        # ---------------------------------------------------------
        print(f"\n--- Scenario 4: Delete Event on '{cal_name}' ---")
        
        if created_event_id:
            prompt = f"'{cal_name}'(ID: {cal_id}) 캘린더에서 ID가 '{created_event_id}'인 일정을 취소해줘."
        else:
             # Fallback if ID wasn't extracted
            prompt = f"'{cal_name}'(ID: {cal_id}) 캘린더의 내일 '{unique_title}' 일정 취소해줘."
            
        run_agent(graph, prompt, thread_id)

        # ---------------------------------------------------------
        # Scenario 5: Verify Deletion
        # ---------------------------------------------------------
        print(f"\n--- Scenario 5: Verify Deletion on '{cal_name}' ---")
        prompt = f"'{cal_name}'(ID: {cal_id}) 캘린더의 내일 일정 확인해줘. '{unique_title}' 지워졌는지 확인."
        response = run_agent(graph, prompt, thread_id)
        
        if response and unique_title not in response:
             print(f"✅ PASS: Event '{unique_title}' is no longer listed.")
        elif response and unique_title in response:
             print(f"❌ FAIL: Event '{unique_title}' is still found.")
        else:
             print(f"⚠️ UNDETERMINED: Agent response was ambiguous: {response}")

    print("\n=== All Scenarios Completed ===")

if __name__ == "__main__":
    # Redirect stdout to a file
    original_stdout = sys.stdout
    # The script is run from `backend` dir, so the path is relative to it
    output_file_path = 'test_llm_scenarios_output.txt' 
    
    with open(output_file_path, 'w', encoding='utf-8') as f:
        sys.stdout = f
        try:
            main()
        finally:
            sys.stdout = original_stdout
    
    print(f"Script output saved to {os.path.abspath(output_file_path)}")
