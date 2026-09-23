"""End-to-end identity pipeline (§1, §56-58). import->persist->simulate->calibrate."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import analysis as A
from . import baseline as B
from . import exchanges as E
from . import modes as M
from . import timeline as T
from .matching import apply_incremental_update, match_identity
from .model import IdentityRecord, ModeDef
from .persona import build_persona, save_persona_version
from .store import IdentityStore
from .whatsapp import ConversationStore, import_export_file


def analyze_conversation(db_path: Path, export_path: str | Path,
                         store: IdentityStore,
                         conversation_id: str | None = None) -> dict[str, Any]:
    summary = import_export_file(db_path, export_path, conversation_id)
    cid = summary["conversation_id"]
    cstore = ConversationStore(db_path)
    messages = cstore.load_messages(cid)
    cstore.save_progress(cid, "exchanges", "", "", "started")
    exchanges = E.build_exchanges(messages)
    existing = store.list_all()
    # participant -> identity (match or create)
    mapping: dict[str, str] = {}
    for p in summary["participants"]:
        m = match_identity(p, existing, {"participants": summary["participants"]})
        if m.identity_id and not m.needs_confirmation:
            mapping[p] = m.identity_id
        else:
            ident = IdentityRecord(display_name=p, aliases=[p])
            store.save(ident, reason=f"import {cid}")
            existing.append(ident)
            mapping[p] = ident.identity_id
    # per-identity analysis (global + relationship-agnostic V1)
    for raw, iid in mapping.items():
        ident = store.get(iid)
        assert ident is not None
        base = B.compute_baseline(messages, raw)
        style = A.style_profile(messages, raw)
        interests = A.discover_interests(messages, raw)
        micro = [A.analyze_exchange(ex) for ex in exchanges]
        modes = M.discover_modes(base, style, micro)
        for name, md in modes.items():
            ident.modes[name] = ModeDef(mode_id=name, name=name,
                                        frequency=float(md.get("frequency", 1)),
                                        confidence=str(md.get("confidence", "LOW")))
        ident.mode_transitions = M.extract_transitions(micro)
        ident.timeline = T.build_timeline(messages)
        ident.global_profile = {"baseline": base, "style": style}
        apply_incremental_update(ident, {"aliases": [raw], "interests": interests,
                                         "vocabulary": dict(base.get("top_vocab", []))},
                                 source=cid)
        persona = build_persona(ident)
        save_persona_version(ident, persona, reason=f"analyze {cid}")
        store.save(ident, reason=f"analyze {cid}")
    cstore.save_progress(cid, "done", "", "", "done")
    first = store.get(next(iter(mapping.values()))) if mapping else None
    gaps = len(first.open_questions) if first else 0
    return {"conversation_id": cid, "messages": summary["messages"],
            "participants": summary["participants"], "mapping": mapping,
            "open_gaps": gaps, "status": "ok"}
