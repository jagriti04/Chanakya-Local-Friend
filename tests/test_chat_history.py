"""
Tests for src/chanakya/core/chat_history.py

Focus: get_chat_history returns the same global memory instance,
and InMemoryChatMessageHistory interface.
"""

import os
import sys
import unittest


def _clean_chanakya_modules():
    for key in list(sys.modules.keys()):
        if 'chanakya' in key:
            del sys.modules[key]


class TestGetChatHistory(unittest.TestCase):
    """Tests for get_chat_history function."""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('APP_SECRET_KEY', 'test-chat-history')
        os.environ.setdefault('FLASK_DEBUG', 'True')
        os.environ.setdefault('DATABASE_PATH', ':memory:')
        os.environ.setdefault('LLM_PROVIDER', 'ollama')

    def setUp(self):
        _clean_chanakya_modules()
        from src.chanakya.core.chat_history import get_chat_history
        self.get_chat_history = get_chat_history

    def test_returns_same_instance_regardless_of_session_id(self):
        """get_chat_history should return the same global memory for any session_id."""
        history_a = self.get_chat_history('session-1')
        history_b = self.get_chat_history('session-2')
        history_c = self.get_chat_history('different')
        self.assertIs(history_a, history_b)
        self.assertIs(history_b, history_c)

    def test_returned_object_has_messages_attribute(self):
        """The returned object should have a messages list."""
        history = self.get_chat_history('test')
        self.assertTrue(hasattr(history, 'messages'))
        self.assertIsInstance(history.messages, list)

    def test_returned_object_has_add_message_methods(self):
        """The returned object should have add_user_message and add_ai_message methods."""
        history = self.get_chat_history('test')
        self.assertTrue(callable(getattr(history, 'add_user_message', None)))
        self.assertTrue(callable(getattr(history, 'add_ai_message', None)))

    def test_add_and_retrieve_messages(self):
        """Messages added should be retrievable."""
        history = self.get_chat_history('test')
        initial_count = len(history.messages)
        history.add_user_message('hello')
        history.add_ai_message('hi there')
        self.assertEqual(len(history.messages), initial_count + 2)


if __name__ == '__main__':
    unittest.main()
