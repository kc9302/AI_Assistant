import os
import sys
import re
from datetime import datetime, timedelta
import json # Added import
import time

# Add parent directory to sys.path to allow importing 'app'
current_dir = os.path.dirname(os.path.abspath(__file__))
tests_dir = os.path.dirname(current_dir)  # tests/
backend_dir = os.path.dirname(tests_dir)  # backend/
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from app.tools.calendar import (
    list_calendars,
    list_events_on_date,
    create_event,
    delete_event,
    get_event,
)

"""
Refactored Integration Test for Calendar Tools

This script directly calls the calendar tool functions to verify their behavior
against the Google Calendar API. It checks the actual return values from the API
wrappers, logs them, and determines a Pass/Fail status.
"""

def main():
    print("=== Starting Refactored Integration Scenarios ===")
    thread_id = f"test-run-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    # --------------------------------
    # [0] 캘린더 전체 목록 조회
    # --------------------------------
    print("\n[0] 사용 가능한 캘린더 목록 조회")
    calendars_str = list_calendars.invoke({})
    print(f"API Result:\n{calendars_str}")

    test_calendars = []
    for line in calendars_str.split('\n'):
        match = re.search(r'- (.*) \(ID: (.*)\)', line)
        if match:
            name = match.group(1).strip()
            cal_id = match.group(2).strip()
            # For this test, only use calendars that are likely test calendars
            if 'WS' in name or '나만보여' in name:
                test_calendars.append({'name': name, 'id': cal_id})

    if not test_calendars:
        print("\nCould not find any test calendars ('WS' or '나만보여'). Exiting.")
        return
        
    print(f"\nFound {len(test_calendars)} test calendars: {[cal['name'] for cal in test_calendars]}")

    # --------------------------------
    # [1~] 캘린더별 일정 조회 -> 등록 -> 삭제
    # --------------------------------
    for idx, cal in enumerate(test_calendars, start=1):
        calendar_name = cal["name"]
        calendar_id = cal["id"]
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        
        print(f"\n--- Scenario for Calendar: '{calendar_name}' (ID: {calendar_id}) ---")

        # [1-idx] 오늘 일정 조회
        print(f"\n[1-{idx}] '{calendar_name}' 캘린더에서 오늘 일정 조회")
        today_str = datetime.now().strftime("%Y-%m-%d")
        events_today_str = list_events_on_date.invoke({"date": today_str, "calendar_id": calendar_id})
        print(f"API Result Log: {events_today_str}")
        
        # Check: Pass if there are 0 or more events. Fail only on error.
        if "오류" in events_today_str or "Error" in events_today_str:
            print("Check Result: Fail - API call returned an error.")
        else:
            num_events = len([line for line in events_today_str.split('\n') if line.strip().startswith('-')])
            print(f"Check Result: Pass - Found {num_events} events.")

        # [2-idx] 내일 일정 등록
        unique_title = f"[IT-{idx}] 통합테스트 일정 {timestamp}"
        print(f"\n[2-{idx}] '{calendar_name}' 캘린더에 일정 등록")
        tomorrow = datetime.now() + timedelta(days=1)
        start_time_iso = tomorrow.replace(hour=14 + idx, minute=0, second=0, microsecond=0).isoformat()
        
        end_time_iso = (tomorrow.replace(hour=14 + idx, minute=0, second=0, microsecond=0) + timedelta(hours=1)).isoformat()
        creation_result = create_event.invoke({
            "summary": unique_title,
            "start_time": start_time_iso,
            "end_time": end_time_iso,
            "calendar_id": calendar_id,
            "description": '통합 테스트용 일정입니다',
            "location": f'테스트실 {idx}호'
        })
        print(f"API Result Log: {creation_result}")

        parsed_creation_result = {}
        event_id = None
        try:
            parsed_creation_result = json.loads(creation_result)
            event_id = parsed_creation_result.get('eventId')
        except json.JSONDecodeError:
            print(f"Check Result: Fail - Could not parse creation_result as JSON: {creation_result}")
            continue # Skip to next calendar if parsing fails

        if not event_id:
            print(f"Check Result: Fail - 'eventId' not found in creation_result: {creation_result}")
            continue # Skip to next calendar if event_id cannot be extracted

        # Check: Pass if status is success.
        if parsed_creation_result.get('status') == "success":
            print("Check Result: Pass - Event creation successful.")
        else:
            print(f"Check Result: Fail - {creation_result}")
            continue # Skip to next calendar if creation fails

        # [2.5-idx] 단건 조회 검증
        print(f"\n[2.5-{idx}] 생성된 일정(ID: {event_id}) 단건 조회 검증")
        retrieved_event_json = get_event.invoke({"event_id": event_id, "calendar_id": calendar_id})
        
        parsed_retrieved_event = {}
        try:
            parsed_retrieved_event = json.loads(retrieved_event_json)
        except json.JSONDecodeError:
            print(f"Check Result: Fail - Could not parse retrieved event as JSON: {retrieved_event_json}")
            continue # Skip to next calendar

        if parsed_retrieved_event.get('status') == "success" and parsed_retrieved_event.get('summary') == unique_title:
            print(f"Check Result: Pass - Retrieved event details match for '{unique_title}'.")
        else:
            print(f"Check Result: Fail - Retrieved event details do not match or an error occurred. Retrieved: {retrieved_event_json}")
            continue # Skip to next calendar if verification fails

        # [3-idx] 등록된 일정(내일) 재조회
        print(f"\n[3-{idx}] '{calendar_name}' 캘린더에서 등록된 일정(내일) 재조회")
        tomorrow_str = tomorrow.strftime("%Y-%m-%d")
        events_tomorrow_str = list_events_on_date.invoke({"date": tomorrow_str, "calendar_id": calendar_id})
        print(f"API Result Log: {events_tomorrow_str}")

        # Check: Pass if the unique title is found in the event list.
        if unique_title in events_tomorrow_str:
            print(f"Check Result: Pass - Found the created event '{unique_title}'.")
        else:
            print(f"Check Result: Fail - Could not find the created event.")

        # [4-idx] 일정 삭제
        print(f"\n[4-{idx}] '{calendar_name}' 캘린더에서 일정 삭제")
        deletion_result = delete_event.invoke({
            "event_id": event_id,
            "calendar_id": calendar_id
        })
        print(f"API Result Log: {deletion_result}")

        # Check: Pass if success message is returned.
        if "✓ 일정" in deletion_result and "삭제되었습니다" in deletion_result:
            print("Check Result: Pass - Event deletion successful.")
        else:
            print(f"Check Result: Fail - {deletion_result}")

        # [5-idx] 삭제 확인(내일 재조회)
        print(f"\n[5-{idx}] '{calendar_name}' 캘린더에서 삭제 확인(내일 재조회)")
        events_after_delete_str = list_events_on_date.invoke({"date": tomorrow_str, "calendar_id": calendar_id})
        print(f"API Result Log: {events_after_delete_str}")
        
        # Check: Pass if the unique title is NOT found.
        if unique_title not in events_after_delete_str:
            print(f"Check Result: Pass - Event '{unique_title}' is confirmed deleted.")
        else:
            print(f"Check Result: Fail - Event '{unique_title}' was not deleted.")        
    print("\n=== All Scenarios Completed ===")


if __name__ == "__main__":
    # Redirect stdout to a file
    original_stdout = sys.stdout
    # The script is run from `backend` dir, so the path is relative to it
    output_file_path = current_dir + '/test_calendar_output.txt' 
    
    with open(output_file_path, 'w', encoding='utf-8') as f:
        sys.stdout = f
        try:
            main()
        finally:
            sys.stdout = original_stdout
    
    print(f"Script output saved to {os.path.abspath(output_file_path)}")
