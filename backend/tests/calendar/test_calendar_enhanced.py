import pytest
from unittest.mock import MagicMock, patch
from app.tools.calendar import (
    list_today_events, 
    list_events_on_date, 
    list_upcoming_events, 
    _format_events
)
from datetime import datetime, timedelta, timezone

@pytest.fixture
def mock_calendar_service():
    with patch("app.tools.calendar.get_calendar_service") as mock_get:
        mock_service = MagicMock()
        mock_get.return_value = mock_service
        yield mock_service

def test_format_events():
    events = [
        {
            "summary": "Meeting A",
            "start": {"dateTime": "2025-12-24T10:00:00+09:00"},
            "_calendarName": "Work",
            "location": "Room 101"
        },
        {
            "summary": "Lunch",
            "start": {"date": "2025-12-24"},
            "_calendarName": "Personal"
        }
    ]
    formatted = _format_events(events, "No events")
    assert "Meeting A" in formatted
    assert "Work" in formatted
    assert "Room 101" in formatted
    assert "Lunch" in formatted
    assert "Personal" in formatted

@patch("app.tools.calendar._get_selected_calendars")
def test_list_today_events(mock_get_cals, mock_calendar_service):
    mock_get_cals.return_value = [{"id": "primary", "summary": "Primary"}]
    
    # Mock events response
    mock_calendar_service.events().list().execute.return_value = {
        "items": [
            {
                "summary": "Today Event",
                "start": {"dateTime": "2025-12-24T14:00:00+09:00"}
            }
        ]
    }
    
    result = list_today_events.invoke({})
    assert "Today Event" in result
    
    # Verify timeMin/timeMax are sent (KST 00:00 to 23:59:59)
    args, kwargs = mock_calendar_service.events().list.call_args
    assert "timeMin" in kwargs
    assert "timeMax" in kwargs
    assert "00:00:00" in kwargs["timeMin"]

@patch("app.tools.calendar._get_selected_calendars")
def test_list_events_on_date(mock_get_cals, mock_calendar_service):
    mock_get_cals.return_value = [{"id": "primary", "summary": "Primary"}]
    mock_calendar_service.events().list().execute.return_value = {"items": []}
    
    result = list_events_on_date.invoke({"date": "2025-12-25"})
    assert "2025-12-25" in result
    assert "일정이 없습니다" in result
    
    args, kwargs = mock_calendar_service.events().list.call_args
    assert "2025-12-25T00:00:00" in kwargs["timeMin"]

@patch("app.tools.calendar._get_selected_calendars")
def test_list_upcoming_events(mock_get_cals, mock_calendar_service):
    mock_get_cals.return_value = [{"id": "primary", "summary": "Primary"}]
    mock_calendar_service.events().list().execute.return_value = {"items": []}
    
    result = list_upcoming_events.invoke({"max_results": 5})
    assert "다가올 일정이 없습니다" in result
    
    args, kwargs = mock_calendar_service.events().list.call_args
    assert kwargs["maxResults"] == 5
