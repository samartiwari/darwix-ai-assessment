"""Split documents into retrievable records.

Chunking is structure-aware rather than fixed-width. A retrieved record has to
stand on its own when read aloud to a caller, which means it needs the heading
that gives it context and it must not begin halfway through a sentence.

Three shapes are handled differently:

* Markdown internal documents split on headings, which are authored and
  reliable, so each section becomes one record where it fits the size budget.
* Web and PDF prose has no reliable heading markup, so a heuristic identifies
  heading-like lines and paragraphs are packed into overlapping windows beneath
  them.
* Tables become one record each, with the header row repeated when a large table
  is split, so a row is never separated from the column it belongs to.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

# Budgets are in words. Roughly 260 words is 350 tokens for English prose, which
# fits comfortably in a retrieval context alongside several other records.
TARGET_WORDS = 260
MAX_WORDS = 400
MIN_WORDS = 25
OVERLAP_WORDS = 45

# Table rows per record before splitting, header repeated on each part.
TABLE_ROWS_PER_RECORD = 12


@dataclass
class Chunk:
    content: str
    section_path: str
    kind: str = "prose"  # prose | table
    ordinal: int = 0
    doc_id: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def word_count(self) -> int:
        return len(self.content.split())

    @property
    def checksum(self) -> str:
        return hashlib.sha256(self.content.encode()).hexdigest()[:16]


def _is_heading_like(line: str, next_line: str | None) -> bool:
    """A short, unpunctuated line introducing longer text below it."""
    stripped = line.strip()
    if not stripped or stripped.startswith("|"):
        return False
    words = stripped.split()
    if not (1 <= len(words) <= 10):
        return False
    if re.search(r"[.!?,;]$", stripped):
        return False
    if stripped.islower():
        return False
    if next_line is None:
        return False
    return len(next_line.split()) > len(words)


def _split_sentences(text: str) -> list[str]:
    """Split on sentence boundaries, avoiding common abbreviations."""
    protected = re.sub(r"\b(Rs|Mr|Mrs|Ms|Dr|No|vs|etc|i\.e|e\.g)\.", r"\1<DOT>", text)
    parts = re.split(r"(?<=[.!?])\s+", protected)
    return [p.replace("<DOT>", ".").strip() for p in parts if p.strip()]


def _pack(units: list[str], section_path: str, doc_id: str, start_ordinal: int) -> list[Chunk]:
    """Pack text units into overlapping windows within the word budget.

    Overlap is taken from the tail of the previous window in whole units, so a
    record never opens mid-sentence.
    """
    chunks: list[Chunk] = []
    current: list[str] = []
    ordinal = start_ordinal

    def flush() -> None:
        nonlocal current, ordinal
        if not current:
            return
        text = " ".join(current).strip()
        if len(text.split()) >= MIN_WORDS or not chunks:
            chunks.append(
                Chunk(
                    content=text,
                    section_path=section_path,
                    kind="prose",
                    ordinal=ordinal,
                    doc_id=doc_id,
                )
            )
            ordinal += 1
        current = []

    for unit in units:
        unit_words = len(unit.split())

        # A single unit larger than the ceiling is split on sentences.
        if unit_words > MAX_WORDS:
            flush()
            sentences = _split_sentences(unit)
            if len(sentences) > 1:
                chunks.extend(_pack(sentences, section_path, doc_id, ordinal))
                ordinal = start_ordinal + len(chunks)
            else:
                words = unit.split()
                for i in range(0, len(words), TARGET_WORDS):
                    chunks.append(
                        Chunk(
                            content=" ".join(words[i : i + TARGET_WORDS]),
                            section_path=section_path,
                            kind="prose",
                            ordinal=ordinal,
                            doc_id=doc_id,
                        )
                    )
                    ordinal += 1
            continue

        if current and len(" ".join(current).split()) + unit_words > TARGET_WORDS:
            tail = []
            tail_words = 0
            for previous in reversed(current):
                previous_words = len(previous.split())
                if tail_words + previous_words > OVERLAP_WORDS:
                    break
                tail.insert(0, previous)
                tail_words += previous_words
            flush()
            current = list(tail)

        current.append(unit)

    flush()
    return chunks


def _chunk_markdown(text: str, doc_id: str, title: str) -> list[Chunk]:
    """Split on authored headings, keeping the heading trail as context."""
    chunks: list[Chunk] = []
    trail: dict[int, str] = {}
    buffer: list[str] = []
    current_path = title
    ordinal = 0

    def flush_buffer() -> None:
        nonlocal buffer, ordinal
        body = "\n".join(buffer).strip()
        buffer = []
        if not body:
            return
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
        # Table blocks inside a section become their own records.
        prose = [p for p in paragraphs if not p.lstrip().startswith("|")]
        tables = [p for p in paragraphs if p.lstrip().startswith("|")]

        for table in tables:
            rows = [r for r in table.splitlines() if r.strip()]
            chunks.extend(_chunk_table_rows(rows, current_path, doc_id, ordinal))
            ordinal = len(chunks)

        if prose:
            packed = _pack(prose, current_path, doc_id, ordinal)
            chunks.extend(packed)
            ordinal = len(chunks)

    for line in text.splitlines():
        heading = re.match(r"^(#{1,6})\s+(.*)$", line)
        if heading:
            flush_buffer()
            level = len(heading.group(1))
            trail[level] = heading.group(2).strip()
            for deeper in [k for k in trail if k > level]:
                del trail[deeper]
            parts = [trail[k] for k in sorted(trail)]
            current_path = " > ".join(parts) if parts else title
            continue
        buffer.append(line)

    flush_buffer()
    return chunks


def _chunk_prose(text: str, doc_id: str, title: str) -> list[Chunk]:
    """Pack paragraphs under heuristically detected headings."""
    lines = text.splitlines()
    sections: list[tuple[str, list[str]]] = []
    current_heading = title
    buffer: list[str] = []

    for index, line in enumerate(lines):
        following = next(
            (candidate for candidate in lines[index + 1 : index + 3] if candidate.strip()), None
        )
        if _is_heading_like(line, following):
            if buffer:
                sections.append((current_heading, buffer))
                buffer = []
            current_heading = line.strip()
            continue
        if line.strip():
            buffer.append(line.strip())
    if buffer:
        sections.append((current_heading, buffer))

    chunks: list[Chunk] = []
    for heading, body_lines in sections:
        section_path = heading if heading == title else f"{title} > {heading}"
        paragraphs: list[str] = []
        run: list[str] = []
        for line in body_lines:
            if line.startswith("|"):
                if run:
                    paragraphs.append(" ".join(run))
                    run = []
                paragraphs.append(line)
            else:
                run.append(line)
        if run:
            paragraphs.append(" ".join(run))

        table_rows = [p for p in paragraphs if p.startswith("|")]
        prose = [p for p in paragraphs if not p.startswith("|")]

        if table_rows:
            chunks.extend(_chunk_table_rows(table_rows, section_path, doc_id, len(chunks)))
        if prose:
            chunks.extend(_pack(prose, section_path, doc_id, len(chunks)))

    return chunks


def _chunk_table_rows(
    rows: list[str], section_path: str, doc_id: str, start_ordinal: int
) -> list[Chunk]:
    """One record per table, split with the header repeated when large."""
    if not rows:
        return []
    header = rows[0]
    body = [r for r in rows[1:] if not re.fullmatch(r"[\s|:-]+", r)]
    if not body:
        return [
            Chunk(
                content=header,
                section_path=section_path,
                kind="table",
                ordinal=start_ordinal,
                doc_id=doc_id,
            )
        ]

    chunks: list[Chunk] = []
    for index in range(0, len(body), TABLE_ROWS_PER_RECORD):
        part = body[index : index + TABLE_ROWS_PER_RECORD]
        chunks.append(
            Chunk(
                content="\n".join([header, *part]),
                section_path=section_path,
                kind="table",
                ordinal=start_ordinal + len(chunks),
                doc_id=doc_id,
                extra={"rows": len(part)},
            )
        )
    return chunks


# Document-level metadata lines. These belong in record fields, where version
# and effective date are already stored, not in retrievable content. Left in
# place they become records whose whole text is "Version 1.9 | Last updated
# 2025-03-15 | Contact centre reference".
METADATA_LINE = re.compile(
    r"^\s*(?:version\s+[\d.]+|"
    r"(?:version|effective|last updated)\b[^|\n]{0,40}\|.*|"
    r".*\|\s*(?:internal distribution|sales operations|contact centre[^|\n]*)\s*)$",
    re.I,
)


def strip_metadata_lines(text: str) -> str:
    return "\n".join(ln for ln in text.splitlines() if not METADATA_LINE.match(ln))


# Debris that survives PDF extraction: front matter, contents pages with dot
# leaders, chart axis labels reduced to bare numbers, abbreviation glossaries.
# None of it answers a question, and each piece occupies a retrieval slot.
DOT_LEADERS = re.compile(r"\.{4,}")

# Markers of a bibliography rather than prose. Counted, not merely detected: a
# paragraph about German social health insurance may cite one DOI, while a
# reference block is made of nothing else. An earlier version dropped any record
# containing a single ISSN, which discarded three substantial passages.
CITATION_MARKER = re.compile(
    r"Retrieved\s+\d{4}|Archived from the original|-\s*↑|"
    r"\b(?:ISBN|ISSN)\b|\bdoi:|10\.\d{4,}/|\bpp\.\s*\d|\bvol\.\s*\d",
    re.I,
)
# A reference block carries roughly one marker every fifteen words; a paragraph
# that cites a single source carries one in two hundred. Density separates them
# where an absolute count cannot, since a long passage may cite several sources
# and still be prose.
MIN_CITATION_MARKERS = 3
MAX_CITATION_DENSITY = 0.02
MAX_DOT_LEADER_RUNS = 2
ANSWERABLE_MIN_WORDS = 10
MAX_NON_PROSE_RATIO = 0.4


def is_answerable(content: str) -> bool:
    """Whether a prose record could plausibly answer a question.

    Applied to prose only. Table records are exempt: a two-row table is short by
    nature and its numbers are the content.
    """
    text = content.strip()
    if not text:
        return False

    # A contents page: repeated dot leaders joining headings to page numbers.
    if len(DOT_LEADERS.findall(text)) >= MAX_DOT_LEADER_RUNS:
        return False

    words = text.split()

    markers = len(CITATION_MARKER.findall(text))
    if markers >= MIN_CITATION_MARKERS and markers / max(len(words), 1) > MAX_CITATION_DENSITY:
        return False

    if len(words) >= ANSWERABLE_MIN_WORDS:
        return True

    # Short and mostly numeric or punctuation is chart or front-matter debris.
    non_prose = sum(1 for c in text if c.isdigit() or c in "%.,:;|/-()[]")
    if non_prose / max(len(text), 1) > MAX_NON_PROSE_RATIO:
        return False

    # Short but sentence-like is acceptable: it needs real words to read aloud.
    return sum(1 for w in words if len(w) >= 4 and w.isalpha()) >= 3


def _merge_undersized(chunks: list[Chunk]) -> list[Chunk]:
    """Fold chunks below the floor into the previous chunk of the same section.

    A nine-word fragment is not an answer. Merging keeps the text rather than
    discarding it, and only within a section so unrelated passages never join.
    """
    merged: list[Chunk] = []
    for chunk in chunks:
        if (
            merged
            and chunk.kind == "prose"
            and merged[-1].kind == "prose"
            and chunk.word_count < MIN_WORDS
            and merged[-1].section_path == chunk.section_path
            and merged[-1].word_count + chunk.word_count <= MAX_WORDS
        ):
            merged[-1].content = f"{merged[-1].content} {chunk.content}".strip()
            continue
        merged.append(chunk)

    # A short answer alone in its section has nothing to merge with, and joining
    # it to a neighbouring section would splice unrelated content. Prepending its
    # own heading makes it self-contained instead — and an FAQ record that opens
    # with the question matches a caller asking that question far better than the
    # bare answer does.
    for chunk in merged:
        if chunk.kind != "prose" or chunk.word_count >= MIN_WORDS:
            continue
        heading = chunk.section_path.split(" > ")[-1].strip()
        if heading and heading.lower() not in chunk.content[: len(heading) + 8].lower():
            chunk.content = f"{heading}\n{chunk.content}"

    return merged


def chunk_document(
    text: str, doc_id: str, title: str, source_type: str, tables: list[list[list[str]]] | None = None
) -> list[Chunk]:
    """Split one document into records, choosing the strategy by source type."""
    text = strip_metadata_lines(text)

    if source_type in ("internal_document", "internal_data") and re.search(
        r"^#{1,6}\s+", text, re.M
    ):
        chunks = _chunk_markdown(text, doc_id, title)
    else:
        chunks = _chunk_prose(text, doc_id, title)

    # Tables extracted separately from PDFs, which never appear in the text.
    for table in tables or []:
        rows = ["| " + " | ".join(cells) + " |" for cells in table]
        chunks.extend(
            _chunk_table_rows(rows, f"{title} > table", doc_id, len(chunks))
        )

    chunks = _merge_undersized([c for c in chunks if c.content.strip()])

    # Renumber so ordinals are contiguous after nested packing and merging.
    for index, chunk in enumerate(chunks):
        chunk.ordinal = index
    return chunks
