"""Detect and mask personally identifiable information.

Two outcomes, not one. A document with incidental personal data — an example
call written into a sales script — is masked and indexed with a flag. A document
whose substance *is* personal data, such as a lead export, is quarantined and
never indexed at all. A knowledge base that a voice agent retrieves from has no
legitimate need for customer records, so masking alone would be the wrong
answer there.

Name detection is deliberately conservative and context-driven. Detecting names
by shape alone would flag "Arogya First" and "Optima Secure" as people; the
false positives would corrupt the content. Limits are recorded in the report.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Fraction of tokens that must be personal data before a document is treated as
# a records export rather than prose with an example in it.
QUARANTINE_DENSITY = 0.02


@dataclass
class PIIFinding:
    kind: str
    count: int
    sample: str  # already masked; never the original value


@dataclass
class PIIResult:
    text: str
    findings: list[PIIFinding] = field(default_factory=list)
    quarantined: bool = False
    reason: str = ""

    @property
    def has_pii(self) -> bool:
        return bool(self.findings)

    @property
    def kinds(self) -> list[str]:
        return sorted({f.kind for f in self.findings})

    @property
    def total(self) -> int:
        return sum(f.count for f in self.findings)


# Patterns whose shape alone is decisive. A PAN has a fixed letter-digit
# structure and an email an unambiguous form, so neither needs context.
UNAMBIGUOUS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b")),
    ("PAN", re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")),
    ("LEAD_REF", re.compile(r"\bAF-\d{4}-\d{2}-\d{4,6}\b")),
    ("POLICY_NUMBER", re.compile(r"\bAF-[A-Z]-\d{6,}\b")),
    # An explicit country code makes a phone number unambiguous.
    ("PHONE", re.compile(r"\+91[\s-]?[6-9]\d{4}[\s-]?\d{5}\b")),
)

# Patterns whose shape is shared with ordinary data. A run of digit groups is a
# statistical table as often as it is an identifier, so a nearby cue word is
# required. Without this, premium tables in a policy report were being redacted
# as Aadhaar and phone numbers, destroying the figures.
CONTEXT_REQUIRED: tuple[tuple[str, re.Pattern[str], tuple[str, ...]], ...] = (
    (
        "AADHAAR",
        re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
        ("aadhaar", "aadhar", "uid", "uidai"),
    ),
    (
        "PHONE",
        re.compile(r"\b[6-9]\d{4}[\s-]?\d{5}\b"),
        ("phone", "mobile", "contact", "number", "call", "tel", "whatsapp", "reach", "cell"),
    ),
)

CONTEXT_WINDOW = 70

# Names are taken only where a cue word makes the person's role explicit.
# Honorifics alone are not enough: "Dr K Madan Gopal, Senior Consultant" in a
# report's acknowledgements and a regulator's chairman are published public
# figures, not customer data, and masking them corrupts the content.
# The case-insensitive flag is scoped to the cue words only. Applied to the
# whole pattern it would make the capitalised name shape case-insensitive too,
# and ordinary lowercase words would start matching as names.
NAME_CUES = re.compile(
    r"\b(?i:caller|customer|insured|agent|advisor|policyholder|lead\s+name|name)\s*[:\-]?\s+"
    r"((?:Mr|Mrs|Ms|Dr|Shri|Smt)\.?\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b"
)


def _mask_token(kind: str) -> str:
    return f"[{kind}_REDACTED]"


def _has_cue(text: str, start: int, cues: tuple[str, ...]) -> bool:
    window = text[max(0, start - CONTEXT_WINDOW) : start].lower()
    return any(cue in window for cue in cues)


def scan_and_mask(text: str) -> PIIResult:
    findings: list[PIIFinding] = []
    masked = text

    for kind, pattern in UNAMBIGUOUS:
        matches = pattern.findall(masked)
        if matches:
            findings.append(PIIFinding(kind=kind, count=len(matches), sample=_mask_token(kind)))
            masked = pattern.sub(_mask_token(kind), masked)

    for kind, pattern, cues in CONTEXT_REQUIRED:
        count = 0

        def replace(match: re.Match[str], _kind=kind, _cues=cues) -> str:
            nonlocal count
            if not _has_cue(match.string, match.start(), _cues):
                return match.group(0)
            count += 1
            return _mask_token(_kind)

        masked = pattern.sub(replace, masked)
        if count:
            existing = next((f for f in findings if f.kind == kind), None)
            if existing is not None:
                existing.count += count
            else:
                findings.append(
                    PIIFinding(kind=kind, count=count, sample=_mask_token(kind))
                )

    name_count = len(NAME_CUES.findall(masked))
    if name_count:
        # Replace only the captured name, keeping the cue word and honorific so
        # the surrounding sentence still reads correctly.
        masked = NAME_CUES.sub(
            lambda m: m.group(0).replace(m.group(2), _mask_token("NAME")), masked
        )
        findings.append(PIIFinding(kind="NAME", count=name_count, sample=_mask_token("NAME")))

    result = PIIResult(text=masked, findings=findings)

    words = max(len(text.split()), 1)
    density = result.total / words
    if density >= QUARANTINE_DENSITY:
        result.quarantined = True
        result.reason = (
            f"{result.total} personal-data matches across {words} words "
            f"({density:.1%}) — treated as a records export, not reference content"
        )

    return result


def csv_to_text(raw: str) -> str:
    """Render a CSV as labelled lines so detectors see values in context."""
    lines = raw.strip().splitlines()
    if not lines:
        return ""
    header = [h.strip() for h in lines[0].split(",")]
    out = []
    for line in lines[1:]:
        cells = [c.strip() for c in line.split(",")]
        out.append("; ".join(f"{h}: {c}" for h, c in zip(header, cells, strict=False) if c))
    return "\n".join(out)
