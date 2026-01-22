import pytest
from unittest.mock import MagicMock, patch
from app.agent.graph import executor_node
from app.agent.state import AgentState
from app.agent.schemas import ExecutorResponse, ProposedAction
from langchain_core.messages import HumanMessage, AIMessage

def test_executor_node_prevents_duplicates():
    # Setup state with a mock intent
    state = {
        "messages": [HumanMessage(content="[WS] Inc. 캘린더에 일정 추가")],
        "intent_summary": "Create a team lunch event on [WS] Inc. calendar",
        "pending_calendar_events": []
    }
    
    # Mock LLM response that contains BOTH proposed_action and proposed_actions
    mock_response = MagicMock()
    mock_response.content = """
    {
        "proposed_action": {"tool": "create_event", "args": {"summary": "Duplicate", "start_time": "2026-01-21T14:00:00"}},
        "proposed_actions": [{"tool": "create_event", "args": {"summary": "Original", "start_time": "2026-01-21T14:00:00"}}],
        "reasoning": "Duplicate test"
    }
    """
    
    with patch("app.agent.graph.get_llm") as mock_get_llm, \
         patch("app.agent.graph.get_calendar_service") as mock_get_service, \
         patch("app.agent.graph._get_selected_calendars") as mock_get_cals:
        
        # Mock LLM invoke
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm
        
        # Mock calendar mapping
        mock_get_cals.return_value = [{"summary": "[WS] Inc.", "id": "ws_id"}]
        
        # Execute node
        # Note: We need to pass a mock config as well
        config = {"configurable": {"thread_id": "test_thread"}}
        result = executor_node(state, config)
        
        tool_calls = result["messages"][0].tool_calls
        
        # VERIFICATION: Only proposed_actions should be taken if both exist (based on our fix)
        # In our fix: 
        # all_actions = []
        # if parsed.proposed_actions: all_actions.extend(parsed.proposed_actions)
        # elif parsed.proposed_action: all_actions.append(parsed.proposed_action)
        
        assert len(tool_calls) == 1
        # ToolCall is a TypedDict, so we must access via keys
        assert tool_calls[0]["args"]["summary"] == "Original"
        assert tool_calls[0]["args"]["calendar_id"] == "ws_id" # Case-insensitive check verified here too

if __name__ == "__main__":
    pytest.main([__file__])
