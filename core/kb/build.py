"""Turn collected documents into indexed records.

Runs after the collect stage. Chunks each document, assigns a taxonomy
category, removes near-duplicate records, embeds what survives, and writes the
database, the lexical index and the vector index.

Near-duplicate removal happens here rather than at document level. Two documents
are rarely duplicates of each other, but the same fact stated in a brochure and
an FAQ sheet produces two records that say the same thing, and it is those that
waste a retrieval slot.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from core.kb.chunk import chunk_document, is_answerable
from core.kb.dedupe import deduplicate
from core.kb.embed import encode, model_name
from core.kb.fetch import ROOT
from core.kb.store import KnowledgeBase, Record, faiss_path, write_metadata

INTERIM = ROOT / "data" / "interim"
REPORT_DIR = ROOT / "deliverables" / "q2_kb"

TAXONOMY = ("product", "policy_rule", "qualification", "faq", "objection", "process")

# Distinct keyword hits are counted per category and the highest score wins.
# First-match-wins was tried first and produced a corpus that was 65% policy
# rules: the broadest pattern ran first and absorbed everything it touched.
# Scoring lets a passage that mentions renewal once but is mostly about premiums
# land under product, where it belongs.
CATEGORY_TERMS: dict[str, tuple[str, ...]] = {
    "product": (
        "sum insured", "premium", "plan", "cover", "benefit", "floater",
        "top-up", "restoration", "no claim bonus", "network hospital",
        "day care", "room rent", "maternity benefit", "senior care",
    ),
    "policy_rule": (
        "waiting period", "exclusion", "grace period", "co-payment",
        "pre-existing", "portability", "lapse", "deductible", "sub-limit",
        "irdai", "grievance", "not covered", "permanent exclusion",
    ),
    "qualification": (
        "eligib", "age band", "age limit", "entry age", "zone", "qualif",
        "budget", "underwrit", "declared condition", "medical check",
        "required information", "decline", "referred",
    ),
    "faq": (
        "what is", "how do", "how long", "can i", "does the", "do i",
        "why is", "when are", "what happens", "is a ",
    ),
    "objection": (
        "objection", "too expensive", "already have", "do not need",
        "reject claims", "think about it", "guarantee", "cheapest",
        "price-sensitive", "acknowledge the concern",
    ),
    "process": (
        "script", "opening", "closing", "escalat", "compliance", "do not say",
        "consent", "call flow", "claim intimation", "pre-authoris",
        "transfer to", "callback",
    ),
}

# A heading states what a passage is about; a body mentions things in passing.
HEADING_WEIGHT = 3
BODY_WEIGHT = 1
HINT_WEIGHT = 2
BODY_SCAN_CHARS = 600


@dataclass
class BuildStats:
    documents: int = 0
    chunks: int = 0
    unanswerable_removed: int = 0
    duplicates_removed: int = 0
    records: int = 0
    tables: int = 0
    pii_records: int = 0


def classify(section_path: str, content: str, hint: str) -> str:
    """Assign a taxonomy category by scoring keyword evidence.

    Distinct terms are counted rather than total occurrences, so a passage that
    repeats "premium" nine times does not outrank one that discusses eligibility,
    zones and age bands. Ties fall to the document's own hint.
    """
    heading = section_path.lower()
    body = content[:BODY_SCAN_CHARS].lower()

    scores: dict[str, int] = {}
    for category, terms in CATEGORY_TERMS.items():
        score = sum(HEADING_WEIGHT for term in terms if term in heading)
        score += sum(BODY_WEIGHT for term in terms if term in body)
        if category == hint:
            score += HINT_WEIGHT
        scores[category] = score

    best = max(scores.values())
    if best == 0:
        return hint if hint in TAXONOMY else "product"

    winners = [c for c, s in scores.items() if s == best]
    if len(winners) > 1 and hint in winners:
        return hint
    return winners[0]


def _extract_version(text: str) -> str:
    match = re.search(r"\bVersion\s+(\d+(?:\.\d+)?)", text, re.I)
    return match.group(1) if match else "1.0"


def _extract_effective_date(text: str) -> str | None:
    match = re.search(
        r"\b(?:Effective|Last updated)\b[^\n]{0,20}?(\d{4}-\d{2}-\d{2})", text, re.I
    )
    return match.group(1) if match else None


def load_documents() -> list[dict]:
    path = INTERIM / "documents.json"
    if not path.exists():
        raise FileNotFoundError(
            "no collected documents — run scripts/build_kb.py --stage collect first"
        )
    return json.loads(path.read_text())


def build_records(documents: list[dict]) -> tuple[list[Record], BuildStats, list]:
    stats = BuildStats(documents=len(documents))
    candidates: list[Record] = []

    for doc in documents:
        version = _extract_version(doc["text"])
        effective = _extract_effective_date(doc["text"])
        chunks = chunk_document(
            text=doc["text"],
            doc_id=doc["doc_id"],
            title=doc["title"],
            source_type=doc["source_type"],
            tables=doc.get("tables") or [],
        )
        stats.chunks += len(chunks)

        keep = [c for c in chunks if c.kind == "table" or is_answerable(c.content)]
        stats.unanswerable_removed += len(chunks) - len(keep)

        for chunk in keep:
            category = classify(chunk.section_path, chunk.content, doc.get("category_hint", ""))
            record_id = f"kb_{category}_{doc['doc_id']}_{chunk.ordinal:03d}"
            candidates.append(
                Record(
                    record_id=record_id,
                    title=chunk.section_path.split(" > ")[-1][:120] or doc["title"][:120],
                    content=chunk.content,
                    category=category,
                    source_url=doc["url"],
                    source_type=doc["source_type"],
                    section_path=chunk.section_path,
                    version=version,
                    effective_date=effective,
                    checksum=chunk.checksum,
                    pii=bool(doc.get("pii")),
                    pii_types=list(doc.get("pii_types") or []),
                    lang="en",
                    kind=chunk.kind,
                    doc_id=doc["doc_id"],
                    ordinal=chunk.ordinal,
                    word_count=chunk.word_count,
                    ingested_at=datetime.now(UTC).isoformat(timespec="seconds"),
                )
            )

    dedup = deduplicate([(r.record_id, r.content) for r in candidates])
    dropped = dedup.dropped_ids
    records = [r for r in candidates if r.record_id not in dropped]

    stats.duplicates_removed = len(dropped)
    stats.records = len(records)
    stats.tables = sum(1 for r in records if r.kind == "table")
    stats.pii_records = sum(1 for r in records if r.pii)
    return records, stats, dedup.pairs


def write_schema_doc(
    kb: KnowledgeBase,
    stats: BuildStats,
    duplicate_pairs: list,
    embedding_dimension: int,
) -> None:
    """Write the schema deliverable.

    The embedding dimension is passed in rather than re-derived. Asking the
    embedding library for it re-enters the model hub, which turned a local
    report into a network call that failed intermittently.
    """
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    records = kb.all_records()
    counts = kb.category_counts()

    def sample(predicate) -> Record | None:
        return next((r for r in records if predicate(r)), None)

    def render(record: Record) -> list[str]:
        content = record.content.replace("\n", " ")
        content = content[:300] + ("…" if len(record.content) > 300 else "")
        return [
            "| Field | Value |",
            "|---|---|",
            f"| `record_id` | `{record.record_id}` |",
            f"| `title` | {record.title} |",
            f"| `content` | {content.replace('|', chr(92) + '|')} |",
            f"| `category` | `{record.category}` |",
            f"| `source_url` | {record.source_url} |",
            f"| `source_type` | `{record.source_type}` |",
            f"| `section_path` | {record.section_path.replace('|', chr(92) + '|')} |",
            f"| `version` / `effective_date` | {record.version} / {record.effective_date or '—'} |",
            f"| `checksum` | `{record.checksum}` |",
            f"| `pii` / `pii_types` | {str(record.pii).lower()} / "
            f"{', '.join(record.pii_types) or '—'} |",
            f"| `lang` / `kind` | {record.lang} / `{record.kind}` |",
            f"| `doc_id` / `ordinal` | `{record.doc_id}` / {record.ordinal} |",
            f"| `word_count` | {record.word_count} |",
            "",
        ]

    lines = [
        "# Knowledge-base schema and records",
        "",
        f"Generated {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')} by "
        "`python scripts/build_kb.py --stage build`.",
        "",
        "## Build summary",
        "",
        "| Measure | Value |",
        "|---|---|",
        f"| Documents chunked | {stats.documents} |",
        f"| Chunks produced | {stats.chunks} |",
        f"| Unanswerable fragments removed | {stats.unanswerable_removed} |",
        f"| Near-duplicate records removed | {stats.duplicates_removed} |",
        f"| Records indexed | {stats.records} |",
        f"| Table records | {stats.tables} |",
        f"| Records carrying masked personal data | {stats.pii_records} |",
        f"| Embedding model | `{model_name()}` ({embedding_dimension} dimensions) |",
        f"| Median record length | "
        f"{sorted(r.word_count for r in records)[len(records) // 2] if records else 0} words |",
        "",
        "## Taxonomy",
        "",
        "Six categories, chosen to match the question types a caller actually asks. "
        "Retrieval can filter by category, so the conversation stage narrows the search: "
        "an objection turn searches objections and policy rules before product pages.",
        "",
        "| Category | Records | Purpose |",
        "|---|---|---|",
    ]
    purposes = {
        "product": "plans, cover amounts, premiums, benefits",
        "policy_rule": "waiting periods, exclusions, regulatory and renewal terms",
        "qualification": "eligibility bands, zones, declared conditions, budget guidance",
        "faq": "questions asked in the caller's own words",
        "objection": "approved responses to resistance",
        "process": "call flow, consent, escalation, compliance requirements",
    }
    for category in TAXONOMY:
        lines.append(f"| `{category}` | {counts.get(category, 0)} | {purposes[category]} |")

    lines += [
        "",
        "## Field definitions",
        "",
        "| Field | Type | Purpose |",
        "|---|---|---|",
        "| `record_id` | text, primary key | stable citation target; encodes category and source document |",
        "| `title` | text | the record's own heading, read aloud when citing |",
        "| `content` | text | the retrievable passage, cleaned, normalized and masked |",
        "| `category` | text | one of the six taxonomy values |",
        "| `source_url` | text | provenance; a real URL for public sources, `internal://` for authored documents |",
        "| `source_type` | text | `web_page`, `pdf`, `internal_document`, `internal_data` |",
        "| `section_path` | text | heading trail within the source, giving a human the location |",
        "| `version` | text | taken from the source document's own version line |",
        "| `effective_date` | date | when the stated terms took effect, ISO 8601 |",
        "| `checksum` | text | content hash; a changed hash means a new version of the record |",
        "| `superseded_by` | text | set when a newer record replaces this one |",
        "| `pii` | boolean | whether personal data was found and masked |",
        "| `pii_types` | text | which classes were masked |",
        "| `lang` | text | `en`, `fil`, `id` |",
        "| `kind` | text | `prose` or `table`; tables keep their header row |",
        "| `doc_id` | text | the source document this record came from |",
        "| `ordinal` | integer | position within the document, for reading neighbours |",
        "| `word_count` | integer | length, used to check retrieval budget |",
        "| `ingested_at` | timestamp | audit trail |",
        "",
        "## Versioning",
        "",
        "`version` and `effective_date` are read from the source document rather than "
        "invented, so a record states the authority it came from. `checksum` is the "
        "content hash: a re-ingest that changes a passage produces a different "
        "checksum, which is how a superseding record is identified. `superseded_by` "
        "then points forward, so an answer given last month can still be traced to the "
        "record that produced it.",
        "",
        "## Sample records",
        "",
    ]

    samples = [
        ("A product record", sample(lambda r: r.category == "product" and r.kind == "prose")),
        ("A policy rule", sample(lambda r: r.category == "policy_rule")),
        ("A qualification table", sample(lambda r: r.category == "qualification" and r.kind == "table")),
        ("An objection response", sample(lambda r: r.category == "objection")),
        ("A record with masked personal data", sample(lambda r: r.pii)),
    ]
    for label, record in samples:
        if record is None:
            continue
        lines.append(f"### {label}")
        lines.append("")
        lines.extend(render(record))

    if duplicate_pairs:
        lines += [
            "## Near-duplicate records removed",
            "",
            "The same fact stated in two places produces two records that compete for "
            "the same retrieval slot. Similarity is Jaccard overlap over five-word "
            "shingles; the longer record is kept.",
            "",
            "| Kept | Removed | Similarity |",
            "|---|---|---|",
        ]
        for pair in duplicate_pairs[:20]:
            lines.append(
                f"| `{pair.kept}` | `{pair.dropped}` | {pair.similarity:.2f} ({pair.kind}) |"
            )
        if len(duplicate_pairs) > 20:
            lines.append(f"| … | {len(duplicate_pairs) - 20} more | |")

    lines.append("")
    (REPORT_DIR / "schema.md").write_text("\n".join(lines))


def main() -> None:
    documents = load_documents()
    records, stats, duplicate_pairs = build_records(documents)
    if not records:
        raise RuntimeError("chunking produced no records")

    print(f"chunked {stats.documents} documents into {stats.chunks} chunks")
    print(f"dropped {stats.unanswerable_removed} unanswerable fragments")
    print(f"removed {stats.duplicates_removed} near-duplicates, {stats.records} records remain")

    kb = KnowledgeBase()
    kb.replace_all(records)

    print(f"embedding {len(records)} records with {model_name()}…")
    vectors = encode([f"{r.title}\n{r.content}" for r in records])
    kb.build_vector_index(vectors)

    kb.set_build_info(
        {
            "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "embedding_model": model_name(),
            "embedding_dimension": str(vectors.shape[1]),
            "record_count": str(len(records)),
        }
    )
    write_metadata(
        {
            "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "embedding_model": model_name(),
            "embedding_dimension": int(vectors.shape[1]),
            "records": len(records),
            "documents": stats.documents,
            "duplicates_removed": stats.duplicates_removed,
            "unanswerable_removed": stats.unanswerable_removed,
            "categories": kb.category_counts(),
        }
    )
    write_schema_doc(kb, stats, duplicate_pairs, int(vectors.shape[1]))

    print(f"categories: {kb.category_counts()}")
    print(f"database: {Path(kb.path).name}  vectors: {faiss_path().name}")
    print("report: deliverables/q2_kb/schema.md")
    kb.close()
