import os
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from langchain_core.messages import BaseMessage, message_to_dict, messages_from_dict

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.getcwd(), "data")
SESSIONS_DIR = os.path.join(DATA_DIR, "sessions")
USER_PROFILE_PATH = os.path.join(DATA_DIR, "user_profile.json")

class MemoryService:
    """Handles high-speed session IO and profile management."""
    
    def __init__(self):
        os.makedirs(SESSIONS_DIR, exist_ok=True)
        if not os.path.exists(USER_PROFILE_PATH):
            with open(USER_PROFILE_PATH, "w", encoding="utf-8") as f:
                json.dump({"patterns": [], "facts": {}}, f)

    def save_session(self, thread_id: str, messages: List[BaseMessage]):
        """Saves current session messages to JSON in date-based directory."""
        date_str = datetime.now().strftime("%Y-%m-%d")
        daily_dir = os.path.join(SESSIONS_DIR, date_str)
        os.makedirs(daily_dir, exist_ok=True)
        
        path = os.path.join(daily_dir, f"{thread_id}.json")
        try:
            data = [message_to_dict(m) for m in messages]
            with open(path, "w", encoding="utf-8") as f:
                json.dump({
                    "updated_at": datetime.now().isoformat(),
                    "messages": data
                }, f, ensure_ascii=False, indent=2)
            logger.debug(f"Session {thread_id} saved to {date_str}.")
        except Exception as e:
            logger.error(f"Failed to save session {thread_id}: {e}")

    def load_session(self, thread_id: str, date_str: Optional[str] = None) -> List[BaseMessage]:
        """
        Loads session messages from JSON.
        If date_str is provided, look specifically in that folder.
        Otherwise, search folders (descending) or fallback to old flat format.
        """
        # 1. Search in specific date folder if provided
        if date_str:
            path = os.path.join(SESSIONS_DIR, date_str, f"{thread_id}.json")
            if os.path.exists(path):
                return self._read_json(path)

        # 2. Search in all date folders (new format)
        if os.path.exists(SESSIONS_DIR):
            dates = sorted([d for d in os.listdir(SESSIONS_DIR) if os.path.isdir(os.path.join(SESSIONS_DIR, d))], reverse=True)
            for d in dates:
                path = os.path.join(SESSIONS_DIR, d, f"{thread_id}.json")
                if os.path.exists(path):
                    return self._read_json(path)

        # 3. Fallback to old flat format: {thread_id}_{date}.json
        # Check files in SESSIONS_DIR directly
        for f in os.listdir(SESSIONS_DIR):
            if f.startswith(thread_id) and f.endswith(".json"):
                 path = os.path.join(SESSIONS_DIR, f)
                 if os.path.isfile(path):
                     return self._read_json(path)

        return []

    def _read_json(self, path: str) -> List[BaseMessage]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return messages_from_dict(data.get("messages", []))
        except Exception as e:
            logger.error(f"Failed to load session from {path}: {e}")
            return []

    def list_sessions_by_date(self, date_str: str) -> List[str]:
        """Returns list of session IDs for a specific date."""
        daily_dir = os.path.join(SESSIONS_DIR, date_str)
        if not os.path.exists(daily_dir):
            return []
        
        return [f.replace(".json", "") for f in os.listdir(daily_dir) if f.endswith(".json")]

    def list_all_dates(self) -> List[str]:
        """Returns all dates that have session subdirectories."""
        if not os.path.exists(SESSIONS_DIR):
            return []
        return sorted([d for d in os.listdir(SESSIONS_DIR) if os.path.isdir(os.path.join(SESSIONS_DIR, d))], reverse=True)

    def get_user_profile(self) -> Dict[str, Any]:
        """Returns the long-term user profile."""
        try:
            with open(USER_PROFILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load user profile: {e}")
            return {"patterns": [], "facts": {}}

    def update_user_profile(self, new_facts: Dict[str, Any]):
        """Updates the persistent user profile."""
        profile = self.get_user_profile()
        profile["facts"].update(new_facts)
        try:
            with open(USER_PROFILE_PATH, "w", encoding="utf-8") as f:
                json.dump(profile, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to update user profile: {e}")

class MemoryAnalyzer:
    """Extracts patterns and facts from conversation history."""
    
    def __init__(self, memory_service: MemoryService):
        self.service = memory_service

    async def analyze_and_update(self, messages: List[BaseMessage]):
        """
        Background task to analyze conversation for long-term facts.
        In a real app, this would use an LLM. Here, we'll simulate logic.
        """
        # Example logic: if user mentions "I like morning meetings", extract it.
        # This is where we'd call a small LLM to 'distill' the session.
        logger.info("MemoryAnalyzer: Running background analysis...")
        # (Distillation logic would go here)
        pass

memory_service = MemoryService()
memory_analyzer = MemoryAnalyzer(memory_service)
