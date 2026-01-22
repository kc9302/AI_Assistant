import sys
import json
from datetime import datetime
sys.path.append('backend')
from app.tools.calendar import _get_selected_calendars, _fetch_events_from_calendars
from app.core.google_auth import get_calendar_service

def fetch_and_save_events():
    service = get_calendar_service()
    if not service:
        print("Auth failed")
        return
    
    calendars = _get_selected_calendars(service)
    time_min = "2026-01-01T00:00:00Z"
    time_max = "2026-02-01T23:59:59Z"
    
    events = _fetch_events_from_calendars(service, calendars, time_min, time_max)
    
    output = []
    for ev in events:
        output.append({
            "start": ev["start"].get("dateTime") or ev["start"].get("date"),
            "summary": ev.get("summary", "(No Title)"),
            "calendar": ev.get("_calendarName", "Unknown"),
            "id": ev.get("id")
        })
    
    with open("temp_events.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(output)} events to temp_events.json")

if __name__ == "__main__":
    fetch_and_save_events()
