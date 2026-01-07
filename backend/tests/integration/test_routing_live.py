import os
import pytest
from langchain_core.messages import HumanMessage

from app.agent.graph import router_node


def _state_with_user_message(text: str):
    return {"messages": [HumanMessage(content=text)]}


@pytest.mark.skipif(
    os.getenv("RUN_LIVE_TESTS") != "1",
    reason="Set RUN_LIVE_TESTS=1 to run live LLM routing tests.",
)
def test_router_travel_query_live():
    state = _state_with_user_message("osaka flight time")
    result = router_node(state)

    assert result["router_mode"] == "complex"
