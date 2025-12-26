from app.core.google_auth import get_calendar_service
import json

def test_calendar():
    print("Testing Google Calendar Service...")
    service = get_calendar_service()
    if not service:
        print("FAILURE: Could not get calendar service (Authentication failed).")
        return
    
    try:
        print("Listing calendars...")
        calendar_list = service.calendarList().list().execute()
        items = calendar_list.get("items", [])
        if not items:
            print("No calendars found.")
        else:
            print(f"Found {len(items)} calendars:")
            for item in items:
                print(f"- {item['summary']} (ID: {item['id']})")
                
        print("\nSUCCESS: Calendar service is working.")
    except Exception as e:
        print(f"FAILURE: Error calling Calendar API: {e}")

if __name__ == "__main__":
    test_calendar()
