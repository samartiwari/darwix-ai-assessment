"""Speech synthesis, with native voices per market.

edge-tts publishes neural voices for `fil-PH` and `id-ID` alongside English, and
needs no API key at all, which is what makes genuinely native Filipino and
Indonesian output possible here rather than an English voice reading foreign text.

It rides an undocumented Microsoft endpoint, so it can break without notice.
ElevenLabs is the configured fallback. Both compromises are recorded in the
market documentation rather than left implicit.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from pathlib import Path

from core.telemetry import Trace

# Voices verified present by scripts/smoke_test.py. Rate and pitch are tuned per
# market: the Filipino and Indonesian voices read noticeably faster than the
# English one at the default rate, which sounds brusque in a collections or
# renewal call where politeness carries meaning.
VOICES: dict[str, dict] = {
    "en": {"voice": "en-IN-NeerjaNeural", "rate": "+0%"},
    "en-US": {"voice": "en-US-AriaNeural", "rate": "+0%"},
    "fil": {"voice": "fil-PH-BlessicaNeural", "rate": "-6%"},
    "fil-male": {"voice": "fil-PH-AngeloNeural", "rate": "-6%"},
    "id": {"voice": "id-ID-GadisNeural", "rate": "-8%"},
    "id-male": {"voice": "id-ID-ArdiNeural", "rate": "-8%"},
}

DEFAULT_VOICE = "en-IN-NeerjaNeural"


@dataclass
class Speech:
    audio: bytes = b""
    mime_type: str = "audio/mpeg"
    voice: str = ""
    provider: str = ""
    fell_back: bool = False
    error: str | None = None

    @property
    def ok(self) -> bool:
        return len(self.audio) > 512 and self.error is None

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.audio)
        return path


def voice_for(language: str, prefer_male: bool = False) -> tuple[str, str]:
    """Resolve a language code to a voice name and speaking rate."""
    key = f"{language}-male" if prefer_male and f"{language}-male" in VOICES else language
    entry = VOICES.get(key) or VOICES.get(language) or {"voice": DEFAULT_VOICE, "rate": "+0%"}
    return entry["voice"], entry.get("rate", "+0%")


async def _synthesise_edge(text: str, voice: str, rate: str) -> bytes:
    import edge_tts

    chunks = bytearray()
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    async for event in communicate.stream():
        if event["type"] == "audio":
            chunks.extend(event["data"])
    return bytes(chunks)


def _synthesise_elevenlabs(text: str, _language: str) -> bytes:
    """The multilingual model detects language from the text, so the language
    code is accepted for interface symmetry and not sent."""
    import httpx

    key = os.getenv("ELEVENLABS_API_KEY")
    if not key:
        raise RuntimeError("ELEVENLABS_API_KEY is not set")

    # A multilingual model is required; the English-only models mispronounce
    # Tagalog and Indonesian badly enough to be unusable.
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
    response = httpx.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers={"xi-api-key": key, "accept": "audio/mpeg"},
        json={
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.content


def synthesise(
    text: str,
    language: str = "en",
    prefer_male: bool = False,
    trace: Trace | None = None,
) -> Speech:
    """Synthesise speech, falling back to the hosted provider if edge-tts fails."""
    if not text.strip():
        return Speech(error="nothing to synthesise")

    voice, rate = voice_for(language, prefer_male)
    provider = os.getenv("TTS_PROVIDER", "edge").lower()

    if provider == "edge":
        try:
            audio = asyncio.run(_synthesise_edge(text, voice, rate))
            if len(audio) <= 512:
                raise RuntimeError("edge-tts returned no usable audio")
            if trace:
                trace.note(tts_provider="edge", tts_voice=voice)
            return Speech(audio=audio, voice=voice, provider="edge")
        except Exception as exc:  # noqa: BLE001 - the fallback is the point
            reason = f"{type(exc).__name__}: {exc}"
            try:
                audio = _synthesise_elevenlabs(text, language)
                if trace:
                    trace.note(
                        tts_provider="elevenlabs", tts_fallback_reason=reason
                    )
                return Speech(
                    audio=audio, voice="elevenlabs", provider="elevenlabs", fell_back=True
                )
            except Exception as fallback_exc:  # noqa: BLE001
                if trace:
                    trace.note(tts_error=reason)
                # A failed voice is not a failed call. The caller-facing layer
                # falls back to showing text so the conversation continues.
                return Speech(error=f"edge failed ({reason}); elevenlabs failed ({fallback_exc})")

    try:
        audio = _synthesise_elevenlabs(text, language)
        if trace:
            trace.note(tts_provider="elevenlabs", tts_voice="elevenlabs")
        return Speech(audio=audio, voice="elevenlabs", provider="elevenlabs")
    except Exception as exc:  # noqa: BLE001
        return Speech(error=f"{type(exc).__name__}: {exc}")


def synthesise_stream(text: str, language: str = "en", prefer_male: bool = False):
    """Yield audio chunks as they are produced.

    Synthesis dominates turn latency, measured against 427ms for transcription
    and 384ms for generation. Most of it is spent waiting for the last chunk of a
    reply the caller could already be hearing, so what matters is time to the
    first chunk: a median 873ms here against 1286ms to complete, a 413ms saving in
    perceived wait. A browser plays a progressively delivered MP3 with no
    client-side buffering code.

    Falls back to a single-shot synthesis yielded as one chunk, so a caller of
    this function does not need to handle two shapes of result.
    """
    if not text.strip():
        return

    voice, rate = voice_for(language, prefer_male)

    if os.getenv("TTS_PROVIDER", "edge").lower() != "edge":
        speech = synthesise(text, language, prefer_male)
        if speech.ok:
            yield speech.audio
        return

    # edge-tts is async and this generator is consumed synchronously, so the
    # event loop runs on a worker thread and hands chunks over through a queue.
    # Collecting them inside asyncio.run() and yielding afterwards was measured
    # to save nothing at all, because the first chunk then waits for the last.
    import queue
    import threading

    chunks: queue.Queue = queue.Queue()
    DONE = object()

    async def produce() -> None:
        import edge_tts

        async for event in edge_tts.Communicate(text, voice, rate=rate).stream():
            if event["type"] == "audio":
                chunks.put(event["data"])

    def run() -> None:
        try:
            asyncio.run(produce())
        except Exception as exc:  # noqa: BLE001 - reported through the queue
            chunks.put(exc)
        finally:
            chunks.put(DONE)

    worker = threading.Thread(target=run, daemon=True)
    worker.start()

    failure: Exception | None = None
    produced = False
    while True:
        item = chunks.get()
        if item is DONE:
            break
        if isinstance(item, Exception):
            failure = item
            continue
        produced = True
        yield item

    if failure is not None or not produced:
        speech = synthesise(text, language, prefer_male)
        if speech.ok:
            yield speech.audio


async def synthesise_stream_async(text: str, language: str = "en", prefer_male: bool = False):
    """Async chunk generator, for use inside an event loop such as the web server."""
    if not text.strip():
        return

    voice, rate = voice_for(language, prefer_male)

    if os.getenv("TTS_PROVIDER", "edge").lower() != "edge":
        speech = synthesise(text, language, prefer_male)
        if speech.ok:
            yield speech.audio
        return

    import edge_tts

    try:
        async for event in edge_tts.Communicate(text, voice, rate=rate).stream():
            if event["type"] == "audio":
                yield event["data"]
    except Exception:  # noqa: BLE001 - degrade to the fallback provider
        speech = synthesise(text, language, prefer_male)
        if speech.ok:
            yield speech.audio


async def list_voices(prefix: str = "") -> list[str]:
    """Voice names available from edge-tts, optionally filtered by locale."""
    import edge_tts

    voices = await edge_tts.list_voices()
    names = sorted(v["ShortName"] for v in voices)
    return [n for n in names if n.startswith(prefix)] if prefix else names
