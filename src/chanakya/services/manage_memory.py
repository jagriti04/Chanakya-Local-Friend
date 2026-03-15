"""
Memory management operations (CRUD) for long-term storage.

Provides add_memory(), list_all_memories(), delete_memory(), etc.
Note: This is separate from core/memory_management.py; consider consolidating.
"""

import sqlite3
import datetime

DATABASE = "database/long_term_memory.db"


def add_memory(memory_text):
    """Add a new memory with current timestamp."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    now = datetime.datetime.now()
    formatted_datetime = now.strftime("%Y-%m-%d, Time: %I:%M:%S %p")  # Format datetime
    cursor.execute(
        "INSERT INTO memories (datetime, memory) VALUES (?, ?)",
        (formatted_datetime, memory_text),
    )
    conn.commit()
    conn.close()
    print(f"Memory added: {memory_text}")


def delete_memory(memory_id):
    """Delete a memory by its rowid."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM memories WHERE rowid = ?", (memory_id,)
    )  # Use rowid for deletion
    conn.commit()
    conn.close()
    print(f"Memory with ID {memory_id} deleted.")


def list_memories():
    """Print all memories from the database."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT rowid, datetime, memory FROM memories")
    memories = cursor.fetchall()
    conn.close()

    if not memories:
        print("No memories found.")
        return

    print("Memories:")
    for rowid, datetime, memory in memories:
        print(f"ID: {rowid}, Date: {datetime}, Memory: {memory}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(
            "Usage: python manage_memory.py <add|delete|list> [memory_text] [memory_id]"
        )
        sys.exit(1)

    action = sys.argv[1]

    if action == "add":
        if len(sys.argv) < 3:
            print('Usage: python manage_memory.py add "memory text"')
            sys.exit(1)
        memory_text = " ".join(sys.argv[2:])  # Allow multi-word memory
        add_memory(memory_text)

    elif action == "delete":
        if len(sys.argv) < 3:
            print("Usage: python manage_memory.py delete <memory_id>")
            sys.exit(1)
        try:
            memory_id = int(sys.argv[2])
        except ValueError:
            print("Memory ID must be an integer.")
            sys.exit(1)
        delete_memory(memory_id)

    elif action == "list":
        list_memories()

    else:
        print("Invalid action.  Use add, delete, or list.")
