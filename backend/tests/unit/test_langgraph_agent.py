import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from app.agent.graph import chatbot, route_tools, tools
from app.agent.state import AgentState

def test_route_tools_with_tool_call():
    """
    Tests that the router correctly identifies a tool call and routes to the 'tools' node.
    """
    ai_message_with_tool_call = AIMessage(
        content="",
        tool_calls=[{"name": "list_events", "args": {"calendar_id": "primary"}, "id": "1"}]
    )
    state = AgentState(messages=[ai_message_with_tool_call])
    
    result = route_tools(state)
    assert result == "tools"

def test_route_tools_without_tool_call():
    """
    Tests that the router correctly identifies a message without a tool call and routes to END.
    """
    ai_message_without_tool_call = AIMessage(content="Hello there!")
    state = AgentState(messages=[ai_message_without_tool_call])
    
    result = route_tools(state)
    assert result == "__end__"

@patch('app.agent.graph.get_llm')
def test_chatbot_generates_tool_call(mock_get_llm):
    """
    Tests that the chatbot node can generate a tool call.
    """
    # Arrange: Mock the LLM and its response
    mock_llm = MagicMock()
    mock_llm_with_tools = MagicMock()
    
    # This is the crucial part: we are simulating the LLM's response
    # to be an AIMessage that contains a tool call.
    mock_response = AIMessage(
        content="",
        tool_calls=[{"name": "list_events", "args": {"calendar_id": "primary"}, "id": "tool_123"}]
    )
    mock_llm_with_tools.invoke.return_value = mock_response
    mock_llm.bind_tools.return_value = mock_llm_with_tools
    mock_get_llm.return_value = mock_llm
    
    # Act: Call the chatbot node
    initial_state = AgentState(messages=[HumanMessage(content="What are my upcoming events?")])
    result_state = chatbot(initial_state)
    
    # Assert: Check that the response contains the tool call
    last_message = result_state["messages"][-1]
    assert isinstance(last_message, AIMessage)
    assert hasattr(last_message, "tool_calls")
    assert len(last_message.tool_calls) == 1
    assert last_message.tool_calls[0]["name"] == "list_events"
