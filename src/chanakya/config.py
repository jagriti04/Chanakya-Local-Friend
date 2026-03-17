"""
Configuration management for Chanakya.

Handles environment variable loading, validation, and application-wide settings.
Provides the get_env_clean() helper for parsing .env values with comments/quotes.
"""

import os
import secrets

from dotenv import load_dotenv

load_dotenv()


def get_env_clean(key, default=None):
    """Helper to get and clean environment variables."""
    val = os.environ.get(key, default)
    if val is None:
        return None
    if not isinstance(val, str):
        return val
    # Remove inline comments if they leaked into the environment
    if "#" in val:
        idx = val.find("#")
        if idx == 0 or val[idx - 1].isspace():
            val = val[:idx]
    val = val.strip()
    # Remove surrounding quotes
    if len(val) >= 2:
        if (val[0] == '"' and val[-1] == '"') or (val[0] == "'" and val[-1] == "'"):
            val = val[1:-1]
    return val.strip()


# General App Config
DEBUG_MODE = os.environ.get("FLASK_DEBUG", "True").lower() in ("true", "1", "t")

# Secure APP_SECRET_KEY handling
APP_SECRET_KEY = os.environ.get("APP_SECRET_KEY")
if not APP_SECRET_KEY:
    if DEBUG_MODE:
        APP_SECRET_KEY = secrets.token_hex(32)
        print(
            f"[CONFIG WARNING] APP_SECRET_KEY not set. Using generated dev fallback: {APP_SECRET_KEY}"
        )
    else:
        raise ValueError(
            "APP_SECRET_KEY environment variable is required in production mode (FLASK_DEBUG is False)."
        )

WAKE_WORD = os.environ.get("WAKE_WORD", "Chanakya")

# LLM Configuration
LLM_PROVIDER = get_env_clean("LLM_PROVIDER", "ollama")
LLM_ENDPOINT = get_env_clean("LLM_ENDPOINT")

# Fix for OpenAI-compatible providers missing /v1 suffix in local setups (like LM Studio)
if LLM_PROVIDER.lower() in ["openai", "lmstudio"] and LLM_ENDPOINT:
    if not LLM_ENDPOINT.endswith("/v1") and not LLM_ENDPOINT.endswith("/v1/"):
        LLM_ENDPOINT = LLM_ENDPOINT.rstrip("/") + "/v1"

_raw_model_name = get_env_clean("LLM_MODEL_NAME", "")
LLM_MODEL_NAME = _raw_model_name or None
LLM_NUM_CTX = int(get_env_clean("LLM_NUM_CTX", "2048"))
LLM_API_KEY = get_env_clean("LLM_API_KEY")

# Configuration for a smaller, secondary model (optional)
# If these are not set in the .env file, they will fall back to the primary model's configuration.
# If they are set to an empty string, query refinement will be disabled.
llm_endpoint_small_env = get_env_clean("LLM_ENDPOINT_SMALL")
LLM_ENDPOINT_SMALL = llm_endpoint_small_env if llm_endpoint_small_env is not None else LLM_ENDPOINT

# Also fix the small model endpoint if it's using OpenAI/LMStudio
if LLM_PROVIDER.lower() in ["openai", "lmstudio"] and LLM_ENDPOINT_SMALL:
    if not LLM_ENDPOINT_SMALL.endswith("/v1") and not LLM_ENDPOINT_SMALL.endswith("/v1/"):
        LLM_ENDPOINT_SMALL = LLM_ENDPOINT_SMALL.rstrip("/") + "/v1"

llm_model_name_small_env = get_env_clean("LLM_MODEL_NAME_SMALL")
LLM_MODEL_NAME_SMALL = (
    llm_model_name_small_env if llm_model_name_small_env is not None else LLM_MODEL_NAME
)

llm_num_ctx_small_env = get_env_clean("LLM_NUM_CTX_SMALL")
if llm_num_ctx_small_env is not None:
    # If the variable is set, use it. If it's an empty string, use the default.
    if llm_num_ctx_small_env:
        try:
            LLM_NUM_CTX_SMALL = int(llm_num_ctx_small_env)
        except ValueError:
            print(
                f"[CONFIG WARNING] Invalid LLM_NUM_CTX_SMALL: '{llm_num_ctx_small_env}', using 2048"
            )
            LLM_NUM_CTX_SMALL = 2048
    else:
        LLM_NUM_CTX_SMALL = 2048
else:
    # If the variable is not set at all, fall back to the main model's context size.
    LLM_NUM_CTX_SMALL = LLM_NUM_CTX

# TTS Configuration
TTS_PROVIDER = get_env_clean("TTS_PROVIDER", "openai")
TTS_BASE_URL = get_env_clean("TTS_BASE_URL", "http://localhost:8080/v1")
TTS_MODEL = get_env_clean("TTS_MODEL", "tts-1")
TTS_VOICE = get_env_clean("TTS_VOICE", "alloy")
TTS_API_KEY = get_env_clean("TTS_API_KEY", "not-required")

# STT Configuration
STT_PROVIDER = get_env_clean("STT_PROVIDER", "openai")
STT_BASE_URL = get_env_clean("STT_BASE_URL", "http://localhost:8080/v1")
STT_MODEL = get_env_clean("STT_MODEL", "whisper-1")
STT_API_KEY = get_env_clean("STT_API_KEY", "not-required")

# Database Configuration
DATABASE_PATH = get_env_clean("DATABASE_PATH")

# Client Activity Tracking
CLIENT_INACTIVE_THRESHOLD = int(os.environ.get("CLIENT_INACTIVE_THRESHOLD", 10))
CLIENT_SAVE_INTERVAL = int(os.environ.get("CLIENT_SAVE_INTERVAL", 10))
CLIENT_COUNT_FILE = os.environ.get("CLIENT_COUNT_FILE", "client_count.txt")

# Paths
# PROJECT_ROOT points to the repository root (two levels up from src/chanakya/config.py)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")

# Debug: Print resolved config values at startup
print(f"[CONFIG DEBUG] LLM_PROVIDER='{LLM_PROVIDER}'")
print(f"[CONFIG DEBUG] LLM_ENDPOINT='{LLM_ENDPOINT}'")
print(f"[CONFIG DEBUG] LLM_MODEL_NAME='{LLM_MODEL_NAME}' (raw env: '{_raw_model_name}')")
print(f"[CONFIG DEBUG] LLM_MODEL_NAME_SMALL='{LLM_MODEL_NAME_SMALL}'")
print(f"[CONFIG DEBUG] LLM_ENDPOINT_SMALL='{LLM_ENDPOINT_SMALL}'")
