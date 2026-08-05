"""Find exact duplicates, near-duplicates and numeric contradictions.

Works on (id, text) pairs so the same code serves whole documents and, later,
individual chunks. Near-duplicate detection uses MinHash over word shingles,
which finds passages that were reworded rather than copied — the usual case when
the same fact appears in a brochure and an FAQ sheet.

Contradictions are reported, never resolved. Two sources stating a 24 month and
a 36 month waiting period is a source error a person must settle; picking one
silently would bury it.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

from datasketch import MinHash, MinHashLSH

SHINGLE_SIZE = 5
NEAR_DUPLICATE_THRESHOLD = 0.85
MINHASH_PERMUTATIONS = 128


@dataclass
class DuplicatePair:
    kept: str
    dropped: str
    similarity: float
    kind: str  # exact | near


@dataclass
class Contradiction:
    topic: str
    values: list[str]
    sources: list[str]

    def describe(self) -> str:
        pairs = ", ".join(f"{v} ({s})" for v, s in zip(self.values, self.sources, strict=False))
        return f"{self.topic}: {pairs}"


@dataclass
class DedupeResult:
    keep: list[str] = field(default_factory=list)
    pairs: list[DuplicatePair] = field(default_factory=list)
    contradictions: list[Contradiction] = field(default_factory=list)

    @property
    def dropped_ids(self) -> set[str]:
        return {p.dropped for p in self.pairs}


def _canonical(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", re.sub(r"\s+", " ", text.lower())).strip()


def _fingerprint(text: str) -> str:
    return hashlib.sha256(_canonical(text).encode()).hexdigest()


def _shingles(text: str, size: int = SHINGLE_SIZE) -> set[str]:
    words = _canonical(text).split()
    if len(words) < size:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i : i + size]) for i in range(len(words) - size + 1)}


def _minhash(text: str) -> MinHash:
    m = MinHash(num_perm=MINHASH_PERMUTATIONS)
    for shingle in _shingles(text):
        m.update(shingle.encode())
    return m


def _jaccard(a: str, b: str) -> float:
    sa, sb = _shingles(a), _shingles(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def deduplicate(items: list[tuple[str, str]]) -> DedupeResult:
    """Keep one representative per group of duplicates.

    Longer text wins, on the assumption that it carries more context. Ordering
    is by length descending so the decision is deterministic.
    """
    result = DedupeResult()
    ordered = sorted(items, key=lambda it: (-len(it[1]), it[0]))

    seen_exact: dict[str, str] = {}
    survivors: list[tuple[str, str]] = []

    for item_id, text in ordered:
        fp = _fingerprint(text)
        if fp in seen_exact:
            result.pairs.append(
                DuplicatePair(kept=seen_exact[fp], dropped=item_id, similarity=1.0, kind="exact")
            )
            continue
        seen_exact[fp] = item_id
        survivors.append((item_id, text))

    lsh = MinHashLSH(threshold=NEAR_DUPLICATE_THRESHOLD, num_perm=MINHASH_PERMUTATIONS)
    hashes: dict[str, MinHash] = {}
    texts = dict(survivors)
    kept: list[str] = []

    for item_id, text in survivors:
        m = _minhash(text)
        matches = [other for other in lsh.query(m) if other in texts]
        if matches:
            # Confirm with exact Jaccard; MinHash is an estimate and the
            # threshold is close enough to matter.
            best = max(matches, key=lambda o: _jaccard(text, texts[o]))
            similarity = _jaccard(text, texts[best])
            if similarity >= NEAR_DUPLICATE_THRESHOLD:
                result.pairs.append(
                    DuplicatePair(
                        kept=best, dropped=item_id, similarity=similarity, kind="near"
                    )
                )
                continue
        lsh.insert(item_id, m)
        hashes[item_id] = m
        kept.append(item_id)

    result.keep = kept
    return result


# Topics whose numeric values are load-bearing and worth cross-checking.
CONTRADICTION_TOPICS: dict[str, re.Pattern[str]] = {
    "pre-existing disease waiting period": re.compile(
        r"pre-existing disease[^.]{0,80}?(\d{1,3})\s*(month|year)", re.I
    ),
    "initial waiting period": re.compile(
        r"initial waiting period[^.]{0,60}?(\d{1,3})\s*(day|month)", re.I
    ),
    "specified illness waiting period": re.compile(
        r"specified illness[^.]{0,80}?(\d{1,3})\s*(month|year)", re.I
    ),
    "maternity waiting period": re.compile(r"maternity[^.]{0,80}?(\d{1,3})\s*(month|year)", re.I),
    "cashless network size": re.compile(r"([\d,]{3,7})\s*(?:cashless\s+)?hospitals", re.I),
    "co-payment share": re.compile(r"co-payment[^.]{0,60}?(\d{1,3})\s*%", re.I),
    "grace period": re.compile(r"grace period[^.]{0,60}?(\d{1,3})\s*(day|month)", re.I),
}


def find_contradictions(items: list[tuple[str, str]]) -> list[Contradiction]:
    """Flag topics where sources state different numbers."""
    found: list[Contradiction] = []

    for topic, pattern in CONTRADICTION_TOPICS.items():
        by_value: dict[str, list[str]] = {}
        for item_id, text in items:
            for match in pattern.finditer(text):
                groups = match.groups()
                number = groups[0].replace(",", "")
                unit = groups[1].lower() + "s" if len(groups) > 1 and groups[1] else ""
                value = f"{number} {unit}".strip()
                by_value.setdefault(value, [])
                if item_id not in by_value[value]:
                    by_value[value].append(item_id)

        if len(by_value) > 1:
            found.append(
                Contradiction(
                    topic=topic,
                    values=list(by_value.keys()),
                    sources=[", ".join(v) for v in by_value.values()],
                )
            )

    return found
