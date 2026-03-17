"""
Tests for src/chanakya/services/audio_service.py

Focus: init_audio_services, get_tts, get_stt, OpenAITTS, OpenAISTT,
provider selection logic, config-driven initialisation, and singleton management.
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch


def _clean_chanakya_modules():
    """Remove cached chanakya modules so each test class gets a fresh import."""
    for key in list(sys.modules.keys()):
        if "chanakya" in key:
            del sys.modules[key]


def _set_env_defaults(**overrides):
    """Set minimal env vars needed to import chanakya modules."""
    defaults = {
        "APP_SECRET_KEY": "test-audio",
        "FLASK_DEBUG": "True",
        "DATABASE_PATH": ":memory:",
        "LLM_PROVIDER": "ollama",
        "TTS_PROVIDER": "openai",
        "STT_PROVIDER": "openai",
        "TTS_BASE_URL": "http://localhost:9999/v1",
        "TTS_API_KEY": "test-key",
        "TTS_MODEL": "test-tts-model",
        "TTS_VOICE": "test-voice",
        "STT_BASE_URL": "http://localhost:9999/v1",
        "STT_API_KEY": "test-key",
        "STT_MODEL": "test-stt-model",
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        os.environ.setdefault(k, v)


# ──────────────────────────────────────────────────────────────────────
# OpenAITTS unit tests
# ──────────────────────────────────────────────────────────────────────


class TestOpenAITTSUnit(unittest.TestCase):
    """Unit tests for the OpenAITTS class."""

    def setUp(self):
        _clean_chanakya_modules()
        _set_env_defaults()

    @patch("openai.OpenAI")
    def test_generate_uses_default_voice(self, MockOpenAI):
        """generate() should use the default_voice when no override is given."""
        from src.chanakya.services.audio_service import OpenAITTS

        mock_client = MagicMock()
        MockOpenAI.return_value = mock_client
        mock_client.audio.speech.create.return_value = MagicMock(content=b"audio-bytes")

        tts = OpenAITTS(
            base_url="http://test:8080/v1",
            api_key="key",
            model="model-1",
            default_voice="echo",
        )
        result = tts.generate("Hello world")

        mock_client.audio.speech.create.assert_called_once_with(
            model="model-1",
            voice="echo",
            input="Hello world",
        )
        self.assertEqual(result, b"audio-bytes")

    @patch("openai.OpenAI")
    def test_generate_uses_override_voice(self, MockOpenAI):
        """generate() should use a voice override when provided."""
        from src.chanakya.services.audio_service import OpenAITTS

        mock_client = MagicMock()
        MockOpenAI.return_value = mock_client
        mock_client.audio.speech.create.return_value = MagicMock(content=b"data")

        tts = OpenAITTS(
            base_url="http://test:8080/v1",
            api_key="key",
            model="model-1",
            default_voice="echo",
        )
        tts.generate("Hi", voice="nova")

        mock_client.audio.speech.create.assert_called_once_with(
            model="model-1",
            voice="nova",
            input="Hi",
        )

    @patch("openai.OpenAI")
    def test_generate_returns_bytes(self, MockOpenAI):
        """generate() must return raw bytes."""
        from src.chanakya.services.audio_service import OpenAITTS

        mock_client = MagicMock()
        MockOpenAI.return_value = mock_client
        mock_client.audio.speech.create.return_value = MagicMock(content=b"\x00\x01")

        tts = OpenAITTS(
            base_url="http://test:8080/v1",
            api_key="k",
            model="m",
            default_voice="v",
        )
        result = tts.generate("text")
        self.assertIsInstance(result, bytes)


# ──────────────────────────────────────────────────────────────────────
# OpenAISTT unit tests
# ──────────────────────────────────────────────────────────────────────


class TestOpenAISTTUnit(unittest.TestCase):
    """Unit tests for the OpenAISTT class."""

    def setUp(self):
        _clean_chanakya_modules()
        _set_env_defaults()

    @patch("openai.OpenAI")
    def test_transcribe_returns_text(self, MockOpenAI):
        """transcribe() should return the text attribute of the API response."""
        from src.chanakya.services.audio_service import OpenAISTT

        mock_client = MagicMock()
        MockOpenAI.return_value = mock_client
        mock_result = MagicMock()
        mock_result.text = "hello world"
        mock_client.audio.transcriptions.create.return_value = mock_result

        stt = OpenAISTT(
            base_url="http://test:8080/v1",
            api_key="key",
            model="whisper-1",
        )

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"fake-audio")
            path = f.name

        try:
            result = stt.transcribe(path)
            self.assertEqual(result, "hello world")
            mock_client.audio.transcriptions.create.assert_called_once()
        finally:
            os.unlink(path)

    @patch("openai.OpenAI")
    def test_transcribe_passes_language_en(self, MockOpenAI):
        """transcribe() should pass language='en' to the API."""
        from src.chanakya.services.audio_service import OpenAISTT

        mock_client = MagicMock()
        MockOpenAI.return_value = mock_client
        mock_client.audio.transcriptions.create.return_value = MagicMock(text="txt")

        stt = OpenAISTT(base_url="http://x/v1", api_key="k", model="m")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"data")
            path = f.name

        try:
            stt.transcribe(path)
            call_kwargs = mock_client.audio.transcriptions.create.call_args
            self.assertEqual(
                call_kwargs.kwargs.get("language") or call_kwargs[1].get("language"), "en"
            )
        finally:
            os.unlink(path)


# ──────────────────────────────────────────────────────────────────────
# init_audio_services tests
# ──────────────────────────────────────────────────────────────────────


class TestInitAudioServices(unittest.TestCase):
    """Tests for the init_audio_services() initialisation function."""

    def setUp(self):
        _clean_chanakya_modules()

    @patch("openai.OpenAI")
    def test_init_creates_tts_and_stt_singletons(self, MockOpenAI):
        """After calling init_audio_services, _tts_service and _stt_service should be set."""
        with patch.dict(
            os.environ,
            {
                "APP_SECRET_KEY": "test",
                "FLASK_DEBUG": "True",
                "DATABASE_PATH": ":memory:",
                "LLM_PROVIDER": "ollama",
                "TTS_PROVIDER": "openai",
                "STT_PROVIDER": "openai",
                "TTS_BASE_URL": "http://localhost:8080/v1",
                "STT_BASE_URL": "http://localhost:8080/v1",
            },
        ):
            from src.chanakya.services import audio_service

            audio_service._tts_service = None
            audio_service._stt_service = None

            audio_service.init_audio_services()

            self.assertIsNotNone(audio_service._tts_service)
            self.assertIsNotNone(audio_service._stt_service)
            self.assertIsInstance(audio_service._tts_service, audio_service.OpenAITTS)
            self.assertIsInstance(audio_service._stt_service, audio_service.OpenAISTT)

    def test_unsupported_tts_provider_raises_value_error(self):
        """init_audio_services should raise ValueError for unknown TTS_PROVIDER."""
        with patch.dict(
            os.environ,
            {
                "APP_SECRET_KEY": "test",
                "FLASK_DEBUG": "True",
                "DATABASE_PATH": ":memory:",
                "LLM_PROVIDER": "ollama",
                "TTS_PROVIDER": "unsupported_provider",
                "STT_PROVIDER": "openai",
            },
        ):
            _clean_chanakya_modules()
            from src.chanakya.services import audio_service

            audio_service._tts_service = None
            audio_service._stt_service = None

            with self.assertRaises(ValueError) as ctx:
                audio_service.init_audio_services()
            self.assertIn("unsupported_provider", str(ctx.exception).lower())

    @patch("openai.OpenAI")
    def test_unsupported_stt_provider_raises_value_error(self, MockOpenAI):
        """init_audio_services should raise ValueError for unknown STT_PROVIDER."""
        with patch.dict(
            os.environ,
            {
                "APP_SECRET_KEY": "test",
                "FLASK_DEBUG": "True",
                "DATABASE_PATH": ":memory:",
                "LLM_PROVIDER": "ollama",
                "TTS_PROVIDER": "openai",
                "STT_PROVIDER": "unsupported_stt",
                "TTS_BASE_URL": "http://localhost:8080/v1",
            },
        ):
            _clean_chanakya_modules()
            from src.chanakya.services import audio_service

            audio_service._tts_service = None
            audio_service._stt_service = None

            with self.assertRaises(ValueError) as ctx:
                audio_service.init_audio_services()
            self.assertIn("unsupported_stt", str(ctx.exception).lower())


# ──────────────────────────────────────────────────────────────────────
# get_tts / get_stt accessor tests
# ──────────────────────────────────────────────────────────────────────


class TestGetTTSGetSTT(unittest.TestCase):
    """Tests for get_tts() and get_stt() lazy-init accessors."""

    def setUp(self):
        _clean_chanakya_modules()

    @patch("openai.OpenAI")
    def test_get_tts_returns_service_after_init(self, MockOpenAI):
        """get_tts() should return the TTS service after init."""
        with patch.dict(
            os.environ,
            {
                "APP_SECRET_KEY": "test",
                "FLASK_DEBUG": "True",
                "DATABASE_PATH": ":memory:",
                "LLM_PROVIDER": "ollama",
                "TTS_PROVIDER": "openai",
                "STT_PROVIDER": "openai",
                "TTS_BASE_URL": "http://localhost:8080/v1",
                "STT_BASE_URL": "http://localhost:8080/v1",
            },
        ):
            from src.chanakya.services import audio_service

            audio_service._tts_service = None
            audio_service._stt_service = None
            audio_service.init_audio_services()

            tts = audio_service.get_tts()
            self.assertIsInstance(tts, audio_service.OpenAITTS)

    @patch("openai.OpenAI")
    def test_get_stt_returns_service_after_init(self, MockOpenAI):
        """get_stt() should return the STT service after init."""
        with patch.dict(
            os.environ,
            {
                "APP_SECRET_KEY": "test",
                "FLASK_DEBUG": "True",
                "DATABASE_PATH": ":memory:",
                "LLM_PROVIDER": "ollama",
                "TTS_PROVIDER": "openai",
                "STT_PROVIDER": "openai",
                "TTS_BASE_URL": "http://localhost:8080/v1",
                "STT_BASE_URL": "http://localhost:8080/v1",
            },
        ):
            from src.chanakya.services import audio_service

            audio_service._tts_service = None
            audio_service._stt_service = None
            audio_service.init_audio_services()

            stt = audio_service.get_stt()
            self.assertIsInstance(stt, audio_service.OpenAISTT)

    @patch("openai.OpenAI")
    def test_get_tts_auto_initialises_when_none(self, MockOpenAI):
        """get_tts() should call init_audio_services if _tts_service is None."""
        with patch.dict(
            os.environ,
            {
                "APP_SECRET_KEY": "test",
                "FLASK_DEBUG": "True",
                "DATABASE_PATH": ":memory:",
                "LLM_PROVIDER": "ollama",
                "TTS_PROVIDER": "openai",
                "STT_PROVIDER": "openai",
                "TTS_BASE_URL": "http://localhost:8080/v1",
                "STT_BASE_URL": "http://localhost:8080/v1",
            },
        ):
            from src.chanakya.services import audio_service

            audio_service._tts_service = None
            audio_service._stt_service = None

            tts = audio_service.get_tts()
            self.assertIsNotNone(tts)

    @patch("openai.OpenAI")
    def test_get_stt_auto_initialises_when_none(self, MockOpenAI):
        """get_stt() should call init_audio_services if _stt_service is None."""
        with patch.dict(
            os.environ,
            {
                "APP_SECRET_KEY": "test",
                "FLASK_DEBUG": "True",
                "DATABASE_PATH": ":memory:",
                "LLM_PROVIDER": "ollama",
                "TTS_PROVIDER": "openai",
                "STT_PROVIDER": "openai",
                "TTS_BASE_URL": "http://localhost:8080/v1",
                "STT_BASE_URL": "http://localhost:8080/v1",
            },
        ):
            from src.chanakya.services import audio_service

            audio_service._tts_service = None
            audio_service._stt_service = None

            stt = audio_service.get_stt()
            self.assertIsNotNone(stt)


# ──────────────────────────────────────────────────────────────────────
# Config-driven initialisation tests (integration-style)
# ──────────────────────────────────────────────────────────────────────


class TestAudioServiceConfigIntegration(unittest.TestCase):
    """Tests that audio_service reads config values correctly from the config module."""

    def setUp(self):
        _clean_chanakya_modules()

    @patch("openai.OpenAI")
    def test_tts_model_from_config(self, MockOpenAI):
        """OpenAITTS should use the model name from config."""
        with patch.dict(
            os.environ,
            {
                "APP_SECRET_KEY": "test",
                "FLASK_DEBUG": "True",
                "DATABASE_PATH": ":memory:",
                "LLM_PROVIDER": "ollama",
                "TTS_PROVIDER": "openai",
                "STT_PROVIDER": "openai",
                "TTS_BASE_URL": "http://custom:1234/v1",
                "TTS_MODEL": "custom-tts-model",
                "TTS_VOICE": "custom-voice",
                "STT_BASE_URL": "http://localhost:8080/v1",
            },
        ):
            from src.chanakya.services import audio_service

            audio_service._tts_service = None
            audio_service._stt_service = None
            audio_service.init_audio_services()

            self.assertEqual(audio_service._tts_service.model, "custom-tts-model")
            self.assertEqual(audio_service._tts_service.default_voice, "custom-voice")

    @patch("openai.OpenAI")
    def test_stt_model_from_config(self, MockOpenAI):
        """OpenAISTT should use the model name from config."""
        with patch.dict(
            os.environ,
            {
                "APP_SECRET_KEY": "test",
                "FLASK_DEBUG": "True",
                "DATABASE_PATH": ":memory:",
                "LLM_PROVIDER": "ollama",
                "TTS_PROVIDER": "openai",
                "STT_PROVIDER": "openai",
                "TTS_BASE_URL": "http://localhost:8080/v1",
                "STT_BASE_URL": "http://custom:5678/v1",
                "STT_MODEL": "custom-stt-model",
            },
        ):
            from src.chanakya.services import audio_service

            audio_service._tts_service = None
            audio_service._stt_service = None
            audio_service.init_audio_services()

            self.assertEqual(audio_service._stt_service.model, "custom-stt-model")


if __name__ == "__main__":
    unittest.main()
