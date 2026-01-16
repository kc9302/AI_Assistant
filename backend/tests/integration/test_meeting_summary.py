import os
import sys

# Add backend to sys.path with high priority
backend_path = os.path.join(os.getcwd(), "backend")
sys.path.insert(0, backend_path)

# Set dummy environment variables before any imports that trigger Settings initialization
os.environ["LLM_BASE_URL"] = "http://localhost:11434"
os.environ["GOOGLE_API_KEY"] = "dummy"

import unittest
from unittest.mock import MagicMock, patch
import logging
import shutil
import json

# Enable logging to see what's happening
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock the provider and other services to avoid connection/RAG errors during startup
mock_provider = MagicMock()
mock_provider.name = "mock"

# Mock embeddings to return dummy vectors if called
mock_embeddings = MagicMock()
mock_embeddings.embed_documents.side_effect = lambda docs: [[0.1]*768 for _ in docs]
mock_embeddings.embed_query.return_value = [0.1]*768

with patch("app.llm.providers.get_provider", return_value=mock_provider), \
     patch("app.agent.llm.get_embeddings", return_value=mock_embeddings), \
     patch("app.agent.llm.init_models", return_value=None), \
     patch("app.services.travel.FAISS", MagicMock()), \
     patch("app.services.travel.travel_knowledge_service", MagicMock()):
    
    import asyncio
    from app.agent.graph import get_graph
    from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
    from app.agent.schemas import PlannerResponse, ExecutorResponse, ProposedAction
    
    import asyncio
    from app.agent.graph import get_graph
    from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
    from app.agent.schemas import PlannerResponse, ExecutorResponse, ProposedAction

class TestMeetingSummaryIntegration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.test_dir = "data_test_meeting"
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir)
        
        import app.services.memory
        app.services.memory.DATA_DIR = self.test_dir
        app.services.memory.USER_PROFILE_PATH = os.path.join(self.test_dir, "user_profile.json")
        os.makedirs(os.path.dirname(app.services.memory.USER_PROFILE_PATH), exist_ok=True)
        with open(app.services.memory.USER_PROFILE_PATH, "w", encoding="utf-8") as f:
            json.dump({"facts": {}, "history": []}, f)

    async def asyncTearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    @patch("app.agent.graph.get_llm")
    async def test_meeting_summary_flow(self, mock_get_llm):
        """Test the flow from meeting notes to confirmation request."""
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        
        # 1. Router Mock
        mock_llm.invoke.side_effect = [
            # Router Response
            MagicMock(content='{"mode": "complex", "reasoning": "Meeting summary is complex"}'),
            # Planner Response (Execute summarize_meeting_notes)
            MagicMock(content='{"mode": "execute", "assistant_message": "요약 중...", "intent_description": "Summarize meeting notes", "language": "ko", "needs_confirmation": false}'),
            # Executor Response
            MagicMock(content='{"proposed_action": {"tool": "summarize_meeting_notes", "args": {"meeting_notes": "test note"}}}'),
            # Second Planner Response (After tool result) - this is the one that sets needs_confirmation
            # Note: The actual graph logic uses json.loads(last_tool_msg.content), so we need to mock tool output too.
        ]
        
        # We need to mock the tool execution result for the planner to pick up
        # In a real graph run, the tool node executes the tool.
        # Here we'll simulate the graph's internal calls.
        
        graph = get_graph()
        config = {"configurable": {"thread_id": "meeting_test"}}
        
        # Since we want to test the full flow, we might need a more complex mock or a partial integration test.
        # For now, let's test if the planner correctly identifies the tool result.
        
        from app.agent.state import AgentState
        from langchain_core.messages import ToolMessage
        
        tool_result = json.dumps({
            "summary": "핵심 내용",
            "action_items": [
                {
                    "task": "미팅",
                    "is_calendar_event": True,
                    "suggested_calendar_title": "테스트 미팅",
                    "suggested_start_time": "2026-01-20T10:00:00"
                }
            ]
        })
        
        state = AgentState(
            messages=[
                HumanMessage(content="이 회의록 요약하고 일정 등록해줘: '내일 오전 10시 미팅'"),
                AIMessage(content="", tool_calls=[{"name": "summarize_meeting_notes", "args": {"meeting_notes": "..."}, "id": "1"}]),
                ToolMessage(content=tool_result, tool_call_id="1", name="summarize_meeting_notes")
            ],
            mode="plan",
            needs_confirmation=False,
            confirmation_id=None,
            planner_response=None,
            intent_summary=None,
            router_mode="complex",
            pending_calendar_events=None,
            last_meeting_summary=None
        )
        
        # Invoke planner node directly to verify logic
        from app.agent.graph import planner
        result = planner(state)
        
        self.assertTrue(result["needs_confirmation"])
        self.assertIn("등록하시겠습니까?", result["messages"][0].content)
        self.assertEqual(len(result["pending_calendar_events"]), 1)
        self.assertEqual(result["pending_calendar_events"][0]["suggested_calendar_title"], "테스트 미팅")

    @patch("app.agent.graph.get_llm")
    async def test_meeting_confirmation_yes(self, mock_get_llm):
        """Test the flow from 'Yes' confirmation to multiple tool calls."""
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        
        # Router & Planner Mocks for the 'Yes' turn
        # Reset the mock to ensure fresh side_effects
        mock_llm.invoke = MagicMock() # Changed from self.mock_provider.invoke to mock_llm.invoke
        mock_llm.invoke.side_effect = [ # Changed from self.mock_provider.invoke to mock_llm.invoke
            # Executor is the ONLY node that calls LLM here 
            # (Router and Planner skip LLM during confirmation flow)
            MagicMock(content='{"proposed_actions": [{"tool": "create_event", "args": {"summary": "테스트 미팅", "start_time": "2026-01-20T10:00:00"}}]}')
        ]
        
        from app.agent.state import AgentState
        state = AgentState(
            messages=[
                HumanMessage(content="응 등록해줘")
            ],
            mode="execute",
            needs_confirmation=False,
            intent_summary="Confirm and register all pending_calendar_events",
            pending_calendar_events=[{"suggested_calendar_title": "테스트 미팅", "is_calendar_event": True}],
            # other fields...
        )
        
        # Invoke executor node directly
        from app.agent.graph import executor_node
        # Note: executor_node takes (state, config)
        config = {"configurable": {"thread_id": "test"}}
        result = executor_node(state, config)
        
        tool_calls = result["messages"][0].tool_calls
        self.assertEqual(len(tool_calls), 1)
        self.assertEqual(tool_calls[0]["name"], "create_event")
        self.assertEqual(tool_calls[0]["args"]["summary"], "테스트 미팅")
        self.assertIsNone(result.get("pending_calendar_events")) # Should be cleared

if __name__ == "__main__":
    unittest.main()
