from app.tools.calendar import _get_selected_calendars
from app.core.google_auth import get_calendar_service
from datetime import datetime, timedelta
import json

def search_thread_id(thread_id):
    service = get_calendar_service()
    if not service:
        print("Auth failed")
        return
    
    calendars = _get_selected_calendars(service)
    print(f"--- SEARCHING FOR ThreadID: {thread_id} ---")
    
    # Check last 1 hour
    time_min = (datetime.now() - timedelta(hours=1)).isoformat() + 'Z'
    query = f"[ThreadID: {thread_id}]"
    
    found_any = False
    for cal in calendars:
        print(f"Checking {cal['summary']} ({cal['id']})...")
        try:
            res = service.events().list(
                calendarId=cal['id'],
                q=query,
                timeMin=time_min,
                singleEvents=True
            ).execute()
            items = res.get('items', [])
            if items:
                found_any = True
                for item in items:
                    print(f"  [FOUND] Calendar: {cal['summary']} | Summary: {item.get('summary')} | Start: {item.get('start')}")
            else:
                print("  (Empty)")
        except Exception as e:
            print(f"  [ERROR] {e}")

    if not found_any:
        print("\nNo events found with that tag in any calendar.")

if __name__ == "__main__":
    search_thread_id("fa8fe756-a10b-4244-9da9-50ae6d68b5cd")
