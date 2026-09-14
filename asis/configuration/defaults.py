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

# Network
NETWORK_TIMEOUT = 10
NETWORK_RETRIES = 3

# Tool execution
TOOL_TIMEOUT = 30

# Security / permissions
REQUIRE_CONFIRMATION_FOR_DANGEROUS = True

# Runtime
SHUTDOWN_TIMEOUT = 10
