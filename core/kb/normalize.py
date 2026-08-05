"""Standardize terminology, dates, currency and headings.

Sources disagree with each other. The brochure says "cover amount", the FAQ
sheet says "coverage limit", the industry says "sum insured"; dates arrive as
01/04/2025, April 1, 2025, 15-03-2025 and 2025-04-01 in four documents written
by the same team. Retrieval degrades when the same concept is spelled three
ways, so a canonical form is chosen and applied.

Substitutions are recorded rather than applied silently, so the report can show
what was changed and a reviewer can disagree with a choice.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

# Canonical term -> variants seen in the sources. Longest variants first so that
# "pre-existing disease waiting period" is not half-consumed by a shorter rule.
TERMINOLOGY: dict[str, tuple[str, ...]] = {
    "sum insured": ("cover amount", "coverage limit", "cover limit", "sum assured"),
    "waiting period": ("cooling period", "cool-off period", "waiting-period"),
    "pre-existing disease": (
        "pre existing disease",
        "pre-existing condition",
        "preexisting disease",
        "PED",
    ),
    "co-payment": ("co payment", "copayment", "co-pay", "copay"),
    "no claim bonus": ("no-claim bonus", "NCB", "cumulative bonus"),
    "cashless": ("cash-less", "cash less"),
    "premium": ("policy cost", "policy price"),
    "policy year": ("policy-year",),
}

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12, "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}


@dataclass
class NormalizeResult:
    text: str
    term_changes: Counter = field(default_factory=Counter)
    date_changes: int = 0
    currency_changes: int = 0

    @property
    def total_changes(self) -> int:
        return sum(self.term_changes.values()) + self.date_changes + self.currency_changes


def _normalize_terms(text: str) -> tuple[str, Counter]:
    changes: Counter = Counter()
    for canonical, variants in TERMINOLOGY.items():
        for variant in sorted(variants, key=len, reverse=True):
            # Case-insensitive, whole-token, and the replacement preserves
            # sentence capitalisation where the variant began a sentence.
            pattern = re.compile(rf"(?<![\w-]){re.escape(variant)}(?![\w-])", re.I)

            def replace(match: re.Match[str], canon=canonical) -> str:
                original = match.group(0)
                if original.isupper() and len(original) > 3:
                    return canon.upper()
                if original[:1].isupper():
                    return canon[:1].upper() + canon[1:]
                return canon

            text, count = pattern.subn(replace, text)
            if count:
                changes[f"{variant} -> {canonical}"] += count
    return text, changes


def _iso(year: int, month: int, day: int) -> str | None:
    if not (1 <= month <= 12 and 1 <= day <= 31 and 1900 <= year <= 2100):
        return None
    return f"{year:04d}-{month:02d}-{day:02d}"


def _normalize_dates(text: str) -> tuple[str, int]:
    count = 0

    # 01/04/2025 and 15-03-2025. Indian convention is day first, which is the
    # documented assumption; an ambiguous 03/04 is read as 3 April.
    def numeric(match: re.Match[str]) -> str:
        nonlocal count
        day, month, year = (int(g) for g in match.groups())
        if year < 100:
            year += 2000
        iso = _iso(year, month, day)
        if iso is None:
            return match.group(0)
        count += 1
        return iso

    text = re.sub(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b", numeric, text)

    # April 1, 2025 and 1 April 2025
    def named(match: re.Match[str]) -> str:
        nonlocal count
        groups = match.groupdict()
        month = MONTHS.get((groups.get("month") or "").lower())
        if month is None:
            return match.group(0)
        iso = _iso(int(groups["year"]), month, int(groups["day"]))
        if iso is None:
            return match.group(0)
        count += 1
        return iso

    text = re.sub(
        r"\b(?P<month>[A-Za-z]{3,9})\s+(?P<day>\d{1,2}),?\s+(?P<year>\d{4})\b", named, text
    )
    text = re.sub(
        r"\b(?P<day>\d{1,2})\s+(?P<month>[A-Za-z]{3,9})\s+(?P<year>\d{4})\b", named, text
    )
    return text, count


def _normalize_currency(text: str) -> tuple[str, int]:
    """Express amounts as 'Rs <digits>' so lexical search can match them.

    Lakh and crore are expanded because a caller asking about "ten lakh cover"
    and a document written as "Rs 10,00,000" must reach each other.
    """
    count = 0

    def lakh_crore(match: re.Match[str]) -> str:
        nonlocal count
        amount = float(match.group("amount").replace(",", ""))
        unit = match.group("unit").lower()
        multiplier = 10_000_000 if unit.startswith("cr") else 100_000
        count += 1
        value = int(amount * multiplier)
        # Both forms are kept: the spoken form matches speech, the numeric form
        # matches documents.
        return f"Rs {value:,} ({match.group('amount')} {unit})"

    text = re.sub(
        r"(?:Rs\.?|INR|₹)?\s*(?P<amount>\d+(?:\.\d+)?)\s*(?P<unit>lakhs?|lacs?|crores?|cr)\b",
        lakh_crore,
        text,
        flags=re.I,
    )

    text, n = re.subn(r"₹\s*(\d)", r"Rs \1", text)
    count += n
    text, n = re.subn(r"\bINR\s*(\d)", r"Rs \1", text)
    count += n
    text, n = re.subn(r"\bRs\.\s*(\d)", r"Rs \1", text)
    count += n
    return text, count


def _normalize_headings(text: str) -> str:
    """Give markdown headings consistent spacing and drop trailing colons."""
    out = []
    for line in text.splitlines():
        match = re.match(r"^(#{1,6})\s*(.+?)\s*:?\s*$", line)
        out.append(f"{match.group(1)} {match.group(2)}" if match else line)
    return "\n".join(out)


def normalize(text: str) -> NormalizeResult:
    text = _normalize_headings(text)
    text, terms = _normalize_terms(text)
    text, dates = _normalize_dates(text)
    text, currency = _normalize_currency(text)
    return NormalizeResult(
        text=text, term_changes=terms, date_changes=dates, currency_changes=currency
    )
