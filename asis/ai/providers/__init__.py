"""
A.S.I.S. AI providers.

``OllamaProvider`` is lazy: importing this package never requires
``requests`` (base install). The Ollama module is imported on first
attribute access; without the ``ai`` extra that raises an ImportError
naming the missing dependency.
"""

from __future__ import annotations

from typing import Any

from .base import AIProvider
from .mock import MockAIProvider

__all__ = ["AIProvider", "MockAIProvider", "OllamaProvider"]


def __getattr__(name: str) -> Any:
    if name == "OllamaProvider":
        try:
            from .ollama import OllamaProvider
        except ImportError as exc:
            raise ImportError(
                "OllamaProvider requires the 'requests' package "
                "(pip install -e '.[ai]')."
            ) from exc
        globals()[name] = OllamaProvider
        return OllamaProvider
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
