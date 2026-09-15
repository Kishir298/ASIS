"""
A.S.I.S. AI subsystem.
"""

from .context import ContextAssembler
from .conversation import ConversationSession
from .inference import InferenceEngine
from .manager import AIManager, create_provider
from .models import AIMessage, AIResponse, MessageRole, NativeToolCall
from .providers import AIProvider, MockAIProvider, OllamaProvider
from .tool_schemas import (
    ToolDefinition,
    ollama_tools,
    tool_definition_for,
    tool_definitions_for,
    validate_call_arguments,
)

__all__ = [
    "AIManager",
    "create_provider",
    "AIMessage",
    "AIResponse",
    "MessageRole",
    "NativeToolCall",
    "AIProvider",
    "MockAIProvider",
    "OllamaProvider",
    "ConversationSession",
    "ContextAssembler",
    "InferenceEngine",
    "ToolDefinition",
    "ollama_tools",
    "tool_definition_for",
    "tool_definitions_for",
    "validate_call_arguments",
]
