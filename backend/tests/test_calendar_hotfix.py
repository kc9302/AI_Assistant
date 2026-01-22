import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone
from app.tools.calendar import create_event

def test_create_event_duplicate_check_timezone_handling():
    # Scenario: LLM provides naive datetime string
    naive_start = "2026-01-18T14:00:00"
    
    with patch("app.tools.calendar.get_calendar_service") as mock_get_service:
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        
        # Mock events().list().execute().get() to return empty list (no duplicates)
        # Correct path: service.events() returns a mock. That mock has .list method.
        # So we configure mock_service.events.return_value.list
        mock_events = mock_service.events.return_value
        mock_list = mock_events.list
        mock_list.return_value.execute.return_value.get.return_value = []
        
        # Mock events().insert() to succeed
        # Correct path: mock_events.insert
        mock_insert = mock_events.insert
        mock_insert.return_value.execute.return_value = {"id": "new_event_id", "htmlLink": "http://link"}
        
        # Call create_event (accessing the original function via .func to bypass Tool wrapper overhead in unit test)
        # Note: Depending on LangChain version, it might be .func or we should use invoke. 
        # But .func is the standard way to test logic in isolation.
        result = create_event.func(
            summary="Test Event",
            start_time=naive_start,
            calendar_id="primary"
        )
        
        # Verification: Check call args for events().list
        kwargs = mock_list.call_args[1]
        time_min = kwargs.get("timeMin")
        time_max = kwargs.get("timeMax")
        
        print(f"Debug: timeMin={time_min}, timeMax={time_max}")
        
        # Assert that timeMin/timeMax have timezone information (either +09:00 or Z)
        # We explicitly added timezone(timedelta(hours=9)) for naive inputs
        # So it should be ISO format with offset or Z.
        assert "+" in time_min or "Z" in time_min
        assert "+" in time_max or "Z" in time_max
        
        # Also ensure it didn't crash
        # The tool now returns JSON string
        import json
        res_json = json.loads(result)
        assert res_json["status"] == "success"

if __name__ == "__main__":
    pytest.main([__file__])
