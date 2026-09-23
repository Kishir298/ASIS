"""A.S.I.S. persistent identity reconstruction + simulation subsystem.

Real system: parsers, pipeline, storage, retrieval, modes, persona,
calibration, questions, CLI. No mega-prompt. See docs/identity.md.
"""

from .model import IdentityRecord, Provenance, MemoryClass
from .whatsapp import WhatsAppMessage, parse_whatsapp_export
from .matching import match_identity, MatchResult

__all__ = [
    "IdentityRecord",
    "Provenance",
    "MemoryClass",
    "WhatsAppMessage",
    "parse_whatsapp_export",
    "match_identity",
    "MatchResult",
]
