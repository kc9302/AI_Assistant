import unittest
import os
import json
import shutil
from app.services.memory import MemoryService

class TestMemoryService(unittest.TestCase):
    def setUp(self):
        # Use a temporary directory for testing
        self.test_dir = "data_test_memory"
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir)
        
        # Monkeypatch constants in memory module
        import app.services.memory
        self.original_data_dir = app.services.memory.DATA_DIR
        self.original_profile_path = app.services.memory.USER_PROFILE_PATH
        
        app.services.memory.DATA_DIR = self.test_dir
        app.services.memory.SESSIONS_DIR = os.path.join(self.test_dir, "sessions")
        app.services.memory.USER_PROFILE_PATH = os.path.join(self.test_dir, "user_profile.json")
        
        self.service = MemoryService()

    def tearDown(self):
        # Restore original constants if needed (though they are pointers)
        import app.services.memory
        app.services.memory.DATA_DIR = self.original_data_dir
        app.services.memory.USER_PROFILE_PATH = self.original_profile_path
        
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_profile_initialization(self):
        profile = self.service.get_user_profile()
        self.assertIn("facts", profile)
        self.assertIn("history", profile)
        self.assertEqual(profile["history"], [])

    def test_update_facts(self):
        self.service.update_user_profile({"name": "Alice"})
        profile = self.service.get_user_profile()
        self.assertEqual(profile["facts"]["name"], "Alice")
        
        self.service.update_user_profile({"hobby": "Tennis"})
        profile = self.service.get_user_profile()
        self.assertEqual(profile["facts"]["name"], "Alice")
        self.assertEqual(profile["facts"]["hobby"], "Tennis")

    def test_add_session_summary(self):
        self.service.add_session_summary("thread_1", "Work", "Discussed project X")
        profile = self.service.get_user_profile()
        self.assertEqual(len(profile["history"]), 1)
        self.assertEqual(profile["history"][0]["thread_id"], "thread_1")
        self.assertEqual(profile["history"][0]["category"], "Work")
        
        # Update existing
        self.service.add_session_summary("thread_1", "Work", "Discussed project X and Y")
        profile = self.service.get_user_profile()
        self.assertEqual(len(profile["history"]), 1)
        self.assertEqual(profile["history"][0]["summary"], "Discussed project X and Y")

    def test_history_limit(self):
        for i in range(25):
            self.service.add_session_summary(f"thread_{i}", "General", f"Summary {i}")
        
        profile = self.service.get_user_profile()
        self.assertEqual(len(profile["history"]), 20)
        self.assertEqual(profile["history"][-1]["thread_id"], "thread_24")
        self.assertEqual(profile["history"][0]["thread_id"], "thread_5")

if __name__ == "__main__":
    unittest.main()
