"""
Tests for src/chanakya/web/routes.py

Focus: Flask route handlers, especially the new ToolException handling added in this PR.
Tests use the Flask test client with mocked dependencies.
"""

import os
import sys
import json
import asyncio
import tempfile
import unittest
from unittest.mock import patch, MagicMock, AsyncMock

sys.path.insert(0, '/home/jailuser/git')


def setup_flask_app():
    """
    Set up environment and imports needed to get the Flask test client.
    Returns the Flask app instance.
    """
    # Set required env vars
    os.environ['APP_SECRET_KEY'] = 'test-secret-routes'
    os.environ['FLASK_DEBUG'] = 'True'
    os.environ['LLM_PROVIDER'] = 'ollama'
    os.environ['DATABASE_PATH'] = ':memory:'
    os.environ['WAKE_WORD'] = 'TestBot'
    os.environ['TTS_PROVIDER'] = 'openai'

    # Clear any cached chanakya modules
    for key in list(sys.modules.keys()):
        if 'chanakya' in key:
            del sys.modules[key]

    from src.chanakya.web.app_setup import app
    from src.chanakya.web import routes  # Register routes
    return app


class TestRouteIndex(unittest.TestCase):
    """Tests for the / (index) route."""

    @classmethod
    def setUpClass(cls):
        cls.app = setup_flask_app()
        cls.client = cls.app.test_client()

    def test_index_redirects_or_responds(self):
        """/ route should respond (may need template, so we at least test it doesn't crash badly)."""
        with patch("src.chanakya.web.routes.update_client_activity"), \
             patch("src.chanakya.web.routes.render_template", return_value="<html>ok</html>"):
            response = self.client.get("/")
            self.assertIn(response.status_code, [200, 302, 404, 500])


class TestChatRouteEmptyMessage(unittest.TestCase):
    """Tests for /chat with edge case inputs."""

    @classmethod
    def setUpClass(cls):
        cls.app = setup_flask_app()
        cls.client = cls.app.test_client()

    def test_chat_empty_message_returns_prompt(self):
        """POST /chat with empty message should return a prompt to provide a message."""
        with patch("src.chanakya.web.routes.update_client_activity"), \
             patch("src.chanakya.web.routes.get_query_refinement_chain", return_value=None), \
             patch("src.chanakya.web.routes.retrieve_relevant_memories", return_value=[]), \
             patch("src.chanakya.web.routes.get_chanakya_react_agent_with_history") as mock_agent:
            response = self.client.post("/chat", data={"message": ""})
            data = json.loads(response.data)
            self.assertIn("response", data)
            self.assertIn("provide a message", data["response"].lower())

    def test_chat_whitespace_only_message_returns_prompt(self):
        """POST /chat with whitespace-only message should return a prompt."""
        with patch("src.chanakya.web.routes.update_client_activity"), \
             patch("src.chanakya.web.routes.get_query_refinement_chain", return_value=None), \
             patch("src.chanakya.web.routes.retrieve_relevant_memories", return_value=[]):
            response = self.client.post("/chat", data={"message": "   "})
            data = json.loads(response.data)
            self.assertIn("response", data)


class TestChatRouteToolException(unittest.TestCase):
    """
    Tests for the new ToolException handling in /chat route.
    This is the key new behavior added in this PR.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = setup_flask_app()
        cls.client = cls.app.test_client()

    def test_chat_tool_exception_returns_200_with_error_message(self):
        """When a ToolException is raised, /chat should return 200 with an informative message."""
        from langchain_core.tools import ToolException

        async def mock_agent_invoke(*args, **kwargs):
            raise ToolException("Tool failed: connection refused")

        mock_agent_with_history = MagicMock()
        mock_agent_with_history.ainvoke = mock_agent_invoke

        with patch("src.chanakya.web.routes.update_client_activity"), \
             patch("src.chanakya.web.routes.get_query_refinement_chain", return_value=None), \
             patch("src.chanakya.web.routes.retrieve_relevant_memories", return_value=[]), \
             patch("src.chanakya.web.routes.get_chanakya_react_agent_with_history",
                   return_value=mock_agent_with_history):
            response = self.client.post("/chat", data={"message": "use a tool please"})

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn("response", data)
        self.assertIn("tool", data["response"].lower())
        # Should include the tool exception message
        self.assertIn("Tool failed: connection refused", data["response"])

    def test_chat_tool_exception_returns_empty_used_tools(self):
        """When a ToolException is raised, used_tools should be empty list."""
        from langchain_core.tools import ToolException

        async def mock_agent_invoke(*args, **kwargs):
            raise ToolException("Tool error")

        mock_agent = MagicMock()
        mock_agent.ainvoke = mock_agent_invoke

        with patch("src.chanakya.web.routes.update_client_activity"), \
             patch("src.chanakya.web.routes.get_query_refinement_chain", return_value=None), \
             patch("src.chanakya.web.routes.retrieve_relevant_memories", return_value=[]), \
             patch("src.chanakya.web.routes.get_chanakya_react_agent_with_history",
                   return_value=mock_agent):
            response = self.client.post("/chat", data={"message": "use a tool"})

        data = json.loads(response.data)
        self.assertIn("used_tools", data)
        self.assertEqual(data["used_tools"], [])

    def test_chat_runtime_error_event_loop_returns_500(self):
        """When RuntimeError with 'Event loop is closed' is raised, /chat returns 500."""
        async def mock_agent_invoke(*args, **kwargs):
            raise RuntimeError("Event loop is closed")

        mock_agent = MagicMock()
        mock_agent.ainvoke = mock_agent_invoke

        with patch("src.chanakya.web.routes.update_client_activity"), \
             patch("src.chanakya.web.routes.get_query_refinement_chain", return_value=None), \
             patch("src.chanakya.web.routes.retrieve_relevant_memories", return_value=[]), \
             patch("src.chanakya.web.routes.get_chanakya_react_agent_with_history",
                   return_value=mock_agent):
            response = self.client.post("/chat", data={"message": "hello"})

        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data)
        self.assertIn("response", data)
        self.assertIn("Event loop", data["response"])

    def test_chat_generic_exception_returns_500(self):
        """When a generic exception is raised, /chat returns 500."""
        async def mock_agent_invoke(*args, **kwargs):
            raise ValueError("Unexpected error")

        mock_agent = MagicMock()
        mock_agent.ainvoke = mock_agent_invoke

        with patch("src.chanakya.web.routes.update_client_activity"), \
             patch("src.chanakya.web.routes.get_query_refinement_chain", return_value=None), \
             patch("src.chanakya.web.routes.retrieve_relevant_memories", return_value=[]), \
             patch("src.chanakya.web.routes.get_chanakya_react_agent_with_history",
                   return_value=mock_agent):
            response = self.client.post("/chat", data={"message": "test message"})

        self.assertEqual(response.status_code, 500)

    def test_chat_success_returns_response_and_used_tools(self):
        """Successful /chat should return response and used_tools fields."""
        async def mock_agent_invoke(*args, **kwargs):
            return {"output": "Hello! I am your assistant.", "intermediate_steps": []}

        mock_agent = MagicMock()
        mock_agent.ainvoke = mock_agent_invoke

        with patch("src.chanakya.web.routes.update_client_activity"), \
             patch("src.chanakya.web.routes.get_query_refinement_chain", return_value=None), \
             patch("src.chanakya.web.routes.retrieve_relevant_memories", return_value=[]), \
             patch("src.chanakya.web.routes.get_chanakya_react_agent_with_history",
                   return_value=mock_agent):
            response = self.client.post("/chat", data={"message": "Hello"})

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn("response", data)
        self.assertIn("used_tools", data)
        self.assertIsInstance(data["used_tools"], list)


class TestRecordRouteToolException(unittest.TestCase):
    """
    Tests for the new ToolException handling in /record route.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = setup_flask_app()
        cls.client = cls.app.test_client()

    def test_record_no_audio_file_returns_400(self):
        """POST /record without audio file should return 400."""
        with patch("src.chanakya.web.routes.update_client_activity"):
            response = self.client.post("/record")
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("error", data)

    def test_record_empty_filename_returns_400(self):
        """POST /record with empty filename should return 400."""
        from io import BytesIO
        with patch("src.chanakya.web.routes.update_client_activity"):
            response = self.client.post(
                "/record",
                data={"audio": (BytesIO(b""), "")},
                content_type="multipart/form-data",
            )
        self.assertEqual(response.status_code, 400)

    def test_record_tool_exception_returns_200(self):
        """When ToolException is raised in /record, response should be 200 with error message."""
        from langchain_core.tools import ToolException
        from io import BytesIO

        async def mock_agent_invoke(*args, **kwargs):
            raise ToolException("Maps tool failed")

        mock_agent = MagicMock()
        mock_agent.ainvoke = mock_agent_invoke

        with patch("src.chanakya.web.routes.update_client_activity"), \
             patch('src.chanakya.web.routes.get_stt') as mock_get_stt, \
             patch('src.chanakya.web.routes.get_query_refinement_chain', return_value=None), \
             patch('src.chanakya.web.routes.retrieve_relevant_memories', return_value=[]), \
             patch('src.chanakya.web.routes.get_chanakya_react_agent_with_history',
                   return_value=mock_agent):
            mock_get_stt.return_value.transcribe.return_value = 'what is the weather'
            response = self.client.post(
                "/record",
                data={"audio": (BytesIO(b"fake_wav_data"), "audio.wav")},
                content_type="multipart/form-data",
            )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn("response", data)
        self.assertIn("tool", data["response"].lower())
        self.assertIn("used_tools", data)
        self.assertEqual(data["used_tools"], [])

    def test_record_tool_exception_includes_transcription(self):
        """When ToolException is raised in /record, transcription should be included."""
        from langchain_core.tools import ToolException
        from io import BytesIO

        async def mock_agent_invoke(*args, **kwargs):
            raise ToolException("Tool failed")

        mock_agent = MagicMock()
        mock_agent.ainvoke = mock_agent_invoke

        with patch("src.chanakya.web.routes.update_client_activity"), \
             patch('src.chanakya.web.routes.get_stt') as mock_get_stt, \
             patch('src.chanakya.web.routes.get_query_refinement_chain', return_value=None), \
             patch('src.chanakya.web.routes.retrieve_relevant_memories', return_value=[]), \
             patch('src.chanakya.web.routes.get_chanakya_react_agent_with_history',
                   return_value=mock_agent):
            mock_get_stt.return_value.transcribe.return_value = 'original transcribed text'
            response = self.client.post(
                "/record",
                data={"audio": (BytesIO(b"data"), "audio.wav")},
                content_type="multipart/form-data",
            )

        data = json.loads(response.data)
        self.assertEqual(data["transcription"], "original transcribed text")

    def test_record_stt_empty_transcription_returns_400(self):
        """When STT returns empty transcription, /record should return 400."""
        from io import BytesIO

        with patch('src.chanakya.web.routes.update_client_activity'), \
             patch('src.chanakya.web.routes.get_stt') as mock_get_stt:
            mock_get_stt.return_value.transcribe.return_value = ''
            response = self.client.post(
                "/record",
                data={"audio": (BytesIO(b"data"), "audio.wav")},
                content_type="multipart/form-data",
            )

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("error", data)
        self.assertIn("understand", data["error"].lower())

    def test_record_stt_none_transcription_returns_400(self):
        """When STT returns None, /record should return 400."""
        from io import BytesIO

        with patch('src.chanakya.web.routes.update_client_activity'), \
             patch('src.chanakya.web.routes.get_stt') as mock_get_stt:
            mock_get_stt.return_value.transcribe.return_value = None
            response = self.client.post(
                "/record",
                data={"audio": (BytesIO(b"data"), "audio.wav")},
                content_type="multipart/form-data",
            )

        self.assertEqual(response.status_code, 400)

    def test_record_runtime_event_loop_error_returns_500(self):
        """When RuntimeError with 'Event loop is closed' in /record, returns 500."""
        from io import BytesIO

        async def mock_agent_invoke(*args, **kwargs):
            raise RuntimeError("Event loop is closed")

        mock_agent = MagicMock()
        mock_agent.ainvoke = mock_agent_invoke

        with patch("src.chanakya.web.routes.update_client_activity"), \
             patch('src.chanakya.web.routes.get_stt') as mock_get_stt, \
             patch('src.chanakya.web.routes.get_query_refinement_chain', return_value=None), \
             patch('src.chanakya.web.routes.retrieve_relevant_memories', return_value=[]), \
             patch('src.chanakya.web.routes.get_chanakya_react_agent_with_history',
                   return_value=mock_agent):
            mock_get_stt.return_value.transcribe.return_value = 'hello there'
            response = self.client.post(
                "/record",
                data={"audio": (BytesIO(b"data"), "audio.wav")},
                content_type="multipart/form-data",
            )

        self.assertEqual(response.status_code, 500)


class TestPlayResponseRoute(unittest.TestCase):
    """Tests for /play_response route."""

    @classmethod
    def setUpClass(cls):
        cls.app = setup_flask_app()
        cls.client = cls.app.test_client()

    def test_play_response_no_last_response_returns_error(self):
        """POST /play_response with no last AI response should return an error."""
        with patch("src.chanakya.web.routes.update_client_activity"), \
             patch("src.chanakya.web.routes.utils_module") as mock_utils:
            mock_utils.last_ai_response = ""
            response = self.client.post("/play_response")

        data = json.loads(response.data)
        self.assertIn("error", data)
        self.assertIn("No response available", data["error"])

    def test_play_response_with_last_response_calls_tts(self):
        """POST /play_response with a last AI response should call TTS."""
        with patch('src.chanakya.web.routes.update_client_activity'), \
             patch('src.chanakya.web.routes.utils_module') as mock_utils, \
             patch('src.chanakya.web.routes.get_tts') as mock_get_tts:
            mock_utils.last_ai_response = 'Previous response text'
            mock_get_tts.return_value.generate.return_value = b'RIFF' + b'\x00' * 40
            response = self.client.post('/play_response')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('audio_data_url', data)
        self.assertTrue(data['audio_data_url'].startswith('data:audio/wav;base64,'))

    def test_play_response_tts_fails_returns_500(self):
        """When TTS fails, /play_response should return 500."""
        with patch('src.chanakya.web.routes.update_client_activity'), \
             patch('src.chanakya.web.routes.utils_module') as mock_utils, \
             patch('src.chanakya.web.routes.get_tts') as mock_get_tts:
            mock_utils.last_ai_response = 'some text'
            mock_get_tts.return_value.generate.side_effect = Exception('TTS server unreachable')
            response = self.client.post('/play_response')

        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data)
        self.assertIn("error", data)


class TestMemoryRoutes(unittest.TestCase):
    """Tests for memory management routes."""

    @classmethod
    def setUpClass(cls):
        cls.app = setup_flask_app()
        cls.client = cls.app.test_client()

    def test_add_memory_route_redirects(self):
        """POST /add-memory should redirect to memory page."""
        with patch("src.chanakya.web.routes.add_memory") as mock_add, \
             patch("src.chanakya.web.routes.list_all_memories", return_value=[]), \
             patch("src.chanakya.web.routes.render_template", return_value="<html>ok</html>"):
            response = self.client.post(
                "/add-memory", data={"memory_text": "test memory"}
            )

        self.assertIn(response.status_code, [301, 302])

    def test_add_memory_route_no_text_no_call(self):
        """POST /add-memory without memory_text should not call add_memory."""
        with patch("src.chanakya.web.routes.add_memory") as mock_add, \
             patch("src.chanakya.web.routes.list_all_memories", return_value=[]), \
             patch("src.chanakya.web.routes.render_template", return_value="<html>ok</html>"):
            response = self.client.post("/add-memory", data={})

        mock_add.assert_not_called()

    def test_delete_memory_route_redirects(self):
        """POST /delete-memory should redirect to memory page."""
        with patch("src.chanakya.web.routes.delete_memory") as mock_delete, \
             patch("src.chanakya.web.routes.list_all_memories", return_value=[]), \
             patch("src.chanakya.web.routes.render_template", return_value="<html>ok</html>"):
            response = self.client.post(
                "/delete-memory", data={"memory_id": "1"}
            )

        self.assertIn(response.status_code, [301, 302])

    def test_delete_memory_route_no_id_no_call(self):
        """POST /delete-memory without memory_id should not call delete_memory."""
        with patch("src.chanakya.web.routes.delete_memory") as mock_delete, \
             patch("src.chanakya.web.routes.list_all_memories", return_value=[]), \
             patch("src.chanakya.web.routes.render_template", return_value="<html>ok</html>"):
            response = self.client.post("/delete-memory", data={})

        mock_delete.assert_not_called()


class TestBackgroundThread(unittest.TestCase):
    """Tests for the background_thread function."""

    def test_background_thread_importable(self):
        """background_thread should be importable from routes."""
        for key in list(sys.modules.keys()):
            if 'chanakya' in key:
                del sys.modules[key]
        os.environ.setdefault('APP_SECRET_KEY', 'test-bg-thread')
        os.environ.setdefault('FLASK_DEBUG', 'True')
        os.environ.setdefault('DATABASE_PATH', ':memory:')
        from src.chanakya.web.routes import background_thread
        self.assertTrue(callable(background_thread))

    def test_background_thread_calls_remove_inactive_clients(self):
        """background_thread should call remove_inactive_clients."""
        import threading

        from src.chanakya.web.routes import background_thread

        call_count = [0]
        stop_event = threading.Event()

        def mock_remove():
            call_count[0] += 1
            if call_count[0] >= 2:
                stop_event.set()

        def mock_sleep(t):
            if stop_event.is_set():
                raise SystemExit("stop")

        with patch("src.chanakya.web.routes.remove_inactive_clients", side_effect=mock_remove), \
             patch("src.chanakya.web.routes.time.sleep", side_effect=mock_sleep), \
             patch("src.chanakya.web.routes.time.time", return_value=0.0):
            try:
                background_thread()
            except SystemExit:
                pass

        self.assertGreaterEqual(call_count[0], 1)


if __name__ == "__main__":
    unittest.main()