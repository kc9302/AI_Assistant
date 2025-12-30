import logging
from typing import List, Optional
from app.services.memory import memory_service
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

@tool
def retrieve_past_session(thread_id: str) -> str:
    """
    Retrieves the full conversation history for a specific past session.
    Use this ONLY when the session summary in 'Past Conversations' seems highly relevant 
    but lacks the specific detail needed to answer the user's current request.
    """
    try:
        messages = memory_service.load_session(thread_id)
        if not messages:
            return f"No history found for session ID: {thread_id}"
        
        history_text = f"--- Full History for Session {thread_id} ---\n"
        for m in messages:
            role = "User" if m.type == "human" else "Assistant"
            history_text += f"{role}: {m.content}\n"
        return history_text
    except Exception as e:
        logger.error(f"Failed to retrieve past session {thread_id}: {e}")
        return f"Error retrieving session: {e}"

memory_tools = [retrieve_past_session]
