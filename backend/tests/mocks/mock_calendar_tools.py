from langchain_core.tools import tool

@tool
def mock_get_calendars():
    """Mock implementation of get_calendars."""
    return [{"id": "primary", "summary": "Primary Calendar"}]

@tool
def mock_list_events(calendar_id: str, time_min: str = None, time_max: str = None, max_results: int = 10):
    """Mock implementation of list_events."""
    return [{"summary": "Mock Event 1"}, {"summary": "Mock Event 2"}]

@tool
def mock_create_event(calendar_id: str, summary: str, start_time: str, end_time: str):
    """Mock implementation of create_event."""
    return {"status": "confirmed", "summary": summary}
