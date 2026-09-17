"""
Ollama AI provider for A.S.I.S.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Sequence
from typing import Any

import requests

from asis.configuration.defaults import AI_MODEL as DEFAULT_OLLAMA_MODEL
from asis.errors import InferenceError

from ..models import AIMessage, AIResponse, NativeToolCall
from .base import AIProvider

# Upper bound for the implicit availability probe so a down/unreachable
# server is reported fast. Inference timeouts are unaffected; callers may
# still pass an explicit ``timeout`` to ``available()``.
AVAILABILITY_PROBE_TIMEOUT = 5.0


class OllamaProvider(AIProvider):
    """AI provider backed by a local Ollama server."""

    def __init__(
        self,
        model: str = DEFAULT_OLLAMA_MODEL,
        host: str = "http://127.0.0.1:11434",
        timeout: float = 120.0,
        temperature: float | None = None,
        request_timeout: float | None = None,
        retries: int = 0,
    ) -> None:
        self._model = model
        self.host = host.rstrip("/")
        # Explicit timeout wins; request_timeout mirrors settings naming.
        self.timeout = timeout if request_timeout is None else request_timeout
        self.temperature = temperature
        self.retries = max(0, int(retries))

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def model(self) -> str:
        return self._model

    def available(self, timeout: float | None = None) -> bool:
        """Return True when the Ollama server is reachable.

        The implicit probe is capped at ``AVAILABILITY_PROBE_TIMEOUT``
        seconds so offline/down servers report fast instead of blocking
        on the (long) inference timeout.
        """
        if timeout is None:
            probe = min(float(self.timeout), AVAILABILITY_PROBE_TIMEOUT)
        else:
            probe = timeout
        try:
            response = requests.get(
                f"{self.host}/api/tags",
                timeout=probe,
            )
            return response.ok

        except requests.RequestException:
            return False

    def _payload(
        self,
        messages: Sequence[AIMessage],
        *,
        stream: bool,
        tools: Sequence[dict] | None = None,
    ) -> dict:
        payload: dict = {
            "model": self._model,
            "messages": [
                {
                    "role": message.role.value,
                    "content": message.content,
                }
                for message in messages
            ],
            "stream": stream,
        }
        if self.temperature is not None:
            payload["options"] = {"temperature": self.temperature}
        if tools:
            payload["tools"] = list(tools)
        return payload

    def _communication_error(self, exc: Exception) -> InferenceError:
        return InferenceError(f"Could not communicate with Ollama: {exc}")

    def chat(
        self,
        messages: Sequence[AIMessage],
    ) -> AIResponse:
        """Send a non-streaming chat request (retried per configuration)."""
        attempts = 1 + self.retries
        for attempt in range(attempts):
            try:
                response = requests.post(
                    f"{self.host}/api/chat",
                    json=self._payload(messages, stream=False),
                    timeout=self.timeout,
                )
                response.raise_for_status()
                break
            except requests.RequestException as exc:
                if attempt + 1 >= attempts:
                    raise self._communication_error(exc) from exc

        data = response.json()
        content = (data.get("message") or {}).get("content")

        if not isinstance(content, str):
            raise InferenceError("Ollama returned an invalid response.")

        return AIResponse(
            content=content,
            model=self._model,
            provider=self.name,
            metadata={
                "done": data.get("done"),
                "total_duration": data.get("total_duration"),
                "prompt_eval_count": data.get("prompt_eval_count"),
                "eval_count": data.get("eval_count"),
            },
        )

    @property
    def supports_native_tools(self) -> bool:
        """Ollama's /api/chat accepts a tools array (model-dependent)."""
        return True

    @staticmethod
    def parse_tool_calls(message: dict) -> tuple[NativeToolCall, ...]:
        """Extract valid native calls; drop malformed entries safely."""
        raw_calls = message.get("tool_calls") or []
        if not isinstance(raw_calls, list):
            return ()
        parsed: list[NativeToolCall] = []
        for entry in raw_calls:
            if not isinstance(entry, dict):
                continue
            function = entry.get("function")
            if not isinstance(function, dict):
                continue
            name = function.get("name")
            arguments = function.get("arguments", {})
            if arguments is None:
                arguments = {}
            if not isinstance(name, str) or not name.strip():
                continue
            if not isinstance(arguments, dict):
                continue
            try:
                parsed.append(
                    NativeToolCall(name=name.strip(), arguments=dict(arguments))
                )
            except TypeError:
                continue
        return tuple(parsed)

    def chat_with_tools(
        self,
        messages: Sequence[AIMessage],
        tools: Sequence[Any],
    ) -> AIResponse:
        """Send a non-streaming chat request with tool definitions."""
        from asis.ai.tool_schemas import ollama_tools

        wire = ollama_tools(list(tools))
        attempts = 1 + self.retries
        for attempt in range(attempts):
            try:
                response = requests.post(
                    f"{self.host}/api/chat",
                    json=self._payload(messages, stream=False, tools=wire),
                    timeout=self.timeout,
                )
                response.raise_for_status()
                break
            except requests.RequestException as exc:
                if attempt + 1 >= attempts:
                    raise self._communication_error(exc) from exc

        data = response.json()
        message = data.get("message") or {}
        content = message.get("content")
        if content is None:
            content = ""
        if not isinstance(content, str):
            raise InferenceError("Ollama returned an invalid response.")

        return AIResponse(
            content=content,
            model=self._model,
            provider=self.name,
            metadata={
                "done": data.get("done"),
                "total_duration": data.get("total_duration"),
                "prompt_eval_count": data.get("prompt_eval_count"),
                "eval_count": data.get("eval_count"),
                "native_tools": True,
            },
            tool_calls=self.parse_tool_calls(message),
        )

    def stream_chat(
        self,
        messages: Sequence[AIMessage],
    ) -> Iterator[str]:
        """
        Stream generated text from Ollama.

        Each yielded value is a newly generated text chunk.

        KeyboardInterrupt is intentionally allowed to propagate to the
        caller so Ctrl+C can interrupt the current response.
        """
        response: requests.Response | None = None

        try:
            response = requests.post(
                f"{self.host}/api/chat",
                json=self._payload(messages, stream=True),
                stream=True,
                timeout=self.timeout,
            )
            response.raise_for_status()

            for line in response.iter_lines(
                decode_unicode=True,
            ):
                if not line:
                    continue

                try:
                    data = json.loads(line)

                except json.JSONDecodeError as exc:
                    raise InferenceError(
                        "Ollama returned invalid streaming data."
                    ) from exc

                content = (data.get("message") or {}).get("content", "")

                if content:
                    yield content

                if data.get("done"):
                    break

        except requests.RequestException as exc:
            raise self._communication_error(exc) from exc

        finally:
            if response is not None:
                response.close()
