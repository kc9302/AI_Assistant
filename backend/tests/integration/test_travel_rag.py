import json
import pytest
from unittest.mock import patch, MagicMock
from app.agent.graph import get_graph
from app.agent.state import AgentState
from app.services.memory import memory_service
import os

@pytest.fixture
def agent():
    return get_graph()

@pytest.fixture(autouse=True)
def mock_settings():
    with patch("app.core.settings.settings") as mock:
        mock.OLLAMA_HOST = "http://192.168.0.100:11434"
        mock.OLLAMA_MODEL_PLANNER = "gemma3:27b"
        yield mock

def test_travel_rag_response(agent):
    """
    Verifies that the agent can retrieve travel info from RAG and answer correctly.
    """
    thread_id = "test_travel_thread"
    
    # Mocking memory to avoid side effects
    with patch("app.services.memory.MemoryService.get_user_profile") as mock_profile:
        mock_profile.return_value = {"facts": {}, "history": []}
        
        # Test case 1: Question about flight
        inputs = {
            "messages": [("user", "오사카 가는 비행기 시간 언제야?")],
            "thread_id": thread_id
        }
        
        print("\n--- Testing Travel RAG: Flight Time ---")
        response = agent.invoke(inputs, config={"configurable": {"thread_id": thread_id}})
        
        final_msg = response["messages"][-1].content
        # Use sys.stdout.buffer for binary printing or just avoid printing special chars directly
        # For simplicity in test, let's just log it safely
        try:
            print(f"DEBUG - Agent Response (Flight): {final_msg.encode('utf-8', errors='replace').decode('utf-8')}")
        except:
            pass
            
        # Assertions - Agent might use "11시" instead of "11:00" and Korean names
        assert any(keyword in final_msg for keyword in ["11:00", "11시", "KE721", "KE722"])
        assert any(keyword in final_msg for keyword in ["KIX", "간사이", "공항", "오사카"])

        # Test case 2: Question about hotel
        inputs = {
            "messages": [("user", "우리 호텔 이름이랑 주소, 전화번호 다 알려줘")],
            "thread_id": thread_id
        }
        
        print("\n--- Testing Travel RAG: Hotel Info ---")
        response = agent.invoke(inputs, config={"configurable": {"thread_id": thread_id}})
        
        final_msg = response["messages"][-1].content
        try:
            print(f"Agent Response (Hotel): {final_msg.encode('utf-8', errors='replace').decode('utf-8')}")
        except:
            pass
        
        assert any(keyword in final_msg for keyword in ["Nikko", "닛코", "호텔", "Hotel"])
        assert any(keyword in final_msg for keyword in ["Shinsaibashi", "신사이바시", "1-3-3", "06-6244-1111", "6-6244-1111", "+81"])

if __name__ == "__main__":
    # For manual run, needs pytest or a mock-up of the agent fixture
    import sys
    # Force UTF-8 for output
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    pytest.main([__file__] + sys.argv[1:])
