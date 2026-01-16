from typing import TypedDict, Annotated, Optional
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from app.agent.schemas import PlannerResponse

import operator

def merge_optional_field(old, new):
    if new is not None:
        return new
    return old

class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    mode: str
    needs_confirmation: bool
    confirmation_id: str | None
    planner_response: Optional[PlannerResponse]
    intent_summary: Optional[str]
    router_mode: Optional[str]
    pending_calendar_events: Optional[list[dict]]
    last_meeting_summary: Optional[str]
    raw_meeting_notes: Optional[str] # New: Store raw text to avoid context loss

