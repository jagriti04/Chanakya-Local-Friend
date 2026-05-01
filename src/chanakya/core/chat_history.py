"""
Chat history management using LangChain's InMemoryChatMessageHistory.

Provides a global chat memory instance for conversation context.
"""

from langchain_core.chat_history import InMemoryChatMessageHistory

_global_chat_memory = InMemoryChatMessageHistory()


def get_chat_history(session_id: str):
    """Return the global in-memory chat history, ignoring session_id (single shared session)."""
    return _global_chat_memory
