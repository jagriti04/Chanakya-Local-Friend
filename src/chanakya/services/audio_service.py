"""
Audio Service - TTS and STT using OpenAI-compatible API endpoints.

Services are initialised once at app startup via init_audio_services().
Use get_tts() / get_stt() to obtain the singleton instances.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional

from src.chanakya import config

logger = logging.getLogger(__name__)


# =============================================================================
# ABSTRACT INTERFACES
# =============================================================================


class TTSService(ABC):
    """Abstract interface for Text-to-Speech services."""

    @abstractmethod
    def generate(self, text: str, voice: Optional[str] = None) -> bytes:
        """
        Generate audio from text.

        Args:
            text: Text to synthesise.
            voice: Optional voice ID override.

        Returns:
            Raw audio bytes.
        """


class STTService(ABC):
    """Abstract interface for Speech-to-Text services."""

    @abstractmethod
    def transcribe(self, audio_path: str) -> str:
        """
        Transcribe an audio file to text.

        Args:
            audio_path: Absolute path to the audio file.

        Returns:
            Transcribed text string.
        """


# =============================================================================
# OPENAI-COMPATIBLE IMPLEMENTATIONS
# =============================================================================


class OpenAITTS(TTSService):
    """TTS via OpenAI-compatible API (local server or remote)."""

    def __init__(self, base_url: str, api_key: str, model: str, default_voice: str):
        from openai import OpenAI

        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model = model
        self.default_voice = default_voice
        logger.info(f"OpenAI TTS initialised: model={model}, base_url={base_url}")

    def generate(self, text: str, voice: Optional[str] = None) -> bytes:
        """Generate audio bytes from text using the configured TTS model."""
        voice = voice or self.default_voice
        response = self.client.audio.speech.create(
            model=self.model,
            voice=voice,
            input=text,
        )
        return response.content


class OpenAISTT(STTService):
    """STT via OpenAI-compatible API (local server or remote)."""

    def __init__(self, base_url: str, api_key: str, model: str):
        from openai import OpenAI

        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model = model
        logger.info(f"OpenAI STT initialised: model={model}, base_url={base_url}")

    def transcribe(self, audio_path: str) -> str:
        """Transcribe an audio file to text using the configured STT model."""
        with open(audio_path, "rb") as f:
            result = self.client.audio.transcriptions.create(
                model=self.model,
                file=f,
                language="en",
            )
        return result.text


# =============================================================================
# SERVICE MANAGEMENT
# =============================================================================

_tts_service: Optional[TTSService] = None
_stt_service: Optional[STTService] = None


def init_audio_services() -> None:
    """
    Initialise TTS and STT singletons from environment config.
    Should be called once at application startup.
    """
    global _tts_service, _stt_service

    tts_provider = config.TTS_PROVIDER.lower() if config.TTS_PROVIDER else "openai"
    stt_provider = config.STT_PROVIDER.lower() if config.STT_PROVIDER else "openai"
    logger.info(f"Initialising audio services: TTS={tts_provider}, STT={stt_provider}")

    if tts_provider == "openai":
        _tts_service = OpenAITTS(
            base_url=config.TTS_BASE_URL or "http://localhost:8080/v1",
            api_key=config.TTS_API_KEY or "not-required",
            model=config.TTS_MODEL or "tts-1",
            default_voice=config.TTS_VOICE or "alloy",
        )
    else:
        raise ValueError(f"Unsupported TTS_PROVIDER: {tts_provider}")

    if stt_provider == "openai":
        _stt_service = OpenAISTT(
            base_url=config.STT_BASE_URL or "http://localhost:8080/v1",
            api_key=config.STT_API_KEY or "not-required",
            model=config.STT_MODEL or "whisper-1",
        )
    else:
        raise ValueError(f"Unsupported STT_PROVIDER: {stt_provider}")


def get_tts() -> TTSService:
    """Return the initialised TTS service, auto-initialising if needed."""
    global _tts_service
    if _tts_service is None:
        logger.info("TTS service not yet initialised. Auto-initialising...")
        init_audio_services()
    if _tts_service is None:
        raise RuntimeError("TTS service failed to initialise.")
    return _tts_service


def get_stt() -> STTService:
    """Return the initialised STT service, auto-initialising if needed."""
    global _stt_service
    if _stt_service is None:
        logger.info("STT service not yet initialised. Auto-initialising...")
        init_audio_services()
    if _stt_service is None:
        raise RuntimeError("STT service failed to initialise.")
    return _stt_service
