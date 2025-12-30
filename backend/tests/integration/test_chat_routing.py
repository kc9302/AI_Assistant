import unittest
import os
import json
import shutil
import asyncio
from unittest.mock import MagicMock, patch
from app.agent.graph import get_graph
from langchain_core.messages import HumanMessage

class TestChatRouting(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.test_dir = "data_test_routing"
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir)
        
        import app.services.memory
        app.services.memory.DATA_DIR = self.test_dir
        app.services.memory.USER_PROFILE_PATH = os.path.join(self.test_dir, "user_profile.json")

    async def asyncTearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    @patch("app.agent.llm.get_llm")
    async def test_general_chat_no_tool_call(self, mock_get_llm):
        """Verify that general greetings or questions don't trigger tool calls unnecessarily."""
        # Force MemoryService to refresh its paths by re-initializing it or manually setting them
        import app.services.memory
        app.services.memory.USER_PROFILE_PATH = os.path.join(self.test_dir, "user_profile.json")
        os.makedirs(os.path.dirname(app.services.memory.USER_PROFILE_PATH), exist_ok=True)
        with open(app.services.memory.USER_PROFILE_PATH, "w", encoding="utf-8") as f:
            json.dump({"facts": {}, "history": []}, f)
            
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        
        from app.agent.schemas import PlannerResponse
        mock_structured_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured_llm
        
        mock_structured_llm.invoke.return_value = PlannerResponse(
            mode="plan",
            assistant_message="Hello! I'm your AI assistant.",
            intent_description="General greeting",
            needs_confirmation=False,
            language="en"
        )
        
        graph = get_graph()
        config = {"configurable": {"thread_id": "routing_test"}}
        
        inputs = {"messages": [HumanMessage(content="Hi there!")]}
        result = await graph.ainvoke(inputs, config=config)
        
        self.assertEqual(result["mode"], "plan")
        self.assertIn("Hello", result["messages"][-1].content)

    @patch("app.agent.llm.get_llm")
    async def test_memory_question_no_tool_call(self, mock_get_llm):
        """Verify that questions about user facts are answered directly."""
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        
        # Ensure profile exists with data
        import app.services.memory
        app.services.memory.USER_PROFILE_PATH = os.path.join(self.test_dir, "user_profile_2.json")
        os.makedirs(os.path.dirname(app.services.memory.USER_PROFILE_PATH), exist_ok=True)
        with open(app.services.memory.USER_PROFILE_PATH, "w", encoding="utf-8") as f:
            json.dump({"facts": {"hobby": "Hiking"}, "history": []}, f)
        
        mock_structured_llm.invoke.return_value = PlannerResponse(
            mode="plan",
            assistant_message="I remember you enjoy hiking!",
            intent_description="Answering from memory",
            needs_confirmation=False,
            language="en"
        )
        
        graph = get_graph()
        config = {"configurable": {"thread_id": "routing_test_2"}}
        
        inputs = {"messages": [HumanMessage(content="What do I like to do for fun?")]}
        result = await graph.ainvoke(inputs, config=config)
        
        self.assertEqual(result["mode"], "plan")
        self.assertIn("hiking", result["messages"][-1].content.lower())

if __name__ == "__main__":
    asyncio.run(unittest.main())
