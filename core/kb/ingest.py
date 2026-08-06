"""Run the collection stage: fetch, extract, clean, normalize, protect, report.

Output goes to data/interim/documents.json for the next stage, plus a
human-readable ingestion report. Sources that fail, records quarantined for
carrying personal data, and contradictions between sources are all reported.
What was excluded is part of the result.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import yaml

from core.kb.clean import clean_text, drop_repeated_across_documents
from core.kb.dedupe import deduplicate, find_contradictions
from core.kb.extract import extract
from core.kb.fetch import ROOT, Fetcher
from core.kb.normalize import normalize
from core.kb.pii import csv_to_text, scan_and_mask

SOURCES_FILE = Path(__file__).resolve().parent / "sources.yaml"
INTERNAL_DIR = ROOT / "data" / "internal"
INTERIM = ROOT / "data" / "interim"
REPORT_DIR = ROOT / "deliverables" / "q2_kb"


@dataclass
class Document:
    doc_id: str
    url: str
    title: str
    text: str
    category_hint: str
    source_type: str  # web_page | pdf | internal_document | internal_data
    page_count: int = 1
    tables: list[list[list[str]]] = field(default_factory=list)
    word_count: int = 0
    lines_dropped: int = 0
    lang: str = "en"
    pii: bool = False
    pii_types: list[str] = field(default_factory=list)
    term_changes: int = 0
    date_changes: int = 0
    currency_changes: int = 0
    fetched_at: str = ""


@dataclass
class Excluded:
    ref: str
    stage: str  # robots | fetch | extract | pii | duplicate
    reason: str


def load_config() -> tuple[dict, list[dict]]:
    config = yaml.safe_load(SOURCES_FILE.read_text())
    return config.get("brand", {}), config.get("sources", [])


def _doc_id(prefix: str, index: int) -> str:
    return f"{prefix}_{index:03d}"


def collect_web(fetcher: Fetcher) -> tuple[list[Document], list[Excluded]]:
    _brand, sources = load_config()
    documents: list[Document] = []
    excluded: list[Excluded] = []

    for index, entry in enumerate(sources, start=1):
        url = entry["url"]
        hint = entry.get("category", "")

        result = fetcher.fetch(url)
        if not result.ok:
            stage = "robots" if "robots.txt" in (result.error or "") else "fetch"
            excluded.append(Excluded(url, stage, result.error or "unknown"))
            continue

        raw = (ROOT / result.path).read_bytes() if result.path else b""
        doc = extract(raw, url, result.is_pdf)
        if not doc.usable:
            excluded.append(Excluded(url, "extract", doc.reason))
            continue

        cleaned = clean_text(doc.text, source_type=doc.source_type)
        documents.append(
            Document(
                doc_id=_doc_id("src", index),
                url=url,
                title=doc.title,
                text=cleaned.text,
                category_hint=hint,
                source_type=doc.source_type,
                page_count=doc.page_count,
                tables=doc.tables,
                lines_dropped=cleaned.lines_dropped,
                fetched_at=datetime.now(UTC).isoformat(timespec="seconds"),
            )
        )

    return documents, excluded


# Which authored documents belong to which corpus. The markets are kept apart
# because their embedding models and calibrated thresholds differ, and mixing
# Tagalog and Indonesian records into an English index would make one similarity
# threshold answer for three scales.
CORPUS_PREFIXES = {
    "en": ("arogya_first_", "sample_leads"),
    "multilingual": ("ph_", "id_"),
}

CORPUS_LANGUAGE = {"ph_": "fil", "id_": "id"}


def collect_internal(corpus: str = "en") -> list[Document]:
    """Load the authored internal documents for the fictional brand.

    These carry what public pages cannot: the brand's own product terms,
    qualification rules, approved objection responses and call script. They also
    contain the personal data, duplication and contradictions that the
    protection and deduplication stages exist to handle.
    """
    documents: list[Document] = []
    if not INTERNAL_DIR.exists():
        return documents

    category_by_stem = {
        "arogya_first_product_brochure": "product",
        "arogya_first_qualification_rules": "qualification",
        "arogya_first_faq": "faq",
        "arogya_first_objections": "objection",
        "arogya_first_sales_script": "process",
        "sample_leads": "internal_records",
        "ph_kalinga_life_products": "product",
        "ph_kalinga_objections": "objection",
        "id_amanah_finance_products": "product",
        "id_amanah_objections": "objection",
    }
    prefixes = CORPUS_PREFIXES.get(corpus, CORPUS_PREFIXES["en"])

    for index, path in enumerate(sorted(INTERNAL_DIR.iterdir()), start=1):
        if path.suffix not in (".md", ".csv"):
            continue
        if not path.stem.startswith(prefixes):
            continue
        raw = path.read_text()
        if path.suffix == ".csv":
            text = csv_to_text(raw)
            source_type = "internal_data"
        else:
            text = raw
            source_type = "internal_document"

        title = text.splitlines()[0].lstrip("# ").strip() if text else path.stem
        if source_type == "internal_data":
            title = path.stem.replace("_", " ").title()

        language = next(
            (lang for prefix, lang in CORPUS_LANGUAGE.items() if path.stem.startswith(prefix)),
            "en",
        )
        documents.append(
            Document(
                doc_id=_doc_id("int", index),
                url=f"internal://{path.name}",
                title=title,
                text=text,
                category_hint=category_by_stem.get(path.stem, ""),
                source_type=source_type,
                lang=language,
                fetched_at=datetime.now(UTC).isoformat(timespec="seconds"),
            )
        )

    return documents


def protect_and_normalize(
    documents: list[Document],
) -> tuple[list[Document], list[Excluded], dict[str, int]]:
    """Mask personal data, quarantine records exports, standardize terminology."""
    kept: list[Document] = []
    excluded: list[Excluded] = []
    term_totals: dict[str, int] = {}

    for doc in documents:
        protected = scan_and_mask(doc.text)
        if protected.quarantined:
            excluded.append(Excluded(doc.url, "pii", protected.reason))
            continue

        normalized = normalize(protected.text)
        doc.text = normalized.text
        doc.pii = protected.has_pii
        doc.pii_types = protected.kinds
        doc.term_changes = sum(normalized.term_changes.values())
        doc.date_changes = normalized.date_changes
        doc.currency_changes = normalized.currency_changes
        doc.word_count = len(doc.text.split())
        for change, count in normalized.term_changes.items():
            term_totals[change] = term_totals.get(change, 0) + count
        kept.append(doc)

    return kept, excluded, term_totals


def collect(use_cache: bool = True, corpus: str = "en") -> dict:
    """Collect one corpus.

    The English corpus draws on the public sources and the India documents. The
    multilingual corpus is the Philippine and Indonesian documents only: there are
    no public Taglish or Bahasa sources in the source list, and the market content
    is authored.
    """
    excluded: list[Excluded] = []
    web: list[Document] = []
    if corpus == "en":
        fetcher = Fetcher(use_cache=use_cache)
        web, excluded = collect_web(fetcher)
    documents = web + collect_internal(corpus)

    # Site-wide headers and footers are only identifiable across documents.
    web_texts = {d.doc_id: d.text for d in documents if d.source_type == "web_page"}
    trimmed, repeated = drop_repeated_across_documents(web_texts)
    for doc in documents:
        if doc.doc_id in trimmed:
            doc.text = trimmed[doc.doc_id]

    documents, pii_excluded, term_totals = protect_and_normalize(documents)
    excluded += pii_excluded

    pairs = [(d.doc_id, d.text) for d in documents]
    dedup = deduplicate(pairs)
    contradictions = find_contradictions(pairs)

    titles = {d.doc_id: d.title for d in documents}
    for pair in dedup.pairs:
        excluded.append(
            Excluded(
                ref=f"{titles.get(pair.dropped, pair.dropped)} ({pair.dropped})",
                stage="duplicate",
                reason=f"{pair.kind} duplicate of {titles.get(pair.kept, pair.kept)}, "
                f"similarity {pair.similarity:.2f}",
            )
        )
    surviving = {d.doc_id for d in documents} - dedup.dropped_ids
    documents = [d for d in documents if d.doc_id in surviving]

    return {
        "documents": documents,
        "excluded": excluded,
        "repeated_lines": repeated,
        "term_totals": term_totals,
        "contradictions": contradictions,
    }


def write_outputs(state: dict, corpus: str = "en") -> None:
    documents: list[Document] = state["documents"]
    excluded: list[Excluded] = state["excluded"]

    INTERIM.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    suffix = "" if corpus == "en" else f"_{corpus}"
    (INTERIM / f"documents{suffix}.json").write_text(
        json.dumps([asdict(d) for d in documents], indent=2, ensure_ascii=False)
    )

    total_words = sum(d.word_count for d in documents)
    tables = sum(len(d.tables) for d in documents)
    pii_docs = [d for d in documents if d.pii]
    term_totals: dict[str, int] = state["term_totals"]

    lines = [
        "# Ingestion report",
        "",
        f"Generated {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')} by "
        "`python scripts/build_kb.py --stage collect`.",
        "",
        "## Summary",
        "",
        "| Measure | Value |",
        "|---|---|",
        f"| Inputs attempted | {len(documents) + len(excluded)} |",
        f"| Documents collected | {len(documents)} |",
        f"| Excluded (failed, refused, quarantined, duplicate) | {len(excluded)} |",
        f"| Words after cleaning | {total_words:,} |",
        f"| Tables extracted | {tables} |",
        f"| Documents containing masked personal data | {len(pii_docs)} |",
        f"| Terminology substitutions applied | {sum(term_totals.values())} |",
        f"| Dates converted to ISO 8601 | {sum(d.date_changes for d in documents)} |",
        f"| Currency amounts standardised | {sum(d.currency_changes for d in documents)} |",
        "",
        "## Documents collected",
        "",
        "| ID | Source | Type | Words | Tables | Personal data |",
        "|---|---|---|---|---|---|",
    ]
    for d in sorted(documents, key=lambda x: -x.word_count):
        label = {
            "pdf": f"PDF, {d.page_count} pages",
            "web_page": "web page",
            "internal_document": "internal document",
            "internal_data": "internal data",
        }.get(d.source_type, d.source_type)
        title = d.title[:52].replace("|", "\\|")
        link = f"[{title}]({d.url})" if d.url.startswith("http") else f"{title}"
        pii = ", ".join(d.pii_types) if d.pii else "none"
        lines.append(
            f"| `{d.doc_id}` | {link} | {label} | {d.word_count:,} | {len(d.tables)} | {pii} |"
        )

    lines += [
        "",
        "## Excluded",
        "",
        "Recorded rather than dropped silently. A pipeline that discards these "
        "without comment reports success on a knowledge base with holes in it.",
        "",
        "| Input | Stage | Reason |",
        "|---|---|---|",
    ]
    for e in excluded:
        ref = e.ref if e.ref.startswith("http") else f"`{e.ref}`"
        lines.append(f"| {ref} | {e.stage} | {e.reason} |")

    contradictions = state["contradictions"]
    lines += [
        "",
        "## Contradictions between sources",
        "",
    ]
    if contradictions:
        lines += [
            "Reported, not resolved. Choosing a value silently would bury a source "
            "error that a person needs to settle. Retrieval surfaces both records "
            "with their provenance so the conflict is visible.",
            "",
            "| Topic | Conflicting values |",
            "|---|---|",
        ]
        for c in contradictions:
            values = " vs ".join(
                f"**{v}** in `{s}`" for v, s in zip(c.values, c.sources, strict=False)
            )
            lines.append(f"| {c.topic} | {values} |")
    else:
        lines.append("None detected.")

    if term_totals:
        lines += [
            "",
            "## Terminology standardisation",
            "",
            "Sources use different words for the same concept. Retrieval degrades "
            "when a concept is spelled three ways, so one canonical form is applied.",
            "",
            "| Substitution | Occurrences |",
            "|---|---|",
        ]
        for change, count in sorted(term_totals.items(), key=lambda kv: -kv[1]):
            lines.append(f"| {change} | {count} |")

    if state["repeated_lines"]:
        repeated = state["repeated_lines"]
        lines += [
            "",
            "## Site-wide repeated lines removed",
            "",
            f"{len(repeated)} lines appeared in three or more web documents and were "
            "removed as headers, footers or navigation.",
            "",
        ]
        lines += [f"- `{line[:100]}`" for line in repeated[:15]]

    lines += [
        "",
        "## Personal data handling",
        "",
        "Two outcomes, not one. Documents with incidental personal data — an "
        "example call written into a script — are masked in place and flagged. A "
        "document whose substance *is* personal data, such as a lead export, is "
        "quarantined and never indexed: a knowledge base a voice agent retrieves "
        "from has no legitimate need for customer records.",
        "",
        "Detected classes: email, phone, PAN, Aadhaar, policy number, lead "
        "reference, and names where a cue word makes the role explicit.",
        "",
        "Known limit: names are only detected after a cue such as \"Caller:\" or an "
        "honorific. Detecting names by capitalisation alone would flag product "
        "names like \"Optima Secure\" as people, so recall is traded for precision.",
        "",
    ]
    report_name = "ingestion_report.md" if corpus == "en" else f"ingestion_report_{corpus}.md"
    (REPORT_DIR / report_name).write_text("\n".join(lines))


def main(use_cache: bool = True, corpus: str = "en") -> None:
    state = collect(use_cache=use_cache, corpus=corpus)
    write_outputs(state, corpus=corpus)

    documents = state["documents"]
    print(f"collected {len(documents)} documents, {len(state['excluded'])} excluded")
    for d in sorted(documents, key=lambda x: -x.word_count):
        flag = f"  PII[{','.join(d.pii_types)}]" if d.pii else ""
        print(f"  {d.word_count:>7,}w  {len(d.tables):>2}t  {d.doc_id}  {d.title[:44]}{flag}")
    for e in state["excluded"]:
        print(f"  EXCLUDED [{e.stage}] {e.ref[:60]} — {e.reason[:70]}")
    if state["contradictions"]:
        print("\ncontradictions:")
        for c in state["contradictions"]:
            print(f"  {c.describe()}")
    print(f"\nreport: deliverables/q2_kb/{report_name}")
