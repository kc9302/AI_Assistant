import asyncio
import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import HumanMessage

from app.agent.graph import get_graph
from app.agent.schemas import PlannerResponse


class DummyResponse:
    def __init__(self, content: str):
        self.content = content


class DummyLLM:
    def __init__(self, content: str):
        self._content = content

    def invoke(self, prompt):
        return DummyResponse(self._content)


@patch(
    "app.agent.graph.memory_service.get_user_profile",
    return_value={"facts": {"favorite_coffee": "Vanilla Latte"}, "history": []},
)
@patch("app.agent.graph.get_llm")
def test_personalized_response_mocked(mock_get_llm, _mock_profile):
    router_llm = DummyLLM('{"mode":"answer","reasoning":"chat"}')

    planner_llm = MagicMock()
    structured = MagicMock()
    structured.invoke.return_value = PlannerResponse(
        mode="plan",
        assistant_message="I remember you like Vanilla Latte.",
        intent_description="Answer from facts",
        needs_confirmation=False,
        language="en",
    )
    planner_llm.with_structured_output.return_value = structured

    mock_get_llm.side_effect = [router_llm, planner_llm]

    graph = get_graph()
    config = {"configurable": {"thread_id": "mock_personalized"}}
    inputs = {"messages": [HumanMessage(content="What coffee should I get?")]}
    result = asyncio.run(graph.ainvoke(inputs, config=config))

    assert "Vanilla Latte" in result["messages"][-1].content
