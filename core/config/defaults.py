"""
Forza default configuration values.

These are safe built-in defaults only.
User-specific configuration and secrets must come from
environment variables or user configuration.
"""

# Application
APP_NAME = "Forza"
APP_VERSION = "2.0.0"

# Runtime
DEBUG = False
LOG_LEVEL = "INFO"

# AI
AI_PROVIDER = "ollama"
AI_MODEL = "qwen2.5:3b"
AI_ENDPOINT = "http://127.0.0.1:11434"

# AI behavior
AI_REQUEST_TIMEOUT = 120
AI_TEMPERATURE = 0.7
AI_MAX_CONTEXT_MESSAGES = 20

# Storage directory names
DATA_DIRECTORY_NAME = "data"
CONFIG_DIRECTORY_NAME = "config"
CACHE_DIRECTORY_NAME = "cache"
LOG_DIRECTORY_NAME = "logs"
MEMORY_DIRECTORY_NAME = "memory"

# Network
NETWORK_TIMEOUT = 10
NETWORK_RETRIES = 3

# Tool execution
TOOL_TIMEOUT = 30

# Security
REQUIRE_CONFIRMATION_FOR_DANGEROUS_TOOLS = True

# Runtime
SHUTDOWN_TIMEOUT = 10