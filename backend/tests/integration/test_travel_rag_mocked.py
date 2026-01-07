import asyncio
import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import HumanMessage

from app.agent.graph import get_graph
from app.agent.schemas import PlannerResponse, ExecutorResponse, ProposedAction


class DummyResponse:
    def __init__(self, content: str):
        self.content = content


class DummyLLM:
    def __init__(self, content: str):
        self._content = content

    def invoke(self, prompt):
        return DummyResponse(self._content)


@patch("app.tools.travel_tools.travel_knowledge_service.search")
@patch(
    "app.agent.graph.memory_service.get_user_profile",
    return_value={"facts": {}, "history": []},
)
@patch("app.agent.graph.get_llm")
def test_travel_rag_flow_mocked(mock_get_llm, _mock_profile, mock_search):
    router_llm = DummyLLM('{"mode":"answer","reasoning":"chat"}')

    planner_llm_first = MagicMock()
    planner_structured_first = MagicMock()
    planner_structured_first.invoke.return_value = PlannerResponse(
        mode="execute",
        assistant_message="Checking travel info.",
        intent_description="Check flight time to Osaka",
        needs_confirmation=False,
        language="en",
    )
    planner_llm_first.with_structured_output.return_value = planner_structured_first

    executor_llm = MagicMock()
    executor_structured = MagicMock()
    executor_structured.invoke.return_value = ExecutorResponse(
        proposed_action=ProposedAction(
            tool="search_travel_info",
            args={"query": "osaka flight time"},
        )
    )
    executor_llm.with_structured_output.return_value = executor_structured

    planner_llm_second = MagicMock()
    planner_structured_second = MagicMock()
    planner_structured_second.invoke.return_value = PlannerResponse(
        mode="plan",
        assistant_message="Flight KE721 departs at 11:00.",
        intent_description="Summarize tool results",
        needs_confirmation=False,
        language="en",
    )
    planner_llm_second.with_structured_output.return_value = planner_structured_second

    mock_get_llm.side_effect = [
        router_llm,
        planner_llm_first,
        executor_llm,
        planner_llm_second,
    ]

    mock_search.return_value = [
        {
            "content": "Flight KE721 departs at 11:00.",
            "metadata": {"source": "logistics.md"},
            "score": 0.1,
        }
    ]

    graph = get_graph()
    config = {"configurable": {"thread_id": "mock_travel"}}
    inputs = {"messages": [HumanMessage(content="osaka flight time")]}
    result = asyncio.run(graph.ainvoke(inputs, config=config))

    assert "KE721" in result["messages"][-1].content
    mock_search.assert_called_once()
