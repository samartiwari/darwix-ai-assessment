"""Speech recognition with an automatic local fallback.

Groq's hosted Whisper is the primary path at roughly 0.25s per utterance. When it
is unavailable or rate-limited — which a free tier will be — transcription falls
back to faster-whisper running locally, measured at a real-time factor of about
0.4 on CPU. The call continues either way, and which provider served the request
is recorded on the trace rather than hidden.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from core.telemetry import Trace


@dataclass
class Transcript:
    text: str
    language: str = ""
    provider: str = ""
    model: str = ""
    duration_s: float = 0.0
    fell_back: bool = False
    error: str | None = None

    @property
    def ok(self) -> bool:
        return bool(self.text.strip()) and self.error is None


def _provider() -> str:
    return os.getenv("ASR_PROVIDER", "groq").lower()


def _hosted_model() -> str:
    return os.getenv("ASR_MODEL", "whisper-large-v3-turbo")


def _local_model_size() -> str:
    return os.getenv("ASR_LOCAL_MODEL", "small")


@lru_cache(maxsize=2)
def _local_model(size: str):
    from faster_whisper import WhisperModel

    # int8 on CPU is the configuration measured in provider verification. A GPU
    # build additionally needs cuDNN, which is easy to misconfigure and buys
    # nothing here, since the local path is a fallback rather than the hot path.
    return WhisperModel(size, device="cpu", compute_type="int8")


def _transcribe_local(audio: Path | bytes, language: str | None) -> Transcript:
    import io

    size = _local_model_size()
    model = _local_model(size)
    source = str(audio) if isinstance(audio, Path) else io.BytesIO(audio)
    segments, info = model.transcribe(
        source,
        beam_size=1,          # greedy: the fallback path favours latency
        language=language,
        vad_filter=True,
    )
    text = " ".join(segment.text.strip() for segment in segments).strip()
    return Transcript(
        text=text,
        language=getattr(info, "language", "") or (language or ""),
        provider="local",
        model=f"faster-whisper-{size}",
        duration_s=float(getattr(info, "duration", 0.0) or 0.0),
    )


def _transcribe_groq(audio: Path | bytes, language: str | None) -> Transcript:
    from groq import Groq

    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY is not set")

    payload = audio.read_bytes() if isinstance(audio, Path) else audio
    name = audio.name if isinstance(audio, Path) else "turn.wav"

    client = Groq(api_key=key)
    kwargs = {"file": (name, payload), "model": _hosted_model()}
    if language:
        kwargs["language"] = language

    response = client.audio.transcriptions.create(**kwargs)
    return Transcript(
        text=(response.text or "").strip(),
        language=language or getattr(response, "language", "") or "",
        provider="groq",
        model=_hosted_model(),
    )


def transcribe(
    audio: Path | bytes,
    language: str | None = None,
    trace: Trace | None = None,
) -> Transcript:
    """Transcribe one utterance.

    `language` is an ISO code hint. Passing it matters for the localized agents:
    left to auto-detection, a short Taglish utterance is sometimes tagged as
    English and transcribed with English spelling conventions.
    """
    primary = _provider()

    if primary == "groq":
        try:
            result = _transcribe_groq(audio, language)
            if trace:
                trace.note(asr_provider=result.provider, asr_model=result.model)
            return result
        except Exception as exc:  # noqa: BLE001 - falling back is the point
            reason = f"{type(exc).__name__}: {exc}"
            try:
                result = _transcribe_local(audio, language)
                result.fell_back = True
                if trace:
                    trace.note(
                        asr_provider=result.provider,
                        asr_model=result.model,
                        asr_fallback_reason=reason,
                    )
                return result
            except Exception as local_exc:  # noqa: BLE001
                if trace:
                    trace.note(asr_error=reason)
                return Transcript(
                    text="",
                    provider="none",
                    error=f"hosted failed ({reason}); local failed ({local_exc})",
                )

    try:
        result = _transcribe_local(audio, language)
        if trace:
            trace.note(asr_provider=result.provider, asr_model=result.model)
        return result
    except Exception as exc:  # noqa: BLE001
        return Transcript(text="", provider="none", error=f"{type(exc).__name__}: {exc}")
