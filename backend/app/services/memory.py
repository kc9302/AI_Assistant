import os
import json
import logging
import asyncio
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
                json.dump({
                    "user": {"name": "Unknown", "calendars": []},
                    "patterns": [],
                    "facts": {},
                    "history": []
                }, f, ensure_ascii=False, indent=2)

    def _normalize_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(profile, dict):
            profile = {}
        profile.setdefault("user", {"name": "Unknown", "calendars": []})
        profile.setdefault("patterns", [])
        profile.setdefault("facts", {})
        profile.setdefault("history", [])
        return profile

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
                profile = json.load(f)
            profile = self._normalize_profile(profile)
            return profile
        except Exception as e:
            logger.error(f"Failed to load user profile: {e}")
            return {"patterns": [], "facts": {}, "history": []}

    def update_user_profile(self, new_facts: Dict[str, Any]):
        """Updates the persistent user profile facts."""
        profile = self._normalize_profile(self.get_user_profile())
        profile["facts"].update(new_facts)
        self._save_profile(profile)

    def update_user_info(self, new_info: Dict[str, Any]):
        """Updates the persistent user information (name, calendars, etc.)."""
        profile = self._normalize_profile(self.get_user_profile())
        profile["user"].update(new_info)
        self._save_profile(profile)

    def add_user_pattern(self, pattern: str):
        """Adds a new pattern entry if it does not already exist."""
        if not pattern:
            return
        profile = self._normalize_profile(self.get_user_profile())
        if pattern not in profile["patterns"]:
            profile["patterns"].append(pattern)
            self._save_profile(profile)

    def add_session_summary(self, thread_id: str, category: str, summary: str):
        """Adds or updates a session summary in the user profile history."""
        profile = self._normalize_profile(self.get_user_profile())
        
        # Check if thread already exists in history to update it
        existing = next((item for item in profile["history"] if item["thread_id"] == thread_id), None)
        if existing:
            existing.update({
                "category": category,
                "summary": summary,
                "updated_at": datetime.now().isoformat()
            })
        else:
            profile["history"].append({
                "thread_id": thread_id,
                "category": category,
                "summary": summary,
                "updated_at": datetime.now().isoformat()
            })
        
        # Keep only last 20 summaries to save tokens later
        profile["history"] = profile["history"][-20:]
        self._save_profile(profile)

    def _save_profile(self, profile: Dict[str, Any]):
        try:
            with open(USER_PROFILE_PATH, "w", encoding="utf-8") as f:
                json.dump(profile, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save user profile: {e}")

class MemoryAnalyzer:
    """Extracts patterns and facts from conversation history."""
    
    def __init__(self, memory_service: MemoryService):
        self.service = memory_service

    async def analyze_and_update(self, messages: List[BaseMessage]):
        """
        Background task to analyze conversation for long-term facts.
        """
        logger.info("MemoryAnalyzer: Running background analysis...")
        
        # 1. Prepare history text
        history = ""
        for m in messages:
            role = "User" if isinstance(m, HumanMessage) else "Assistant"
            history += f"{role}: {m.content}\n"

        # 2. Extract facts using LLM
        from app.agent.llm import get_llm
        from app.core.settings import settings
        from app.core.utils import extract_json
        from langchain_core.messages import ToolMessage
        
        llm = get_llm(model=settings.LLM_MODEL_PLANNER)
        
        prompt = f"""You are a Fact Extractor & Conversation Summarizer. 
Analyze the following conversation and extract:
1. NEW, IMPORTANT facts or preferences about the user.
2. A category for this conversation (e.g., 'Work', 'Health', 'Personal', 'General').
3. A concise one-line summary of the conversation.

Current conversation:
{history}

Respond ONLY in JSON format with the following keys:
- 'facts': dictionary of key-value strings.
- 'category': string.
- 'summary': string.

Example: {{
  "facts": {{"favorite_sport": "tennis"}},
  "category": "Interests",
  "summary": "User shared their love for tennis and morning routines."
}}
If no new facts found, 'facts' should be {{}}.
"""
        try:
            # Run LLM in thread to avoid blocking
            response = await asyncio.to_thread(llm.invoke, prompt)
            json_str = extract_json(response.content)
            data = json.loads(json_str)
            
            new_facts = data.get("facts", {})
            category = data.get("category", "General")
            summary = data.get("summary", "Conversation snapshot")

            # Only keep travel facts when grounded in travel knowledge (logistics.md).
            allow_travel = any(
                isinstance(m, ToolMessage)
                and m.name == "search_travel_info"
                and "logistics.md" in str(m.content)
                for m in messages
            )
            if new_facts and not allow_travel:
                def is_travel_key(key: str) -> bool:
                    k = key.lower()
                    return (
                        k.startswith("travel_")
                        or any(tok in k for tok in ["travel", "flight", "hotel", "accommodation", "check_in", "check-in", "itinerary", "airline", "ticket", "boarding", "gate", "osaka"])
                    )
                new_facts = {k: v for k, v in new_facts.items() if not is_travel_key(k)}
            
            # Use specific thread_id if available from message context or pass as arg
            # For background tasks, we usually have a way to know which thread it was.
            # We'll assume the caller of analyze_and_update can provide it or we find it.
            # For now, let's add an optional thread_id to the method. (Refactoring for this below)
            # Find the thread_id from the last AI message if possible
            thread_id = "unknown"
            for m in reversed(messages):
                if hasattr(m, "additional_kwargs") and "thread_id" in m.additional_kwargs:
                    thread_id = m.additional_kwargs["thread_id"]
                    break
            
            if new_facts:
                logger.info(f"MemoryAnalyzer: Discovered new facts: {new_facts}")
                self.service.update_user_profile(new_facts)
            
            # Save session-specific metadata
            self.service.add_session_summary(thread_id, category, summary)
            logger.info(f"MemoryAnalyzer: Session [{thread_id}] summarized: {category} - {summary}")
            
        except Exception as e:
            logger.error(f"MemoryAnalyzer: Analysis failed: {e}")

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, message_to_dict, messages_from_dict

memory_service = MemoryService()
memory_analyzer = MemoryAnalyzer(memory_service)
