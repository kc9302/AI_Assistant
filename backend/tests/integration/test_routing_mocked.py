import pytest
from unittest.mock import patch
from langchain_core.messages import HumanMessage

from app.agent.graph import is_travel_query, router_node


class DummyResponse:
    def __init__(self, content: str):
        self.content = content


class DummyLLM:
    def __init__(self, content: str):
        self._content = content

    def invoke(self, prompt):
        return DummyResponse(self._content)


def _state_with_user_message(text: str):
    return {"messages": [HumanMessage(content=text)]}


@patch("app.agent.graph.memory_service.get_user_profile", return_value={})
def test_is_travel_query_basic(_mock_profile):
    assert is_travel_query("osaka flight time")
    assert is_travel_query("KIX gate info")
    assert not is_travel_query("hello there")


@patch("app.agent.graph.memory_service.get_user_profile", return_value={})
@patch("app.agent.graph.get_llm")
def test_router_overrides_answer_for_travel(mock_get_llm, _mock_profile):
    mock_get_llm.return_value = DummyLLM('{"mode":"answer","reasoning":"chat"}')

    state = _state_with_user_message("osaka flight time")
    result = router_node(state)

    assert result["router_mode"] == "complex"


@patch("app.agent.graph.memory_service.get_user_profile", return_value={})
@patch("app.agent.graph.get_llm")
def test_router_keeps_answer_for_non_travel(mock_get_llm, _mock_profile):
    mock_get_llm.return_value = DummyLLM('{"mode":"answer","reasoning":"chat"}')

    state = _state_with_user_message("hello there")
    result = router_node(state)

    assert result["router_mode"] == "answer"
