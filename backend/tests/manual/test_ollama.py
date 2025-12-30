import pytest
import os
from dotenv import load_dotenv, find_dotenv
from app.agent.llm import get_llm
from app.core.settings import settings # Import settings
import ollama # Keep ollama import for now, might be needed for specific mocks later

load_dotenv(find_dotenv("../.env")) # Load environment variables from .env file

# Removed @pytest.mark.skip to enable the test
def test_ollama_connection():
    """
    Tests the connection to the Ollama server and a simple invocation.
    """
    try:
        llm = get_llm()
        response = llm.invoke("Why is the sky blue?")
        
        assert response is not None
        assert isinstance(response.content, str)
        assert len(response.content) > 0
        
    except Exception as e:
        pytest.fail(f"Ollama connection test failed: {e}")