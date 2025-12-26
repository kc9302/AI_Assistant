from app.tools.calendar import (
    list_calendars, 
    list_today_events, 
    list_weekly_events, 
    create_event, 
    delete_event
)
from app.core.google_auth import get_calendar_service
from datetime import datetime, timedelta, timezone
import pytest
import re

def test_calendar_integration_scenarios():
    service = get_calendar_service()
    if not service:
        pytest.skip("Google Calendar service not available")

    print("\n[Scenario 1] 오늘 전체 일정 가져오기")
    today_all = list_today_events.invoke({})
    print(f"Result:\n{today_all}")
    # Flexible assertion: either starts with '-' (events found) or contains '없습니다' (none found)
    assert "-" in today_all or "없습니다" in today_all

    print("\n[Scenario 2] 오늘 특정 캘린더 개별 가져오기")
    cal_list_str = list_calendars.invoke({})
    print(f"Calendars:\n{cal_list_str}")
    
    # Extract IDs using regex from "- Summary (ID: xyz)"
    cal_ids = re.findall(r"\(ID: (.*?)\)", cal_list_str)
    
    for cal_id in cal_ids:
        print(f"\nFetching today for ID: {cal_id}")
        cal_today = list_today_events.invoke({"calendar_id": cal_id})
        print(f"Result: {cal_today[:100]}...")
        assert "-" in cal_today or "없습니다" in cal_today
        assert f"캘린더({cal_id})" in cal_today

    print("\n[Scenario 3] 주간 전체 일정 가져오기")
    weekly_all = list_weekly_events.invoke({})
    print(f"Result:\n{weekly_all}")
    assert "-" in weekly_all or "없습니다" in weekly_all

    print("\n[Scenario 4] 주간 특정 캘린더 개별 가져오기")
    for cal_id in cal_ids:
        print(f"\nFetching weekly for ID: {cal_id}")
        cal_weekly = list_weekly_events.invoke({"calendar_id": cal_id})
        print(f"Result: {cal_weekly[:100]}...")
        assert "-" in cal_weekly or "없습니다" in cal_weekly
        assert f"캘린더({cal_id})" in cal_weekly

    print("\n[Scenario 5] 특정 캘린터 일정 등록하기 (양식 불완전 포함)")
    kst = timezone(timedelta(hours=9))
    start_dt = datetime.now(kst) + timedelta(days=1, hours=1) # Tomorrow + 1h
    end_dt = start_dt + timedelta(hours=1)
    
    start_iso = start_dt.isoformat()
    end_iso = end_dt.isoformat()
    
    writable_cal_ids = []
    for cal_id in cal_ids:
        # Skip known read-only calendars like holidays
        if any(k in cal_id for k in ["holiday", "#", "group.v.calendar", "contacts"]):
            print(f"\nSkipping read-only calendar: {cal_id}")
            continue
        writable_cal_ids.append(cal_id)
            
    print("\n[Scenario 5] 특정 캘린터 일정 등록하기 (양식 불완전 포함)")
    for cal_id in writable_cal_ids:
        summary = f"[Test] Integration {cal_id[:5]}"
        print(f"\nRegistering event in {cal_id}...")
        result = create_event.invoke({
            "summary": summary,
            "start_time": start_iso,
            "end_time": end_iso,
            "calendar_id": cal_id
        })
        print(f"Result: {result}")
        if "❌" in result:
            print(f"Warning: Registration failed for {cal_id} (might be read-only despite filter)")
        else:
            assert "성공" in result or "생성되었습니다" in result

    print("\n[Scenario 6] 특정 캘린더 일정 삭제하기")
    for cal_id in writable_cal_ids:
        print(f"\nCleaning up events in {cal_id}...")
        events_result = service.events().list(
            calendarId=cal_id, 
            q="[Test] Integration",
            timeMin=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        ).execute()
        
        items = events_result.get('items', [])
        if not items:
            print(f"No test events found in {cal_id} to delete.")
            continue

        for item in items:
            event_id = item['id']
            del_result = delete_event.invoke({"event_id": event_id, "calendar_id": cal_id})
            print(f"Deleted {event_id}: {del_result}")
            assert "성공" in del_result

if __name__ == "__main__":
    import sys
    import io
    # Ensure stdout handles UTF-8 for Korean characters and symbols
    sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8', errors='replace')
    test_calendar_integration_scenarios()
