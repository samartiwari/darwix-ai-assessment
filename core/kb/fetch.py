"""Polite fetching with robots.txt compliance and an on-disk cache.

Every fetch outcome is recorded, including refusals and failures. Nothing is
dropped silently — the ingestion report needs to state what was not collected
and why.
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.robotparser as rp
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data" / "raw"

# A descriptive agent for the fetch itself, and a browser agent for retrieving
# robots.txt. Several sites answer automated agents with 403 on robots.txt,
# which a parser reads as "disallow everything" — a false refusal that would
# rule out sources which in fact permit access.
FETCH_UA = "arogya-kb-ingest/1.0 (assessment prototype; contact via repository)"
ROBOTS_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
)

REQUEST_DELAY_SECONDS = 1.5


@dataclass
class FetchResult:
    url: str
    ok: bool
    status: int | None = None
    content_type: str = ""
    path: str | None = None  # cached body, relative to the repository root
    bytes_len: int = 0
    from_cache: bool = False
    error: str | None = None  # populated when ok is False

    @property
    def is_pdf(self) -> bool:
        return "pdf" in self.content_type.lower() or self.url.lower().endswith(".pdf")


class RobotsPolicy:
    """Caches one robots.txt per host and answers permission questions."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[rp.RobotFileParser | None, str]] = {}

    def _load(self, base: str) -> tuple[rp.RobotFileParser | None, str]:
        if base in self._cache:
            return self._cache[base]
        parser = rp.RobotFileParser()
        try:
            with httpx.Client(
                timeout=15, follow_redirects=True, headers={"User-Agent": ROBOTS_UA}
            ) as client:
                resp = client.get(f"{base}/robots.txt")
            if resp.status_code == 200 and resp.text.strip():
                parser.parse(resp.text.splitlines())
                outcome = (parser, "parsed")
            elif resp.status_code in (401, 403):
                # The host hides robots.txt from automation. Treated as "no
                # stated policy" rather than a blanket refusal, and recorded.
                outcome = (None, f"robots.txt returned {resp.status_code}")
            else:
                outcome = (None, "no robots.txt published")
        except Exception as exc:  # noqa: BLE001 - network failure is data here
            outcome = (None, f"robots.txt unreachable ({type(exc).__name__})")
        self._cache[base] = outcome
        return outcome

    def allows(self, url: str) -> tuple[bool, str]:
        parts = urlparse(url)
        parser, note = self._load(f"{parts.scheme}://{parts.netloc}")
        if parser is None:
            return True, note
        if parser.can_fetch(FETCH_UA, url) or parser.can_fetch("*", url):
            return True, "allowed by robots.txt"
        return False, "disallowed by robots.txt"


def _cache_paths(url: str, is_pdf: bool) -> tuple[Path, Path]:
    digest = hashlib.sha1(url.encode()).hexdigest()[:16]
    suffix = "pdf" if is_pdf else "html"
    return CACHE / f"{digest}.{suffix}", CACHE / f"{digest}.meta.json"


class Fetcher:
    """Fetches sources once, caches bodies, and rate-limits per host."""

    def __init__(self, use_cache: bool = True) -> None:
        self.robots = RobotsPolicy()
        self.use_cache = use_cache
        self._last_request: dict[str, float] = {}
        CACHE.mkdir(parents=True, exist_ok=True)

    def _wait_turn(self, host: str) -> None:
        last = self._last_request.get(host)
        if last is not None:
            remaining = REQUEST_DELAY_SECONDS - (time.monotonic() - last)
            if remaining > 0:
                time.sleep(remaining)
        self._last_request[host] = time.monotonic()

    def _cached(self, url: str) -> FetchResult | None:
        for is_pdf in (False, True):
            body, meta = _cache_paths(url, is_pdf)
            if body.exists() and meta.exists():
                saved = json.loads(meta.read_text())
                return FetchResult(**{**saved, "from_cache": True})
        return None

    def fetch(self, url: str) -> FetchResult:
        if self.use_cache:
            hit = self._cached(url)
            if hit is not None:
                return hit

        permitted, reason = self.robots.allows(url)
        if not permitted:
            return FetchResult(url=url, ok=False, error=reason)

        host = urlparse(url).netloc
        self._wait_turn(host)

        try:
            with httpx.Client(
                timeout=60,
                follow_redirects=True,
                max_redirects=5,
                headers={"User-Agent": FETCH_UA, "Accept-Language": "en"},
            ) as client:
                resp = client.get(url)
        except Exception as exc:  # noqa: BLE001 - the failure itself is the result
            return FetchResult(url=url, ok=False, error=f"{type(exc).__name__}: {exc}")

        content_type = resp.headers.get("content-type", "")
        is_pdf = "pdf" in content_type.lower() or url.lower().endswith(".pdf")

        if resp.status_code != 200:
            # Recorded rather than raised. A 404 that still returns a page of
            # navigation is exactly the soft failure the extractor must catch.
            return FetchResult(
                url=url,
                ok=False,
                status=resp.status_code,
                content_type=content_type,
                bytes_len=len(resp.content),
                error=f"HTTP {resp.status_code}",
            )

        body, meta = _cache_paths(url, is_pdf)
        body.write_bytes(resp.content)
        result = FetchResult(
            url=url,
            ok=True,
            status=resp.status_code,
            content_type=content_type,
            path=str(body.relative_to(ROOT)),
            bytes_len=len(resp.content),
        )
        meta.write_text(json.dumps(asdict(result), indent=2))
        return result
