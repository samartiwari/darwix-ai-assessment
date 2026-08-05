"""Turn fetched bodies into text, and judge whether the result is usable.

Extraction succeeding technically is not the same as extraction succeeding
usefully. A site can answer with HTTP 200 and hand back a page of navigation
links; a PDF cover page yields a dozen words. Both look like content to a naive
pipeline. Every extraction is therefore scored and either accepted or rejected
with a stated reason.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber
import trafilatura

MIN_USABLE_WORDS = 150

# Phrases that mark an error page regardless of the status code returned.
ERROR_PAGE_MARKERS = (
    "page you're looking for",
    "page you’re looking for",
    "page doesn't exist",
    "page doesn’t exist",
    "page not found",
    "404 - sorry",
    "404 error",
    "may have been moved, deleted, or never existed",
    "access denied",
    "are you a robot",
    "enable javascript",
)

# Navigation and marketing chrome that appears on every page of a site and
# carries no answerable content.
BOILERPLATE_LINES = (
    "wellness corner",
    "call to buy",
    "contact us",
    "menu",
    "buy health insurance",
    "renew",
    "claim",
    "login",
    "sign in",
    "download app",
    "follow us",
    "privacy policy",
    "terms and conditions",
    "all rights reserved",
    "cookie",
    "subscribe to our newsletter",
    "toll free",
    "customer care",
    "site map",
    "sitemap",
    "share this",
    "read more",
    "view all",
    "know more",
)


@dataclass
class ExtractedDoc:
    url: str
    title: str
    text: str
    tables: list[list[list[str]]] = field(default_factory=list)
    page_count: int = 1
    source_type: str = "web_page"  # web_page | pdf
    usable: bool = True
    reason: str = ""  # why it was rejected, when it was

    @property
    def word_count(self) -> int:
        return len(self.text.split())


def _looks_like_error_page(text: str) -> str | None:
    lowered = text[:2000].lower()
    for marker in ERROR_PAGE_MARKERS:
        if marker in lowered:
            return f"error-page marker in body: {marker!r}"
    return None


def _boilerplate_ratio(text: str) -> float:
    """Share of lines that are navigation or marketing chrome."""
    lines = [ln.strip().lower() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return 1.0
    chrome = sum(
        1
        for ln in lines
        if len(ln.split()) <= 6 and any(b in ln for b in BOILERPLATE_LINES)
    )
    return chrome / len(lines)


def _judge(text: str) -> tuple[bool, str]:
    """Decide whether extracted text is worth indexing."""
    if not text.strip():
        return False, "extraction produced no text"

    marker = _looks_like_error_page(text)
    if marker is not None:
        return False, marker

    words = len(text.split())
    if words < MIN_USABLE_WORDS:
        return False, f"only {words} words extracted, below the {MIN_USABLE_WORDS} threshold"

    ratio = _boilerplate_ratio(text)
    if ratio > 0.5:
        return False, f"{ratio:.0%} of lines are navigation or marketing chrome"

    return True, ""


def extract_html(raw: bytes, url: str) -> ExtractedDoc:
    html = raw.decode("utf-8", errors="replace")

    text = (
        trafilatura.extract(
            html,
            include_tables=True,
            include_comments=False,
            favor_recall=True,
            url=url,
        )
        or ""
    )

    title = ""
    meta = trafilatura.extract_metadata(html)
    if meta is not None and meta.title:
        title = meta.title.strip()
    if not title:
        match = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
        title = re.sub(r"\s+", " ", match.group(1)).strip() if match else url

    usable, reason = _judge(text)
    return ExtractedDoc(
        url=url,
        title=title,
        text=text,
        source_type="web_page",
        usable=usable,
        reason=reason,
    )


def _table_to_rows(table: list[list[str | None]]) -> list[list[str]]:
    rows = []
    for row in table:
        cells = [re.sub(r"\s+", " ", (c or "")).strip() for c in row]
        if any(cells):
            rows.append(cells)
    return rows


def extract_pdf(raw: bytes, url: str) -> ExtractedDoc:
    """Extract text and tables page by page.

    Tables are kept as structured rows rather than flattened into the text, so
    that a row is never separated from its header during chunking.
    """
    texts: list[str] = []
    tables: list[list[list[str]]] = []
    title = ""

    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                texts.append(page_text)
            for table in page.extract_tables() or []:
                rows = _table_to_rows(table)
                if len(rows) > 1:  # a single row carries no header relationship
                    tables.append(rows)
        if pdf.metadata:
            title = (pdf.metadata.get("Title") or "").strip()

    if not title:
        title = Path(urlpath(url)).stem.replace("-", " ").replace("_", " ").strip()

    text = "\n\n".join(texts)
    usable, reason = _judge(text)

    # A long report whose text layer is thin but whose tables extracted well is
    # still valuable; the tables carry the content.
    if not usable and len(tables) >= 3:
        usable, reason = True, ""

    return ExtractedDoc(
        url=url,
        title=title,
        text=text,
        tables=tables,
        page_count=page_count,
        source_type="pdf",
        usable=usable,
        reason=reason,
    )


def urlpath(url: str) -> str:
    from urllib.parse import urlparse

    return urlparse(url).path


def extract(raw: bytes, url: str, is_pdf: bool) -> ExtractedDoc:
    return extract_pdf(raw, url) if is_pdf else extract_html(raw, url)
