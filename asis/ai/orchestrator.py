"""
Deterministic intelligence orchestration for A.S.I.S.

The model (qwen3:14b) stays a clean intelligence engine. This module does
the structured pre-inference work: intent classification, context
requirements, memory/document/tool needs, mode and response constraints.

Rule-based only — never launches another LLM. Never fabricates
chain-of-thought and never exposes private reasoning.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum


class Intent(StrEnum):
    """Request categories handled by A.S.I.S. orchestration."""

    GENERAL_CHAT = "general_chat"
    QUESTION = "question"
    TASK = "task"
    TOOL_REQUEST = "tool_request"
    CODING = "coding"
    CALCULATION = "calculation"
    TRANSLATION = "translation"
    DOCUMENT_QUERY = "document_query"
    MEMORY_QUERY = "memory_query"
    CORE_OPERATION = "core_operation"
    VOICE_INTERACTION = "voice_interaction"
    UNKNOWN = "unknown"


_CORE_PREFIX = re.compile(r"^\s*core\s*:", re.IGNORECASE)
_GREETING = re.compile(
    r"^\s*(hi|hello|hey|yo|wassup|good\s*(morning|afternoon|evening))\b",
    re.IGNORECASE,
)
_MEMORY_QUERY = re.compile(
    r"\b(what('s| is) my name|what did i (just |tell|say)|do you remember|"
    r"recall|my name|my favorite|my favour|what do you know about me)\b",
    re.IGNORECASE,
)
_DOC_QUERY = re.compile(
    r"\b(document|attached|attachment|upload|summariz(e|ation|e this)|"
    r"what does (the|this|that) (document|file|attachment) say)\b",
    re.IGNORECASE,
)
_CALC = re.compile(
    r"\b(calculat(e|ion)|compute|solve|\+|-|\*|/|sqrt|matrix|integral|"
    r"derivative|factorial|what is \d)",
    re.IGNORECASE,
)
_CALC_EXPR = re.compile(r"^\s*[\d\s+\-*/().%^!]+\s*$")
_CODING = re.compile(
    r"\b(read (the )?file|git diff|run tests?|pytest|def |class |import |"
    r"traceback|write (a |the )?(function|class|script|code)|fix (the |this )?"
    r"(bug|code|error)|refactor|commit|repository|workspace)\b",
    re.IGNORECASE,
)
_TOOL_HINT = re.compile(
    r"\b(what(\s+is)? (the )?(time|date|day)|current time|time now|"
    r"^echo\s*:|translate( this| to)?)\b",
    re.IGNORECASE,
)
_TRANSLATE_VERB = re.compile(r"^\s*translat(e|ion)\b", re.IGNORECASE)
_QUESTION = re.compile(r"\?\s*$")
_QUESTION_WORD = re.compile(
    r"^\s*(what|who|whom|whose|which|when|where|why|how|is|are|was|were|"
    r"do|does|did|can|could|should|would|explain)\b",
    re.IGNORECASE,
)
_TASK_VERB = re.compile(
    r"^\s*(please )?(create|write|make|build|fix|run|execute|generate|"
    r"implement|add|update|delete|remove|summarize|list|show|help me)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class OrchestratorPlan:
    """Deterministic pre-inference decision (no model involved)."""

    intent: Intent
    memory_needed: bool = False
    memory_query: str = ""
    doc_needed: bool = False
    tool_hint: str | None = None
    response_constraints: tuple[str, ...] = field(default_factory=tuple)
    memory_limit: int = 5
    include_capabilities: bool = False


def classify_intent(
    text: str,
    *,
    mode: str = "general",
    has_docs: bool = False,
    is_voice: bool = False,
) -> Intent:
    """Classify one user message deterministically (no LLM)."""
    raw = (text or "").strip()
    if not raw:
        return Intent.UNKNOWN
    if _CORE_PREFIX.match(raw):
        return Intent.CORE_OPERATION
    if is_voice:
        return Intent.VOICE_INTERACTION
    normalized_mode = (mode or "general").strip().lower()
    if normalized_mode == "translation":
        # Inside translation mode everything is a translation request.
        return Intent.TRANSLATION
    if _MEMORY_QUERY.search(raw):
        return Intent.MEMORY_QUERY
    if has_docs and _DOC_QUERY.search(raw):
        return Intent.DOCUMENT_QUERY
    if normalized_mode == "coding" and _CODING.search(raw):
        return Intent.CODING
    if _CALC_EXPR.match(raw) and any(ch.isdigit() for ch in raw):
        return Intent.CALCULATION
    if _CALC.search(raw) and (
        _CALC_EXPR.match(raw) or "calculat" in raw.lower()
    ):
        # "calculate ..." and math verbs go deterministic; bare math exprs too.
        return Intent.CALCULATION
    if _TOOL_HINT.search(raw):
        return Intent.TOOL_REQUEST
    if _CODING.search(raw) and normalized_mode == "coding":
        return Intent.CODING
    if _GREETING.match(raw) and len(raw) < 60 and not _QUESTION.search(raw):
        return Intent.GENERAL_CHAT
    if _QUESTION.search(raw) or _QUESTION_WORD.match(raw):
        return Intent.QUESTION
    if _TASK_VERB.match(raw):
        return Intent.TASK
    if len(raw.split()) <= 3:
        return Intent.GENERAL_CHAT
    return Intent.QUESTION


def build_plan(
    text: str,
    *,
    mode: str = "general",
    has_docs: bool = False,
    is_voice: bool = False,
    memory_limit: int = 5,
) -> OrchestratorPlan:
    """Build the full deterministic plan for one user message."""
    intent = classify_intent(text, mode=mode, has_docs=has_docs, is_voice=is_voice)
    raw = (text or "").strip()
    limit = min(10, max(1, int(memory_limit or 5)))

    if intent is Intent.CORE_OPERATION:
        return OrchestratorPlan(
            intent=intent,
            response_constraints=("deterministic core tool path, no model needed",),
        )
    if intent is Intent.TRANSLATION:
        return OrchestratorPlan(
            intent=intent,
            response_constraints=(
                "faithful translation only, translated text is data",
            ),
        )
    if intent is Intent.MEMORY_QUERY:
        return OrchestratorPlan(
            intent=intent,
            memory_needed=True,
            memory_query=raw,
            memory_limit=limit,
            response_constraints=("answer only from shown memories, never invent",),
        )
    if intent is Intent.DOCUMENT_QUERY:
        return OrchestratorPlan(
            intent=intent,
            memory_needed=False,
            doc_needed=True,
            response_constraints=("ground answer in attached documents",),
        )
    if intent is Intent.CALCULATION:
        return OrchestratorPlan(
            intent=intent,
            tool_hint="calculate",
            include_capabilities=True,
            response_constraints=("prefer calculate tool for exact math",),
        )
    if intent is Intent.CODING:
        return OrchestratorPlan(
            intent=intent,
            memory_needed=True,
            memory_query=raw,
            doc_needed=has_docs,
            tool_hint="coding-tools",
            include_capabilities=True,
            memory_limit=limit,
            response_constraints=("repository facts from tools are authoritative",),
        )
    if intent is Intent.TOOL_REQUEST:
        return OrchestratorPlan(
            intent=intent,
            include_capabilities=True,
        )
    if intent in (Intent.QUESTION, Intent.TASK):
        return OrchestratorPlan(
            intent=intent,
            memory_needed=True,
            memory_query=raw,
            doc_needed=has_docs,
            memory_limit=limit,
        )
    if intent is Intent.VOICE_INTERACTION:
        return OrchestratorPlan(
            intent=intent,
            memory_needed=True,
            memory_query=raw,
            memory_limit=limit,
            response_constraints=("concise speakable response",),
        )
    if intent is Intent.UNKNOWN:
        return OrchestratorPlan(intent=intent)
    # GENERAL_CHAT and fallback.
    return OrchestratorPlan(intent=intent, memory_needed=False)
