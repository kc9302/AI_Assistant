from app.tools.calendar import create_event
from datetime import datetime, timedelta, timezone

def main():
    kst = timezone(timedelta(hours=9))
    start_dt = datetime.now(kst) + timedelta(days=1, hours=5) # Tomorrow 2PM-ish
    end_dt = start_dt + timedelta(hours=1)
    
    result = create_event.invoke({
        "summary": "[Visual Test] Direct Verification",
        "start_time": start_dt.isoformat(),
        "end_time": end_dt.isoformat(),
        "calendar_id": "primary"
    })
    print(result)

if __name__ == "__main__":
    main()
