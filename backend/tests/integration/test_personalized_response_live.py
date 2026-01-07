import os
import asyncio
import pytest
from unittest.mock import patch
from langchain_core.messages import HumanMessage

from app.agent.graph import get_graph


@pytest.mark.skipif(
    os.getenv("RUN_LIVE_TESTS") != "1",
    reason="Set RUN_LIVE_TESTS=1 to run live LLM tests.",
)
@patch(
    "app.agent.graph.memory_service.get_user_profile",
    return_value={"facts": {"favorite_coffee": "Vanilla Latte"}, "history": []},
)
def test_personalized_response_live(_mock_profile):
    graph = get_graph()
    config = {"configurable": {"thread_id": "live_personalized"}}
    inputs = {"messages": [HumanMessage(content="What coffee should I get?")]}
    result = asyncio.run(graph.ainvoke(inputs, config=config))

    content = result["messages"][-1].content
    assert isinstance(content, str)
    assert content.strip()
    assert "Error in planning" not in content
