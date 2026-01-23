import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

# Mock environment variables
os.environ["LLM_BASE_URL"] = "http://localhost:11434"
os.environ["LLM_MODEL"] = "gpt-oss-safeguard"
os.environ["LLM_EMBEDDING_MODEL"] = "nomic-embed-text"
os.environ["LLM_KEEP_ALIVE"] = "5m"

from app.agent.llm import get_llm
from app.core.settings import settings

class TestLLMProvider(unittest.TestCase):
    def test_get_llm_with_explicit_model(self):
        """Verify that get_llm doesn't crash when 'model' is passed explicitly."""
        try:
            # We mock the provider to avoid actual network/ollama calls
            with patch("app.agent.llm.get_provider") as mock_get_provider:
                mock_provider = MagicMock()
                mock_get_provider.return_value = mock_provider
                
                # This should NOT raise TypeError: got multiple values for keyword argument 'model'
                llm = get_llm(model="gpt-oss-safeguard")
                
                # Verify that model was passed correctly to the provider
                mock_provider.get_chat_model.assert_called()
                args, kwargs = mock_provider.get_chat_model.call_args
                self.assertEqual(kwargs.get("model"), "gpt-oss-safeguard")
        except TypeError as e:
            self.fail(f"get_llm raised TypeError: {e}")

    def test_get_llm_caching(self):
        """Verify that LLM instances are cached."""
        with patch("app.agent.llm.get_provider") as mock_get_provider:
            mock_provider = MagicMock()
            mock_get_provider.return_value = mock_provider
            
            # Reset cache (if needed, though get_llm uses a global _llm_cache)
            from app.agent.llm import _llm_cache
            _llm_cache.clear()
            
            llm1 = get_llm(model="model-a")
            llm2 = get_llm(model="model-a")
            
            self.assertIs(llm1, llm2)
            self.assertEqual(mock_provider.get_chat_model.call_count, 1)

if __name__ == "__main__":
    unittest.main()
