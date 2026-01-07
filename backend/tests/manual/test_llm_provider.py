import pytest
from dotenv import load_dotenv, find_dotenv
from app.agent.llm import get_llm

load_dotenv(find_dotenv("../.env")) # Load environment variables from .env file

# Removed @pytest.mark.skip to enable the test
def test_llm_provider_connection():
    """
    Tests the connection to the configured LLM provider and a simple invocation.
    """
    try:
        llm = get_llm()
        response = llm.invoke("Why is the sky blue?")

        assert response is not None
        assert isinstance(response.content, str)
        assert len(response.content) > 0

    except Exception as e:
        pytest.fail(f"LLM provider connection test failed: {e}")
