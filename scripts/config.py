# config.py configurations for Chanakya

import os
from dotenv import load_dotenv
load_dotenv()

# General App Config
APP_SECRET_KEY = os.environ.get('APP_SECRET_KEY', str(os.urandom(24))) # Use env var or generate
DEBUG_MODE = os.environ.get('FLASK_DEBUG', 'True').lower() in ('true', '1', 't')
WAKE_WORD = os.environ.get('WAKE_WORD', "Chanakya")

# LLM Configuration
LLM_PROVIDER = os.environ.get('LLM_PROVIDER', 'ollama').strip().strip('"').strip("'")
LLM_ENDPOINT = os.environ.get('LLM_ENDPOINT', '').strip().strip('"').strip("'") or None
_raw_model_name = os.environ.get('LLM_MODEL_NAME', '')
LLM_MODEL_NAME = _raw_model_name.strip().strip('"').strip("'") or None
LLM_NUM_CTX = int(os.environ.get('LLM_NUM_CTX', 2048))
LLM_API_KEY = os.environ.get('LLM_API_KEY', '').strip().strip('"').strip("'") or None

# Configuration for a smaller, secondary model (optional)
# If these are not set in the .env file, they will fall back to the primary model's configuration.
# If they are set to an empty string, query refinement will be disabled.
llm_endpoint_small_env = os.environ.get('LLM_ENDPOINT_SMALL')
LLM_ENDPOINT_SMALL = llm_endpoint_small_env if llm_endpoint_small_env is not None else LLM_ENDPOINT

llm_model_name_small_env = os.environ.get('LLM_MODEL_NAME_SMALL')
LLM_MODEL_NAME_SMALL = llm_model_name_small_env if llm_model_name_small_env is not None else LLM_MODEL_NAME

llm_num_ctx_small_env = os.environ.get('LLM_NUM_CTX_SMALL')
if llm_num_ctx_small_env is not None:
    # If the variable is set, use it. If it's an empty string, use the default from the original code.
    LLM_NUM_CTX_SMALL = int(llm_num_ctx_small_env) if llm_num_ctx_small_env else 2048
else:
    # If the variable is not set at all, fall back to the main model's context size.
    LLM_NUM_CTX_SMALL = LLM_NUM_CTX

# stt and tts Configuration
STT_SERVER_URL = os.environ.get('STT_SERVER_URL') # Default STT API URL
TTS_ENGINE = os.environ.get('TTS_ENGINE', "coqui") # coqui (human like, fast) or chatterbox (great voice cloning, slow) or piper (fastest, but fails on some tests)
if TTS_ENGINE == "chatterbox":
    TTS_SERVER_URL = None  # Chatterbox does not use a server URL
elif TTS_ENGINE == "coqui":
    TTS_SERVER_URL = os.environ.get('TTS_SERVER_URL') 
elif TTS_ENGINE == "piper":
    TTS_SERVER_URL = os.environ.get('TTS_SERVER_URL') 

# Database Configuration
DATABASE_PATH = os.environ.get('DATABASE_PATH')

# Client Activity Tracking
CLIENT_INACTIVE_THRESHOLD = int(os.environ.get('CLIENT_INACTIVE_THRESHOLD', 10))
CLIENT_SAVE_INTERVAL = int(os.environ.get('CLIENT_SAVE_INTERVAL', 10))
CLIENT_COUNT_FILE = os.environ.get('CLIENT_COUNT_FILE', "client_count.txt")

# Paths
# Assuming chanakya.py is in the project root. If not, adjust '..' accordingly.
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__)) 
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")

# Debug: Print resolved config values at startup
print(f"[CONFIG DEBUG] LLM_PROVIDER='{LLM_PROVIDER}'")
print(f"[CONFIG DEBUG] LLM_ENDPOINT='{LLM_ENDPOINT}'")
print(f"[CONFIG DEBUG] LLM_MODEL_NAME='{LLM_MODEL_NAME}' (raw env: '{_raw_model_name}')")
print(f"[CONFIG DEBUG] LLM_MODEL_NAME_SMALL='{LLM_MODEL_NAME_SMALL}'")
print(f"[CONFIG DEBUG] LLM_ENDPOINT_SMALL='{LLM_ENDPOINT_SMALL}'")