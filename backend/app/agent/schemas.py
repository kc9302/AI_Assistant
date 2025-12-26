from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict, Any

class ProposedAction(BaseModel):
    """Represents a tool call proposed by the agent."""
    tool: str = Field(description="The name of the tool to use (e.g., 'create_event', 'list_events')")
    args: Dict[str, Any] = Field(
        default_factory=dict, 
        description="The arguments for the tool. For create_event, use 'summary', 'start_time', and optionally 'end_time', 'calendar_id', 'description', 'location'. For delete_event, use 'event_id' or a combination of 'summary' and 'date'."
    )

class RouterResponse(BaseModel):
    """The structured response from the local router model."""
    mode: Literal["simple", "complex", "answer"] = Field(
        description="'simple' for quick actions, 'complex' for multi-step or reasoning, 'answer' for direct chat"
    )
    reasoning: str = Field(description="Brief reason for choosing this mode")

class PlannerResponse(BaseModel):
    """The structured response from the large Planner model."""
    mode: Literal["plan", "execute"] = Field(
        description="'plan' to ask the user a question, 'execute' to perform a tool action"
    )
    assistant_message: str = Field(
        description="The message to show to the user",
    )
    intent_description: Optional[str] = Field(
        default=None,
        description="Detailed description of the tool action to take. Required if mode is 'execute'."
    )
    language: Literal["ko", "en"] = Field(
        description="The language to use for assistant_message. 'ko' for Korean, 'en' for English."
    )
    needs_confirmation: bool = Field(default=False)

class ExecutorResponse(BaseModel):
    """The structured response from the specialized Executor model."""
    proposed_action: ProposedAction = Field(description="The final tool call to execute")
