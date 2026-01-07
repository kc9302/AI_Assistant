import os
import asyncio
from pathlib import Path
import pytest
from unittest.mock import patch
from langchain_core.messages import HumanMessage

from app.agent.graph import get_graph


def _travel_index_exists() -> bool:
    root = Path(__file__).resolve().parents[3]
    return (root / "backend" / "data" / "travel_index").exists()


@pytest.mark.skipif(
    os.getenv("RUN_LIVE_TESTS") != "1",
    reason="Set RUN_LIVE_TESTS=1 to run live LLM tests.",
)
@pytest.mark.skipif(
    not _travel_index_exists(),
    reason="Travel index missing; build it before running live travel tests.",
)
@patch(
    "app.agent.graph.memory_service.get_user_profile",
    return_value={"facts": {}, "history": []},
)
def test_travel_rag_live(_mock_profile):
    graph = get_graph()
    config = {"configurable": {"thread_id": "live_travel"}}
    inputs = {"messages": [HumanMessage(content="osaka flight time")]}
    result = asyncio.run(graph.ainvoke(inputs, config=config))

    content = result["messages"][-1].content
    assert isinstance(content, str)
    assert content.strip()
    assert "Error in planning" not in content
