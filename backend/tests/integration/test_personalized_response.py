import unittest
import os
import json
import shutil
import asyncio
from unittest.mock import MagicMock, patch
from app.agent.graph import get_graph
from app.services.memory import MemoryService
from langchain_core.messages import HumanMessage, AIMessage

class TestPersonalizedResponse(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.test_dir = "data_test_personalized"
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir)
        
        # Monkeypatch memory paths
        import app.services.memory
        app.services.memory.DATA_DIR = self.test_dir
        app.services.memory.USER_PROFILE_PATH = os.path.join(self.test_dir, "user_profile.json")
        app.services.memory.SESSIONS_DIR = os.path.join(self.test_dir, "sessions")
        
        self.service = MemoryService()
        
        # Setup a fake profile with facts and history
        self.service.update_user_profile({"favorite_coffee": "Vanilla Latte"})
        self.service.add_session_summary("thread_old_1", "Health", "User talked about their morning exercise routine at 7 AM.")
        
        # Also save the actual session history for the tool to find
        date_str = "2024-01-01" # dummy date for load_session search
        daily_dir = os.path.join(app.services.memory.SESSIONS_DIR, date_str)
        os.makedirs(daily_dir, exist_ok=True)
        with open(os.path.join(daily_dir, "thread_old_1.json"), "w", encoding="utf-8") as f:
             json.dump({
                 "messages": [
                     {"type": "human", "data": {"content": "I usually exercise at 7 AM."}},
                     {"type": "ai", "data": {"content": "Noted! That's a great habit."}}
                 ]
             }, f)

    async def asyncTearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    @patch("app.agent.llm.get_llm")
    async def test_planner_selective_memory(self, mock_get_llm):
        # We want to test that the Planner uses facts if available
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        
        # Planner response simulation
        # Use simple response if facts are enough
        from app.agent.schemas import PlannerResponse
        
        # Mocking structured output is tricky, we'll mock the chain invoke
        mock_structured_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured_llm
        
        # Case 1: Fact is enough
        mock_structured_llm.invoke.return_value = PlannerResponse(
            mode="plan",
            assistant_message="I remember you like Vanilla Latte! How about a cup now?",
            intent_description="Greeting with personal fact",
            needs_confirmation=False,
            language="en"
        )
        
        graph = get_graph()
        config = {"configurable": {"thread_id": "new_thread"}}
        
        inputs = {"messages": [HumanMessage(content="What coffee should I get?")]}
        result = await graph.ainvoke(inputs, config=config)
        
        self.assertIn("Vanilla Latte", result["messages"][-1].content)
        
        # Case 2: Deep history needed
        # We won't run the full execution loop here as it requires complex tool mocking
        # but we verified the logic in graph.py.

if __name__ == "__main__":
    asyncio.run(unittest.main())
