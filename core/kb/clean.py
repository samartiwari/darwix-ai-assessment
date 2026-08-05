"""Strip chrome and normalize whitespace from extracted text.

This stage is line-level and conservative: it removes what is provably
navigation or legal furniture and leaves everything else alone. Terminology,
date and currency normalization happen later, once records exist.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from core.kb.extract import BOILERPLATE_LINES

# Lines matching these outright are furniture, not content.
DROP_PATTERNS = (
    re.compile(r"^\s*$"),
    re.compile(r"^[\W_]+$"),  # rules, bullet glyphs, separators
    re.compile(r"^(?:home|menu|search|close|next|previous|back)\s*$", re.I),
    re.compile(r"^\d{1,3}\s*$"),  # stray page numbers
    re.compile(r"©|\ball rights reserved\b", re.I),
    re.compile(r"^\s*(?:irdai|isnp)\s+registration\s+n[o0]", re.I),
    re.compile(r"\b(?:cin|uin|gstin)\s*[:\-]", re.I),
    re.compile(r"^\s*(?:follow|share|connect)\s+(?:us|this)\b", re.I),
    re.compile(r"^\s*(?:toll[\s-]?free|call\s+to\s+buy|whatsapp)\b", re.I),
    re.compile(r"^\s*(?:download|get)\s+(?:the\s+)?app\b", re.I),
    re.compile(r"\bcookies?\b.*\b(?:accept|consent|policy)\b", re.I),
    re.compile(r"^\s*(?:english|हिंदी|தமிழ்|తెలుగు|বাংলা|मराठी)\s*$"),
)

# Wikipedia editorial furniture that is not part of the article's substance.
WIKI_PATTERNS = (
    re.compile(r"^\s*(?:edit|citation needed|jump to|retrieved from)\b", re.I),
    re.compile(r"^\s*\[\d+\]\s*$"),
    re.compile(r"^\s*(?:see also|references|external links|further reading|notes)\s*$", re.I),
)

# Calls to action and marketing furniture. Present on product pages, never an
# answer to a customer question.
CTA_PATTERNS = (
    re.compile(r"^\s*(?:start|begin|get|buy|renew|explore|discover|compare|check)\b.{0,60}$", re.I),
    re.compile(r"\b(?:rated|awarded|ranked)\s+(?:by|as|#)\b", re.I),
    re.compile(r"\b(?:t&c|terms)\s*(?:apply|\*)", re.I),
    re.compile(r"^\s*(?:quick|useful|important|related|popular)\s+(?:links|searches|articles|reads)\s*$", re.I),
    re.compile(r"^\s*(?:with|at)\s+(?:[\w&]+\s+){0,3}(?:today|now)!?\s*$", re.I),
    re.compile(r"^\s*\*+\s*$"),
)

# A run of this many consecutive short, unpunctuated lines is a navigation or
# link block. One such line on its own is usually a heading, which chunking
# needs, so the threshold matters.
NAV_RUN_THRESHOLD = 3
NAV_LINE_MAX_WORDS = 8


@dataclass
class CleanResult:
    text: str
    lines_in: int
    lines_out: int

    @property
    def lines_dropped(self) -> int:
        return self.lines_in - self.lines_out


def _is_navish(line: str) -> bool:
    """Short, unpunctuated, not a table row — the shape of a link label."""
    stripped = line.strip()
    if not stripped or stripped.startswith("|"):
        return False
    words = stripped.split()
    if len(words) > NAV_LINE_MAX_WORDS:
        return False
    return not re.search(r"[.!?:;]$", stripped)


def _drop_nav_runs(lines: list[str]) -> list[str]:
    """Remove runs of consecutive link-shaped lines, keeping isolated headings."""
    out: list[str] = []
    run: list[str] = []

    def flush() -> None:
        if len(run) < NAV_RUN_THRESHOLD:
            out.extend(run)
        run.clear()

    for line in lines:
        if _is_navish(line):
            run.append(line)
        else:
            flush()
            out.append(line)
    flush()
    return out


def _is_chrome(line: str) -> bool:
    stripped = line.strip()
    if stripped.startswith("|"):
        return False  # table rows are content, whatever their shape
    if any(p.search(stripped) for p in DROP_PATTERNS):
        return True
    if any(p.search(stripped) for p in WIKI_PATTERNS):
        return True
    if any(p.search(stripped) for p in CTA_PATTERNS):
        return True

    lowered = stripped.lower()
    # Short lines that exactly match known chrome. Length matters: a sentence
    # discussing a claim is content, the word "Claim" in a nav bar is not.
    if len(stripped.split()) <= 5 and any(b == lowered or b in lowered for b in BOILERPLATE_LINES):
        return True
    return False


def _collapse_repeats(lines: list[str]) -> list[str]:
    """Drop consecutive duplicate lines, common in menu blocks."""
    out: list[str] = []
    for line in lines:
        if out and line.strip().lower() == out[-1].strip().lower():
            continue
        out.append(line)
    return out


def clean_text(text: str, source_type: str = "web_page") -> CleanResult:
    """Clean extracted text.

    Navigation-run removal applies to web pages only. PDF text extraction
    returns naturally short lines, so the same heuristic there deletes genuine
    report prose — measured at roughly a quarter of a 64-page document.
    """
    raw_lines = text.splitlines()
    kept = [ln for ln in raw_lines if not _is_chrome(ln)]
    kept = _collapse_repeats(kept)
    if source_type == "web_page":
        kept = _drop_nav_runs(kept)

    # Rejoin, normalizing intra-line whitespace but preserving paragraph breaks.
    normalized = [re.sub(r"[ \t ]+", " ", ln).strip() for ln in kept]
    body = "\n".join(normalized)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()

    return CleanResult(text=body, lines_in=len(raw_lines), lines_out=len(normalized))


def drop_repeated_across_documents(
    docs: dict[str, str], min_documents: int = 3
) -> tuple[dict[str, str], list[str]]:
    """Remove lines that recur across documents from the same site.

    A header or footer is not identifiable from one page. Seen on most pages of
    a site, it is unmistakable. This runs after all documents are cleaned
    individually.
    """
    counts: dict[str, int] = {}
    for text in docs.values():
        for line in {ln.strip() for ln in text.splitlines() if len(ln.split()) <= 12}:
            if line:
                counts[line] = counts.get(line, 0) + 1

    repeated = {line for line, n in counts.items() if n >= min_documents}
    if not repeated:
        return docs, []

    trimmed = {
        url: "\n".join(ln for ln in text.splitlines() if ln.strip() not in repeated)
        for url, text in docs.items()
    }
    return trimmed, sorted(repeated)
