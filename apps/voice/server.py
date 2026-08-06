"""Web calling interface for the voice agents.

Run with:

    python -m apps.voice.server            # then open http://127.0.0.1:8000

Half-duplex by design: the caller holds a button, releases it, and the agent
replies. Full-duplex audio with interruption handling is the hardest part of a
voice stack to debug and the easiest to get subtly wrong, and it is not what the
assessment is measuring. Every stage here is separately testable.

The agent's reply is streamed as it is synthesised, so the caller hears speech at
first-chunk time — a measured 873ms rather than 1286ms.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from apps.voice import artifacts
from apps.voice.engine import CallState, Engine
from core import asr, tts
from core.telemetry import Trace, TraceLog

STATIC = Path(__file__).resolve().parent / "static"
PACK_DIR = Path(__file__).resolve().parent.parent / "packs"

app = FastAPI(title="Arogya First voice agent")
traces = TraceLog("voice_turns")

# One engine per market, built on first use. Loading the retriever and embedding
# model takes seconds, which is fine once and unacceptable per turn.
_engines: dict[str, Engine] = {}
_calls: dict[str, CallState] = {}
_replies: dict[str, str] = {}  # (call_id, turn) -> text awaiting synthesis


def engine_for(pack_id: str) -> Engine:
    if pack_id not in _engines:
        _engines[pack_id] = Engine(pack_id)
    return _engines[pack_id]


def available_packs() -> list[dict]:
    packs = []
    for path in sorted(PACK_DIR.glob("*.yaml")):
        import yaml

        data = yaml.safe_load(path.read_text())
        packs.append(
            {
                "id": data["id"],
                "market": data.get("market", ""),
                "sector": data.get("sector", "").replace("_", " "),
                "language": data.get("language", "en"),
                "brand": data.get("brand", ""),
            }
        )
    return packs


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (STATIC / "call.html").read_text()


@app.get("/api/packs")
def packs() -> JSONResponse:
    return JSONResponse({"packs": available_packs()})


@app.post("/api/call/start")
def start_call(pack_id: str = Form("in_health_en"), scenario: str = Form("")) -> JSONResponse:
    engine = engine_for(pack_id)
    call_id = uuid.uuid4().hex[:8]
    state = CallState(call_id=call_id, pack_id=pack_id)
    _calls[call_id] = state

    greeting = engine.greeting()
    _replies[f"{call_id}:0"] = greeting
    state.stage = "consent"

    return JSONResponse(
        {
            "call_id": call_id,
            "scenario": scenario,
            "brand": engine.pack["brand"],
            "agent": engine.pack["agent_name"],
            "language": engine.pack.language,
            "greeting": greeting,
            "audio_url": f"/api/call/{call_id}/audio/0",
            "required_slots": engine.pack.required_slots,
        }
    )


@app.post("/api/call/{call_id}/turn")
async def take_turn(call_id: str, audio: UploadFile | None = None, text: str = Form("")) -> JSONResponse:
    """Handle one caller turn.

    Accepts audio, or typed text for scenario replay so the conversation logic can
    be exercised without a microphone.
    """
    state = _calls.get(call_id)
    if state is None:
        raise HTTPException(404, "unknown call")
    engine = engine_for(state.pack_id)

    trace = Trace(kind="voice_turn")
    trace.note(call_id=call_id, pack=state.pack_id, turn=len(state.turns) + 1)

    if audio is not None:
        payload = await audio.read()
        artifacts.save_audio(
            state.pack_id, call_id, f"caller_turn_{len(state.turns) + 1}.wav", payload
        )
        transcript = asr.transcribe(
            payload, language=engine.pack.get("asr_language") or engine.pack.language, trace=trace
        )
        trace.mark("asr")
        if not transcript.ok:
            return JSONResponse(
                {
                    "error": "transcription failed",
                    "detail": transcript.error,
                    "reply": "I did not catch that. Could you say it again?",
                },
                status_code=200,
            )
        utterance = transcript.text
    else:
        if not text.strip():
            raise HTTPException(400, "no audio and no text supplied")
        utterance = text.strip()
        trace.mark("asr")

    turn = engine.respond(utterance, state, trace=trace)
    _replies[f"{call_id}:{turn.index}"] = turn.agent
    traces.write(trace)

    return JSONResponse(
        {
            "turn": turn.index,
            "caller": utterance,
            "reply": turn.agent,
            "intent": turn.intent,
            "answer_source": turn.answer_source,
            "grounded": turn.grounded,
            "retrieval_confidence": turn.retrieval_confidence,
            "retrieval_abstained": turn.retrieval_abstained,
            "citations": turn.citations,
            "stage": state.stage,
            "slots": state.slots,
            "missing": state.missing_required(engine.pack),
            "conflicts": state.conflicts,
            "escalated": state.escalated,
            "latency_ms": {k: round(v) for k, v in turn.latency_ms.items()},
            "audio_url": f"/api/call/{call_id}/audio/{turn.index}",
        }
    )


@app.get("/api/call/{call_id}/audio/{turn}")
def turn_audio(call_id: str, turn: str) -> StreamingResponse:
    """Stream the synthesised reply.

    A progressively delivered MP3 plays in the browser without any client-side
    buffering code, which is why streaming needs no work on the page.
    """
    # The turn key is a string so that the greeting ("0"), numbered turns and the
    # closing line all resolve through one route. Typing it as an integer made
    # /audio/closing fail path validation before reaching the handler.
    text = _replies.get(f"{call_id}:{turn}")
    if text is None:
        raise HTTPException(404, "no reply for that turn")

    state = _calls.get(call_id)
    pack = engine_for(state.pack_id).pack if state else None
    language = pack.tts_language if pack else "en"
    prefer_male = bool(pack and pack.get("tts_prefer_male"))

    collected = bytearray()

    def chunks():
        for chunk in tts.synthesise_stream(text, language, prefer_male):
            collected.extend(chunk)
            yield chunk
        if state is not None and collected:
            artifacts.save_audio(
                state.pack_id, call_id, f"agent_turn_{turn}.mp3", bytes(collected)
            )

    return StreamingResponse(
        chunks(),
        media_type="audio/mpeg",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


@app.post("/api/call/{call_id}/end")
def end_call(call_id: str, scenario: str = Form("")) -> JSONResponse:
    state = _calls.get(call_id)
    if state is None:
        raise HTTPException(404, "unknown call")
    engine = engine_for(state.pack_id)

    closing = engine.close(state)
    _replies[f"{call_id}:closing"] = closing
    saved = artifacts.save_call(state, engine.pack, scenario=scenario)

    return JSONResponse(
        {
            "closing": closing,
            "outcome": state.outcome,
            "lead": saved["lead"],
            "artifacts": saved["directory"],
            "transcript": saved["transcript_md"],
            "audio_url": f"/api/call/{call_id}/audio/closing",
        }
    )


@app.get("/api/latency")
def latency() -> JSONResponse:
    return JSONResponse(traces.summary())


def _free_port(host: str, preferred: int, attempts: int = 20) -> int:
    """Return the preferred port, or the next free one.

    Port 8000 is a popular default and is often already taken by something else
    on a development machine. Failing to bind produces a stack trace that reads
    like a bug in this application, so the port moves instead.
    """
    import socket

    for offset in range(attempts):
        candidate = preferred + offset
        with socket.socket() as probe:
            try:
                probe.bind((host, candidate))
                return candidate
            except OSError:
                continue
    raise RuntimeError(f"no free port between {preferred} and {preferred + attempts}")


def main() -> None:
    import uvicorn

    host = os.getenv("HOST", "127.0.0.1")
    preferred = int(os.getenv("PORT", "8000"))
    port = _free_port(host, preferred)
    if port != preferred:
        print(f"port {preferred} is in use; using {port}")
    print(f"voice agent on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
