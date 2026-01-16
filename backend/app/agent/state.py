from typing import TypedDict, Annotated, Optional
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from app.agent.schemas import PlannerResponse

class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    mode: str
    needs_confirmation: bool
    confirmation_id: str | None
    planner_response: Optional[PlannerResponse]
    intent_summary: Optional[str]
    router_mode: Optional[str]
    pending_calendar_events: Optional[list[dict]]  # New: for meeting summary confirmation
    last_meeting_summary: Optional[str]           # New: for context

