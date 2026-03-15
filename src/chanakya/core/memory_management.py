"""
Memory management using SQLite for long-term storage.

Provides functions to create, read, add, and delete memories with timestamps.
"""

import os
import sqlite3
import datetime
from .. import config
from ..web.app_setup import app

DATABASE_PATH = config.DATABASE_PATH


def create_table():
    """Creates the memories SQLite table if it does not exist."""
    try:
        db_dir = os.path.dirname(DATABASE_PATH)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS memories (datetime TEXT, memory TEXT)"""
        )
        conn.commit()
    except sqlite3.Error as e:
        app.logger.error(f"Database error: {e}")
    finally:
        if "conn" in locals() and conn:
            conn.close()


def retrieve_relevant_memories(user_message, limit=3):
    """Searches memories for keywords from user_message, returns up to limit matches."""
    if not user_message or not user_message.strip():
        return []
    conn = sqlite3.connect(DATABASE_PATH)
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
    except sqlite3.Error as e:
        app.logger.error(f"Database error in retrieve_relevant_memories: {e}")
        relevant_memories = []
    finally:
        conn.close()
    return relevant_memories


def list_all_memories():
    """Lists all memories from the database."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT rowid, datetime, memory FROM memories ORDER BY rowid DESC")
    memories = cursor.fetchall()
    conn.close()
    return memories


def add_memory(memory_text):
    """Adds a new memory to the database."""
    conn = sqlite3.connect(DATABASE_PATH)
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
    """Deletes a memory from the database by its ID."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM memories WHERE rowid = ?", (memory_id,))
    conn.commit()
    conn.close()
