"""Bounded local document parsers (stdlib-first, optional extras)."""

from __future__ import annotations

import csv
import json
import re
import zipfile
from pathlib import Path

SUPPORTED_SUFFIXES = frozenset({".txt", ".md", ".pdf", ".docx", ".csv", ".json"})

MAX_CHARS_PER_FILE = 20_000


def _clean(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = "".join(ch for ch in text if ch == "\n" or ch == "\t" or ord(ch) >= 32)
    return text.strip()[:MAX_CHARS_PER_FILE]


def _parse_txt(path: Path) -> str:
    return _clean(path.read_text(encoding="utf-8", errors="replace"))


def _parse_json(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return _clean(raw)
    return _clean(json.dumps(data, indent=2, ensure_ascii=False))


def _parse_csv(path: Path) -> str:
    lines: list[str] = []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as fh:
        for row in csv.reader(fh):
            lines.append(" | ".join(cell.strip() for cell in row))
            if sum(len(line) for line in lines) > MAX_CHARS_PER_FILE:
                break
    return _clean("\n".join(lines))


def _parse_pdf(path: Path) -> str:
    # Prefer pypdf when installed (optional extra), else best-effort.
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(str(path))
        parts = [(page.extract_text() or "") for page in reader.pages]
        text = "\n".join(parts)
        if text.strip():
            return _clean(text)
    except Exception:
        pass
    try:
        import re as _re

        data = path.read_bytes()
        # Best-effort: printable runs inside the binary stream.
        runs = _re.findall(rb"[ -~]{8,}", data)
        text = "\n".join(r.decode("ascii", errors="ignore") for r in runs)
        return _clean(text)
    except Exception:
        return ""


def _parse_docx(path: Path) -> str:
    try:
        from docx import Document  # type: ignore

        doc = Document(str(path))
        return _clean("\n".join(p.text for p in doc.paragraphs))
    except Exception:
        pass
    try:
        with zipfile.ZipFile(path) as zf:
            xml = zf.read("word/document.xml").decode("utf-8", errors="replace")
        xml = re.sub(r"<w:p[^>]*>", "\n", xml)
        xml = re.sub(r"<[^>]+>", "", xml)
        import html as _html

        return _clean(_html.unescape(xml))
    except Exception:
        return ""


def parse_file(path: str | Path) -> str:
    """Parse a supported file into bounded normalized text.

    Raises FileNotFoundError / ValueError (unsupported suffix).
    Never touches the network.
    """
    resolved = Path(path).expanduser()
    if not resolved.is_file():
        raise FileNotFoundError(f"file not found: {path}")
    suffix = resolved.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(f"unsupported file type: {suffix or '(none)'}")
    if suffix in {".txt", ".md"}:
        return _parse_txt(resolved)
    if suffix == ".json":
        return _parse_json(resolved)
    if suffix == ".csv":
        return _parse_csv(resolved)
    if suffix == ".pdf":
        return _parse_pdf(resolved)
    if suffix == ".docx":
        return _parse_docx(resolved)
    raise ValueError(f"unsupported file type: {suffix}")
