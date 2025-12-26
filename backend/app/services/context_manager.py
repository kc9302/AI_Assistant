import sqlite3
import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.getcwd(), "data", "context_v3.db")

class ContextManager:
    """
    Manages short-term working memory (Context) using SQLite.
    Stores structured entities like Created Events to support 'refer to previous' actions.
    """
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the database schema."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS recent_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        thread_id TEXT NOT NULL,
                        event_id TEXT NOT NULL,
                        calendar_id TEXT, 
                        summary TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to init Context DB: {e}")

    def add_event(self, thread_id: str, event_id: str, summary: str, calendar_id: str = "primary"):
        """Records a created event."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO recent_events (thread_id, event_id, summary, calendar_id)
                    VALUES (?, ?, ?, ?)
                """, (thread_id, event_id, summary, calendar_id))
                conn.commit()
            logger.debug(f"Saved event context: {summary} ({event_id}) on {calendar_id} for thread {thread_id}")
        except Exception as e:
            logger.error(f"Failed to add event context: {e}")

    def get_recent_events(self, thread_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieves the most recent events for a thread."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT event_id, summary, calendar_id, created_at 
                    FROM recent_events 
                    WHERE thread_id = ? 
                    ORDER BY id DESC 
                    LIMIT ?
                """, (thread_id, limit))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get recent events: {e}")
            return []

# Singleton instance
context_manager = ContextManager()
