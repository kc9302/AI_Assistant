import unittest
import os
import json
import shutil
import asyncio
from unittest.mock import MagicMock, patch
from app.services.memory import MemoryAnalyzer, MemoryService
from langchain_core.messages import HumanMessage, AIMessage

class TestMemoryDistillation(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.test_dir = "data_test_distillation"
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir)
        
        # Monkeypatch memory paths
        import app.services.memory
        app.services.memory.DATA_DIR = self.test_dir
        app.services.memory.USER_PROFILE_PATH = os.path.join(self.test_dir, "user_profile.json")
        
        self.service = MemoryService()
        self.analyzer = MemoryAnalyzer(self.service)

    async def asyncTearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    @patch("app.agent.llm.get_llm")
    async def test_full_distillation(self, mock_get_llm):
        # Setup mock LLM
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        
        # Mock response from LLM
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "facts": {"name": "Bob", "specialty": "AI Engineering"},
            "category": "Career",
            "summary": "User introduced himself and his work in AI."
        })
        mock_llm.invoke.return_value = mock_response
        
        messages = [
            HumanMessage(content="Hi, my name is Bob."),
            AIMessage(content="Hello Bob! How can I help you?"),
            HumanMessage(content="I work as an AI Engineer and I love building agentic systems.", additional_kwargs={"thread_id": "test_thread_123"})
        ]
        
        # We need to ensure thread_id extraction works. 
        # In my code, I look for additional_kwargs['thread_id'] in reversed messages.
        
        await self.analyzer.analyze_and_update(messages)
        
        profile = self.service.get_user_profile()
        
        # Check facts
        self.assertEqual(profile["facts"]["name"], "Bob")
        self.assertEqual(profile["facts"]["specialty"], "AI Engineering")
        
        # Check history
        self.assertEqual(len(profile["history"]), 1)
        self.assertEqual(profile["history"][0]["thread_id"], "test_thread_123")
        self.assertEqual(profile["history"][0]["category"], "Career")
        self.assertEqual(profile["history"][0]["summary"], "User introduced himself and his work in AI.")

if __name__ == "__main__":
    asyncio.run(unittest.main())
