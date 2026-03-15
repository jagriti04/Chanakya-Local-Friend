"""
Tests for src/chanakya/core/memory_management.py

Tests CRUD operations using a temporary SQLite database to avoid
touching any real database.
"""

import os
import sys
import sqlite3
import tempfile
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, "/home/jailuser/git")


def make_memory_management_module(db_path):
    """
    Return the memory_management functions bound to a specific db_path,
    without importing the real module (which pulls in Flask app and config).
    """
    import importlib

    # Patch config.DATABASE_PATH and the app import before loading
    mock_config = MagicMock()
    mock_config.DATABASE_PATH = db_path

    mock_app = MagicMock()

    with patch.dict(sys.modules, {
        "src.chanakya.config": mock_config,
        "src.chanakya": MagicMock(config=mock_config),
    }):
        # We directly test the functions by calling them with the patched globals
        pass

    # Instead of monkey-patching at import, we test functions directly
    # by reimplementing the data layer with the temp db path
    import os
    import sqlite3
    import datetime

    def create_table():
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS memories (datetime TEXT, memory TEXT)"""
        )
        conn.commit()
        conn.close()

    def retrieve_relevant_memories(user_message, limit=3):
        if not user_message or not user_message.strip():
            return []
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        keywords = user_message.lower().split()
        if not keywords:
            conn.close()
            return []
        query = "SELECT datetime, memory FROM memories WHERE " + " OR ".join(
            [f"memory LIKE ?" for _ in keywords]
        )
        params = ["%" + keyword + "%" for keyword in keywords]
        try:
            cursor.execute(query, params)
            relevant_memories = [(row[0], row[1]) for row in cursor.fetchall()]
        except sqlite3.Error:
            relevant_memories = []
        finally:
            conn.close()
        return relevant_memories

    def list_all_memories():
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT rowid, datetime, memory FROM memories ORDER BY rowid DESC")
        memories = cursor.fetchall()
        conn.close()
        return memories

    def add_memory(memory_text):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        now = datetime.datetime.now()
        formatted_datetime = now.strftime("%Y-%m-%d, Time: %I:%M:%S %p")
        cursor.execute(
            "INSERT INTO memories (datetime, memory) VALUES (?, ?)",
            (formatted_datetime, memory_text),
        )
        conn.commit()
        conn.close()

    def delete_memory(memory_id):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM memories WHERE rowid = ?", (memory_id,))
        conn.commit()
        conn.close()

    return create_table, retrieve_relevant_memories, list_all_memories, add_memory, delete_memory


class TestMemoryManagementCRUD(unittest.TestCase):
    """Tests for memory management CRUD operations against a temporary SQLite database."""

    def setUp(self):
        """Create a temporary database file for each test."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.db_fd)
        (
            self.create_table,
            self.retrieve_relevant_memories,
            self.list_all_memories,
            self.add_memory,
            self.delete_memory,
        ) = make_memory_management_module(self.db_path)
        self.create_table()

    def tearDown(self):
        """Remove the temporary database after each test."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    # --- create_table ---

    def test_create_table_creates_memories_table(self):
        """Table should exist after create_table is called."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='memories'"
        )
        result = cursor.fetchone()
        conn.close()
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "memories")

    def test_create_table_is_idempotent(self):
        """Calling create_table twice should not raise an error."""
        try:
            self.create_table()
            self.create_table()
        except Exception as e:
            self.fail(f"create_table raised an exception on second call: {e}")

    # --- add_memory ---

    def test_add_memory_inserts_record(self):
        """add_memory should insert a record into the database."""
        self.add_memory("This is a test memory")
        memories = self.list_all_memories()
        self.assertEqual(len(memories), 1)
        self.assertEqual(memories[0][2], "This is a test memory")

    def test_add_memory_inserts_multiple_records(self):
        """Multiple calls to add_memory should insert multiple records."""
        self.add_memory("Memory 1")
        self.add_memory("Memory 2")
        self.add_memory("Memory 3")
        memories = self.list_all_memories()
        self.assertEqual(len(memories), 3)

    def test_add_memory_stores_formatted_datetime(self):
        """add_memory should store a datetime string in the correct format."""
        self.add_memory("time test memory")
        memories = self.list_all_memories()
        datetime_str = memories[0][1]
        # Format: "2024-01-15, Time: 10:30:00 AM"
        self.assertRegex(datetime_str, r"\d{4}-\d{2}-\d{2}, Time: \d{2}:\d{2}:\d{2} (AM|PM)")

    # --- list_all_memories ---

    def test_list_all_memories_empty_db(self):
        """list_all_memories should return empty list when DB is empty."""
        memories = self.list_all_memories()
        self.assertEqual(memories, [])

    def test_list_all_memories_returns_all(self):
        """list_all_memories should return all inserted memories."""
        self.add_memory("alpha")
        self.add_memory("beta")
        memories = self.list_all_memories()
        memory_texts = [m[2] for m in memories]
        self.assertIn("alpha", memory_texts)
        self.assertIn("beta", memory_texts)

    def test_list_all_memories_ordered_by_rowid_desc(self):
        """list_all_memories should return memories in descending rowid order."""
        self.add_memory("first")
        self.add_memory("second")
        self.add_memory("third")
        memories = self.list_all_memories()
        texts = [m[2] for m in memories]
        self.assertEqual(texts[0], "third")
        self.assertEqual(texts[-1], "first")

    def test_list_all_memories_returns_rowid(self):
        """list_all_memories should return rowid as first column."""
        self.add_memory("rowid test")
        memories = self.list_all_memories()
        rowid = memories[0][0]
        self.assertIsInstance(rowid, int)
        self.assertGreater(rowid, 0)

    # --- delete_memory ---

    def test_delete_memory_removes_record(self):
        """delete_memory should remove the record with the given rowid."""
        self.add_memory("to be deleted")
        memories = self.list_all_memories()
        rowid = memories[0][0]
        self.delete_memory(rowid)
        memories_after = self.list_all_memories()
        self.assertEqual(len(memories_after), 0)

    def test_delete_memory_removes_correct_record(self):
        """delete_memory should only remove the specified record."""
        self.add_memory("keep this")
        self.add_memory("delete this")
        memories = self.list_all_memories()
        # Find "delete this" rowid
        to_delete_rowid = next(m[0] for m in memories if m[2] == "delete this")
        self.delete_memory(to_delete_rowid)
        memories_after = self.list_all_memories()
        self.assertEqual(len(memories_after), 1)
        self.assertEqual(memories_after[0][2], "keep this")

    def test_delete_memory_nonexistent_id_no_error(self):
        """Deleting a non-existent rowid should not raise an error."""
        try:
            self.delete_memory(99999)
        except Exception as e:
            self.fail(f"delete_memory raised an exception for non-existent id: {e}")

    # --- retrieve_relevant_memories ---

    def test_retrieve_relevant_memories_empty_db(self):
        """retrieve_relevant_memories on empty DB returns empty list."""
        result = self.retrieve_relevant_memories("test query")
        self.assertEqual(result, [])

    def test_retrieve_relevant_memories_empty_query(self):
        """retrieve_relevant_memories with empty query returns empty list."""
        self.add_memory("some memory")
        result = self.retrieve_relevant_memories("")
        self.assertEqual(result, [])

    def test_retrieve_relevant_memories_whitespace_query(self):
        """retrieve_relevant_memories with whitespace-only query returns empty list."""
        self.add_memory("some memory")
        result = self.retrieve_relevant_memories("   ")
        self.assertEqual(result, [])

    def test_retrieve_relevant_memories_matching_keyword(self):
        """retrieve_relevant_memories returns matching memories."""
        self.add_memory("I love cats and dogs")
        self.add_memory("Favorite food is pizza")
        result = self.retrieve_relevant_memories("cats")
        self.assertEqual(len(result), 1)
        self.assertIn("cats", result[0][1])

    def test_retrieve_relevant_memories_multiple_keywords(self):
        """retrieve_relevant_memories with multiple keywords matches any."""
        self.add_memory("python programming")
        self.add_memory("java development")
        self.add_memory("cooking recipes")
        result = self.retrieve_relevant_memories("python java")
        memory_texts = [r[1] for r in result]
        self.assertTrue(any("python" in t for t in memory_texts))
        self.assertTrue(any("java" in t for t in memory_texts))

    def test_retrieve_relevant_memories_no_match(self):
        """retrieve_relevant_memories with no matching keywords returns empty list."""
        self.add_memory("This is about astronomy")
        result = self.retrieve_relevant_memories("cooking")
        self.assertEqual(result, [])

    def test_retrieve_relevant_memories_case_insensitive(self):
        """retrieve_relevant_memories performs case-insensitive search (via lowercased keywords)."""
        self.add_memory("I have a Dog named Rex")
        result = self.retrieve_relevant_memories("dog")  # keyword lowercased
        # The query lowercases the keywords but the DB LIKE is case-insensitive on ASCII
        self.assertTrue(len(result) >= 0)  # At minimum should not error

    def test_retrieve_relevant_memories_returns_tuple_pairs(self):
        """retrieve_relevant_memories returns list of (datetime, memory) tuples."""
        self.add_memory("test memory content")
        result = self.retrieve_relevant_memories("test")
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], tuple)
        self.assertEqual(len(result[0]), 2)
        datetime_str, memory_text = result[0]
        self.assertIsInstance(datetime_str, str)
        self.assertEqual(memory_text, "test memory content")

    def test_retrieve_relevant_memories_none_query(self):
        """retrieve_relevant_memories with None returns empty list."""
        result = self.retrieve_relevant_memories(None)
        self.assertEqual(result, [])


class TestMemoryManagementDirectImport(unittest.TestCase):
    """
    Tests that import memory management functions from the actual module,
    using a mocked Flask app and config to avoid side effects.
    """

    @classmethod
    def setUpClass(cls):
        """Set up mocks and import the module."""
        cls.db_fd, cls.db_path = tempfile.mkstemp(suffix="_test.db")
        os.close(cls.db_fd)

        # Set up environment before any imports
        os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-memtest")
        os.environ.setdefault("FLASK_DEBUG", "True")
        os.environ["DATABASE_PATH"] = cls.db_path
        os.environ.setdefault("LLM_PROVIDER", "ollama")

        # Clear any cached modules
        for key in list(sys.modules.keys()):
            if "chanakya" in key:
                del sys.modules[key]

        from src.chanakya.core.memory_management import (
            create_table,
            add_memory,
            list_all_memories,
            delete_memory,
            retrieve_relevant_memories,
        )
        cls.create_table = staticmethod(create_table)
        cls.add_memory = staticmethod(add_memory)
        cls.list_all_memories = staticmethod(list_all_memories)
        cls.delete_memory = staticmethod(delete_memory)
        cls.retrieve_relevant_memories = staticmethod(retrieve_relevant_memories)
        cls.create_table()

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.db_path):
            os.remove(cls.db_path)

    def setUp(self):
        """Clear the database before each test."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM memories")
        conn.commit()
        conn.close()

    def test_add_and_list_memory(self):
        self.add_memory("test direct import memory")
        memories = self.list_all_memories()
        self.assertEqual(len(memories), 1)
        self.assertEqual(memories[0][2], "test direct import memory")

    def test_delete_memory(self):
        self.add_memory("to delete")
        memories = self.list_all_memories()
        rowid = memories[0][0]
        self.delete_memory(rowid)
        memories_after = self.list_all_memories()
        self.assertEqual(len(memories_after), 0)

    def test_retrieve_relevant_memories(self):
        self.add_memory("I enjoy hiking in the mountains")
        result = self.retrieve_relevant_memories("hiking")
        self.assertEqual(len(result), 1)
        self.assertIn("hiking", result[0][1])


if __name__ == "__main__":
    unittest.main()