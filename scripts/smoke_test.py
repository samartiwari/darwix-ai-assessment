"""Verify every external and local provider before building on it.

Run this first on any machine:

    python scripts/smoke_test.py

Each check reports PASS, FAIL or SKIP with a timing, so a provider that is
merely slow is distinguishable from one that is broken. Checks needing a key
are skipped rather than failed when the key is absent.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
SCRATCH = ROOT / "scratch"
load_dotenv(ROOT / ".env")

# Phrases chosen to exercise the code-switching the market packs rely on:
# English finance nouns inside Tagalog and Indonesian grammar.
PHRASES = {
    "en-US-AriaNeural": "Your family floater plan covers a room rent of five thousand rupees per day.",
    "fil-PH-BlessicaNeural": "Ma'am, na-miss po yung due date ng premium niyo, pwede po natin i-settle ngayon?",
    "id-ID-GadisNeural": "Pak, cicilan bulan ini sudah jatuh tempo, tenor sisa lima bulan lagi ya.",
}


@dataclass
class Result:
    name: str
    status: str  # PASS | FAIL | SKIP
    detail: str
    seconds: float = 0.0
    artifacts: list[Path] = field(default_factory=list)


def _timed(fn):
    start = time.perf_counter()
    try:
        detail, artifacts = fn()
        return "PASS", detail, time.perf_counter() - start, artifacts
    except Exception as exc:  # noqa: BLE001 - smoke test reports, never raises
        return "FAIL", f"{type(exc).__name__}: {exc}", time.perf_counter() - start, []


def check_edge_tts_voices() -> Result:
    """Confirm Microsoft actually publishes the Filipino and Indonesian voices."""

    def run():
        import edge_tts

        voices = asyncio.run(edge_tts.list_voices())
        names = {v["ShortName"] for v in voices}
        wanted = {
            "fil-PH": [n for n in names if n.startswith("fil-PH")],
            "id-ID": [n for n in names if n.startswith("id-ID")],
        }
        missing = [loc for loc, found in wanted.items() if not found]
        if missing:
            raise RuntimeError(f"no voices published for {missing}")
        summary = "; ".join(
            f"{loc}: {', '.join(sorted(v.split('-')[-1].replace('Neural', '') for v in found))}"
            for loc, found in wanted.items()
        )
        return f"{len(names)} voices total — {summary}", []

    status, detail, secs, arts = _timed(run)
    return Result("edge-tts voice catalogue", status, detail, secs, arts)


def check_edge_tts_synthesis() -> Result:
    """Synthesize one phrase per market. Doubles as ASR test material."""

    def run():
        import edge_tts

        SCRATCH.mkdir(exist_ok=True)
        made = []
        for voice, text in PHRASES.items():
            out = SCRATCH / f"smoke_{voice.split('Neural')[0]}.mp3"

            async def synth(v=voice, t=text, o=out):
                await edge_tts.Communicate(t, v).save(str(o))

            asyncio.run(synth())
            if not out.exists() or out.stat().st_size < 1000:
                raise RuntimeError(f"{voice} produced no usable audio")
            made.append(out)
        sizes = ", ".join(f"{p.name} {p.stat().st_size // 1024}KB" for p in made)
        return sizes, made

    status, detail, secs, arts = _timed(run)
    return Result("edge-tts synthesis (en/fil/id)", status, detail, secs, arts)


def check_local_asr(audio: list[Path]) -> Result:
    """Local faster-whisper is the fallback when the hosted ASR is unavailable."""

    def run():
        from faster_whisper import WhisperModel

        if not audio:
            raise RuntimeError("no audio produced by the synthesis check")
        size = os.getenv("ASR_LOCAL_MODEL", "small")
        model = WhisperModel(size, device="cpu", compute_type="int8")
        lines = []
        for path in audio:
            t0 = time.perf_counter()
            segments, info = model.transcribe(str(path), beam_size=1)
            text = " ".join(s.text.strip() for s in segments)
            elapsed = time.perf_counter() - t0
            rtf = elapsed / info.duration if info.duration else 0
            lines.append(
                f"{path.stem.replace('smoke_', '')} [{info.language}] "
                f"RTF {rtf:.2f} :: {text[:70]}"
            )
        return f"model={size} | " + " | ".join(lines), []

    status, detail, secs, arts = _timed(run)
    return Result("local ASR (faster-whisper, CPU)", status, detail, secs, arts)


def check_embeddings() -> Result:
    """Embeddings run locally so indexing is never rate-limited."""

    def run():
        from sentence_transformers import SentenceTransformer

        name = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
        model = SentenceTransformer(name, device="cpu")
        pair = [
            "What is the waiting period for pre-existing diseases?",
            "How long before my existing conditions are covered?",
        ]
        unrelated = "The branch office opens at nine in the morning."
        vecs = model.encode(pair + [unrelated], normalize_embeddings=True)
        near = float(vecs[0] @ vecs[1])
        far = float(vecs[0] @ vecs[2])
        if near <= far:
            raise RuntimeError(f"paraphrase similarity {near:.2f} not above unrelated {far:.2f}")
        return f"{name} dim={vecs.shape[1]} paraphrase={near:.2f} unrelated={far:.2f}", []

    status, detail, secs, arts = _timed(run)
    return Result("local embeddings", status, detail, secs, arts)


def check_groq_llm() -> Result:
    if not os.getenv("GROQ_API_KEY"):
        return Result("Groq language model", "SKIP", "GROQ_API_KEY not set")

    def run():
        from groq import Groq

        model = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
        client = Groq(api_key=os.environ["GROQ_API_KEY"])
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Reply with exactly the word: ready"}],
            max_tokens=5,
            temperature=0,
        )
        return f"{model} -> {resp.choices[0].message.content.strip()!r}", []

    status, detail, secs, arts = _timed(run)
    return Result("Groq language model", status, detail, secs, arts)


def check_groq_asr(audio: list[Path]) -> Result:
    if not os.getenv("GROQ_API_KEY"):
        return Result("Groq speech recognition", "SKIP", "GROQ_API_KEY not set")

    def run():
        from groq import Groq

        if not audio:
            raise RuntimeError("no audio produced by the synthesis check")
        model = os.getenv("ASR_MODEL", "whisper-large-v3-turbo")
        client = Groq(api_key=os.environ["GROQ_API_KEY"])
        lines = []
        for path in audio:
            with path.open("rb") as fh:
                t0 = time.perf_counter()
                tr = client.audio.transcriptions.create(file=(path.name, fh.read()), model=model)
                lines.append(
                    f"{path.stem.replace('smoke_', '')} {time.perf_counter() - t0:.2f}s "
                    f":: {tr.text.strip()[:70]}"
                )
        return f"model={model} | " + " | ".join(lines), []

    status, detail, secs, arts = _timed(run)
    return Result("Groq speech recognition", status, detail, secs, arts)


def check_gemini() -> Result:
    if not os.getenv("GEMINI_API_KEY"):
        return Result("Gemini fallback", "SKIP", "GEMINI_API_KEY not set")

    def run():
        from google import genai

        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        resp = client.models.generate_content(
            model=model, contents="Reply with exactly the word: ready"
        )
        return f"{model} -> {resp.text.strip()!r}", []

    status, detail, secs, arts = _timed(run)
    return Result("Gemini fallback", status, detail, secs, arts)


def main() -> int:
    print("Provider smoke test\n" + "=" * 78)

    results: list[Result] = []
    results.append(check_edge_tts_voices())

    synth = check_edge_tts_synthesis()
    results.append(synth)

    results.append(check_local_asr(synth.artifacts))
    results.append(check_embeddings())
    results.append(check_groq_asr(synth.artifacts))
    results.append(check_groq_llm())
    results.append(check_gemini())

    for r in results:
        mark = {"PASS": "PASS", "FAIL": "FAIL", "SKIP": "SKIP"}[r.status]
        timing = f"{r.seconds:6.2f}s" if r.seconds else "      -"
        print(f"[{mark}] {timing}  {r.name}")
        print(f"          {r.detail}")

    failed = [r for r in results if r.status == "FAIL"]
    skipped = [r for r in results if r.status == "SKIP"]
    print("=" * 78)
    print(f"{len(results) - len(failed) - len(skipped)} passed, {len(failed)} failed, {len(skipped)} skipped")
    if skipped:
        print("Skipped checks need keys in .env — see .env.example")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
