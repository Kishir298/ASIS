"""
A.S.I.S. default configuration values.

Safe built-in defaults only. Machine-specific values and secrets must
come from environment variables or user configuration files.
"""

# Application
APP_NAME = "A.S.I.S."
APP_VERSION = "0.1.0"

# Identity
IDENTITY_TITLE = "A Smart Intelligence System"
SHUTDOWN_PHRASE = "asis shutdown"

# Runtime
DEBUG = False
LOG_LEVEL = "INFO"

# AI provider
AI_PROVIDER = "ollama"
AI_MODEL = "qwen2.5:3b"
AI_ENDPOINT = "http://127.0.0.1:11434"

# AI behavior
AI_REQUEST_TIMEOUT = 120
AI_TEMPERATURE = 0.7
AI_MAX_CONTEXT_MESSAGES = 20
AI_CONTEXT_CHAR_LIMIT = 12_000
# Native LLM function calling: "auto" (try native, fall back to
# heuristics), "true" (native required when the provider supports it),
# "false" (heuristics only).
AI_NATIVE_TOOLS = "auto"

# Conversation
CONVERSATION_MAX_HISTORY = 20

# Memory
MEMORY_PROVIDER = "local"
MEMORY_DATABASE_NAME = "memory.db"

# Voice
VOICE_SAMPLE_RATE = 16_000
VOICE_CHANNELS = 1
VOICE_BLOCK_SIZE = 1_024
VOICE_INPUT_ENGINE = "mock"
VOICE_OUTPUT_ENGINE = "mock"
VOICE_STT_ENGINE = "mock"
VOICE_STT_MODEL = "small"
VOICE_STT_DEVICE = "cpu"
VOICE_STT_COMPUTE_TYPE = "int8"
VOICE_STT_LANGUAGE = ""
VOICE_TTS_ENGINE = "mock"
VOICE_TTS_VOICE = "male-default"
VOICE_TTS_SAMPLE_RATE = 16_000
VOICE_SPEAKER_ENGINE = "mock"
VOICE_SPEAKER_MODEL = "speechbrain/spkrec-ecapa-voxceleb"
VOICE_SPEAKER_DEVICE = "cpu"
VOICE_SPEAKER_CONFIDENCE = 0.6
VOICE_SPEAKER_THRESHOLD = 0.6
VOICE_SPEAKER_METRIC = "cosine"
VOICE_WAKE_WORD = "hey asis"
VOICE_WAKE_ENGINE = "mock"
VOICE_WAKE_THRESHOLD = 0.5
VOICE_WAKE_MODEL = ""
VOICE_VAD_ENGINE = "mock"
VOICE_VAD_THRESHOLD = 0.5
VOICE_MAX_UTTERANCE_S = 15.0
VOICE_SILENCE_S = 0.8

# Network
NETWORK_TIMEOUT = 10
NETWORK_RETRIES = 3

# Tool execution
TOOL_TIMEOUT = 30
# Maximum validated native tool calls per assistant turn (1-10).
TOOL_MAX_CALLS_PER_TURN = 3

# Basic web access (optional capability; standalone by default)
WEB_ENABLED = True
WEB_SEARCH_PROVIDER = "duckduckgo"
WEB_TIMEOUT = 10
WEB_MAX_RESULTS = 5
WEB_MAX_CHARS = 8_000
WEB_MAX_RESPONSE_BYTES = 1_000_000
WEB_MAX_REDIRECTS = 3
WEB_MAX_QUERY_LENGTH = 500
WEB_MAX_URL_LENGTH = 2_000

# Translation engine (optional local capability; mock backend by default)
TRANSLATION_ENABLED = True
TRANSLATION_PROVIDER = "mock"
TRANSLATION_MODEL = "google/madlad400-3b-mt"
TRANSLATION_MODEL_PATH = ""
TRANSLATION_DEVICE = "cpu"
TRANSLATION_CACHE_ENABLED = True
TRANSLATION_CACHE_SIZE = 200
TRANSLATION_DEFAULT_SOURCE = "auto"
TRANSLATION_DEFAULT_TARGET = "en"
TRANSLATION_MAX_CHARS = 5_000

# Calculator engine (local deterministic mathematics, SymPy-backed)
CALCULATOR_ENABLED = True
CALCULATOR_MAX_EXPRESSION_CHARS = 2_000
CALCULATOR_MAX_MATRIX_SIZE = 10
CALCULATOR_TIMEOUT = 30
CALCULATOR_PRECISION = 10
CALCULATOR_ANGLE_MODE = "radians"

# Security / permissions
REQUIRE_CONFIRMATION_FOR_DANGEROUS = True

# Runtime
SHUTDOWN_TIMEOUT = 10

# C.O.R.E. integration (optional; standalone by default)
CORE_ENABLED = False
CORE_HOST = "127.0.0.1"
CORE_PORT = 5000
CORE_DEVICE_FILE = ""
CORE_CA_FILE = ""
CORE_INSECURE = False
CORE_CONNECT_TIMEOUT = 10
CORE_REQUEST_TIMEOUT = 30
CORE_RECONNECT_ENABLED = True
CORE_RECONNECT_DELAY = 5

# Assistant modes (A.S.C.S. is the coding mode of A.S.I.S.)
DEFAULT_MODE = "general"

# Coding workspace (A.S.C.S.)
CODING_WORKSPACE = ""
CODING_COMMAND_TIMEOUT = 120
CODING_MAX_FILE_SIZE = 200_000
CODING_MAX_OUTPUT_SIZE = 60_000
