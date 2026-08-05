"""Run the collection stage: fetch, extract, clean, and report.

Output is written to data/interim/documents.json for the next stage, and a
human-readable ingestion report to deliverables/q2_kb/. Sources that fail are
listed with the reason, because what was not collected is part of the result.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import yaml

from core.kb.clean import clean_text, drop_repeated_across_documents
from core.kb.extract import extract
from core.kb.fetch import ROOT, Fetcher

SOURCES_FILE = Path(__file__).resolve().parent / "sources.yaml"
INTERIM = ROOT / "data" / "interim"
REPORT_DIR = ROOT / "deliverables" / "q2_kb"


@dataclass
class Document:
    url: str
    title: str
    text: str
    category_hint: str
    source_type: str
    page_count: int
    tables: list[list[list[str]]] = field(default_factory=list)
    word_count: int = 0
    lines_dropped: int = 0
    fetched_at: str = ""


@dataclass
class Failure:
    url: str
    stage: str  # robots | fetch | extract
    reason: str
    category_hint: str = ""


def load_sources() -> tuple[dict, list[dict]]:
    config = yaml.safe_load(SOURCES_FILE.read_text())
    return config.get("brand", {}), config.get("sources", [])


def collect(use_cache: bool = True) -> tuple[list[Document], list[Failure], list[str]]:
    _brand, sources = load_sources()
    fetcher = Fetcher(use_cache=use_cache)

    documents: list[Document] = []
    failures: list[Failure] = []

    for entry in sources:
        url = entry["url"]
        hint = entry.get("category", "")

        result = fetcher.fetch(url)
        if not result.ok:
            stage = "robots" if "robots.txt" in (result.error or "") else "fetch"
            failures.append(Failure(url, stage, result.error or "unknown", hint))
            continue

        raw = (ROOT / result.path).read_bytes() if result.path else b""
        doc = extract(raw, url, result.is_pdf)

        if not doc.usable:
            failures.append(Failure(url, "extract", doc.reason, hint))
            continue

        cleaned = clean_text(doc.text, source_type=doc.source_type)
        documents.append(
            Document(
                url=url,
                title=doc.title,
                text=cleaned.text,
                category_hint=hint,
                source_type=doc.source_type,
                page_count=doc.page_count,
                tables=doc.tables,
                word_count=len(cleaned.text.split()),
                lines_dropped=cleaned.lines_dropped,
                fetched_at=datetime.now(UTC).isoformat(timespec="seconds"),
            )
        )

    # Site-wide headers and footers are only visible across documents.
    trimmed, repeated = drop_repeated_across_documents({d.url: d.text for d in documents})
    for doc in documents:
        doc.text = trimmed[doc.url]
        doc.word_count = len(doc.text.split())

    return documents, failures, repeated


def write_outputs(
    documents: list[Document], failures: list[Failure], repeated: list[str]
) -> None:
    INTERIM.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    (INTERIM / "documents.json").write_text(
        json.dumps([asdict(d) for d in documents], indent=2, ensure_ascii=False)
    )

    total_words = sum(d.word_count for d in documents)
    tables = sum(len(d.tables) for d in documents)

    lines = [
        "# Ingestion report",
        "",
        f"Generated {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')} "
        f"by `python scripts/build_kb.py --stage collect`.",
        "",
        "## Summary",
        "",
        f"| Sources attempted | {len(documents) + len(failures)} |",
        "|---|---|",
        f"| Collected | {len(documents)} |",
        f"| Failed or refused | {len(failures)} |",
        f"| Words after cleaning | {total_words:,} |",
        f"| Tables extracted | {tables} |",
        "",
        "## Collected",
        "",
        "| Source | Type | Words | Tables | Chrome lines removed |",
        "|---|---|---|---|---|",
    ]
    for d in sorted(documents, key=lambda x: -x.word_count):
        label = "PDF, %d pages" % d.page_count if d.source_type == "pdf" else "web page"
        # Source titles routinely contain pipes, which would break the table.
        title = d.title[:58].replace("|", "\\|")
        lines.append(
            f"| [{title}]({d.url}) | {label} | {d.word_count:,} | "
            f"{len(d.tables)} | {d.lines_dropped} |"
        )

    lines += [
        "",
        "## Failed or refused",
        "",
        "Recorded rather than skipped silently. A pipeline that drops these "
        "without comment reports success on a knowledge base with holes in it.",
        "",
        "| Source | Stage | Reason |",
        "|---|---|---|",
    ]
    for f in failures:
        lines.append(f"| `{f.url}` | {f.stage} | {f.reason} |")

    if repeated:
        lines += [
            "",
            "## Site-wide repeated lines removed",
            "",
            f"{len(repeated)} lines appeared in three or more documents and were "
            "removed as headers, footers or navigation. A sample:",
            "",
        ]
        lines += [f"- `{line[:100]}`" for line in repeated[:15]]

    lines.append("")
    (REPORT_DIR / "ingestion_report.md").write_text("\n".join(lines))


def main(use_cache: bool = True) -> None:
    documents, failures, repeated = collect(use_cache=use_cache)
    write_outputs(documents, failures, repeated)

    print(f"collected {len(documents)} documents, {len(failures)} failed or refused")
    for d in sorted(documents, key=lambda x: -x.word_count):
        print(f"  {d.word_count:>7,}w  {len(d.tables):>2} tables  {d.title[:60]}")
    for f in failures:
        print(f"  FAILED [{f.stage}] {f.url} — {f.reason}")
    print(f"\nreport: deliverables/q2_kb/ingestion_report.md")
