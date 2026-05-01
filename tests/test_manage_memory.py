"""
Tests for src/chanakya/services/manage_memory.py

Focus: add_memory, delete_memory, list_memories functions,
using a temporary SQLite database.
"""

import os
import sqlite3
import tempfile
import unittest


class TestManageMemory(unittest.TestCase):
    """Tests for the manage_memory module functions."""

    def setUp(self):
        """Create a temp DB with the memories table for each test."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()

        # Create the table
        conn = sqlite3.connect(self.db_path)
        conn.execute("CREATE TABLE IF NOT EXISTS memories (datetime TEXT, memory TEXT)")
        conn.commit()
        conn.close()

        # Import with patched DATABASE
        from src.chanakya.services import manage_memory

        self.manage_memory = manage_memory
        self._original_db = manage_memory.DATABASE
        manage_memory.DATABASE = self.db_path

    def tearDown(self):
        self.manage_memory.DATABASE = self._original_db
        os.unlink(self.db_path)

    def test_add_memory_inserts_record(self):
        """add_memory should insert a row into the memories table."""
        self.manage_memory.add_memory("Test memory content")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT memory FROM memories")
        rows = cursor.fetchall()
        conn.close()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "Test memory content")

    def test_add_memory_stores_datetime(self):
        """add_memory should store a formatted datetime string."""
        self.manage_memory.add_memory("A note")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT datetime FROM memories")
        rows = cursor.fetchall()
        conn.close()

        self.assertEqual(len(rows), 1)
        # Should contain "Time:" from the format string
        self.assertIn("Time:", rows[0][0])

    def test_add_multiple_memories(self):
        """Adding multiple memories should create multiple rows."""
        for i in range(5):
            self.manage_memory.add_memory(f"Memory #{i}")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT COUNT(*) FROM memories")
        count = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(count, 5)

    def test_delete_memory_removes_record(self):
        """delete_memory should remove the specified row."""
        self.manage_memory.add_memory("To delete")
        self.manage_memory.add_memory("To keep")

        # Get the rowid of the first memory
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT rowid FROM memories WHERE memory = ?", ("To delete",))
        rowid = cursor.fetchone()[0]
        conn.close()

        self.manage_memory.delete_memory(rowid)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT memory FROM memories")
        rows = cursor.fetchall()
        conn.close()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "To keep")

    def test_delete_nonexistent_memory(self):
        """Deleting a non-existent row should succeed without error."""
        self.manage_memory.delete_memory(99999)  # Should not raise

    def test_list_memories_empty(
        self,
    ):
        """list_memories on an empty table should print 'No memories found.'."""
        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            self.manage_memory.list_memories()

        output = f.getvalue()
        self.assertIn("No memories found", output)

    def test_list_memories_shows_data(self):
        """list_memories should print stored memories."""
        import io
        from contextlib import redirect_stdout

        self.manage_memory.add_memory("First memory")
        self.manage_memory.add_memory("Second memory")

        f = io.StringIO()
        with redirect_stdout(f):
            self.manage_memory.list_memories()

        output = f.getvalue()
        self.assertIn("First memory", output)
        self.assertIn("Second memory", output)
        self.assertIn("Memories:", output)


if __name__ == "__main__":
    unittest.main()
