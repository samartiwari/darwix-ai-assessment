# Voice AI Assessment

A knowledge-grounded voice agent, the production knowledge base behind it,
localized agents for the Philippines and Indonesia, and a real-time pipeline
that produces coaching nudges while a call is still in progress.

All four share one codebase: a `core/` layer of speech, language, retrieval and
telemetry adapters, with thin applications on top. See
[docs/architecture.md](docs/architecture.md) for the design,
[docs/decisions.md](docs/decisions.md) for why each choice was made, and
[docs/provider-verification.md](docs/provider-verification.md) for measured
provider performance.

## Status

| Part | Scope | State |
|---|---|---|
| Q2 | Knowledge base — ingestion, cleaning, PII handling, hybrid retrieval | not started |
| Q1 | Health-insurance lead qualification voice agent, grounded in Q2 | not started |
| Q3 | Philippines (Taglish life insurance) and Indonesia (Bahasa multifinance) agents | not started |
| Q4 | Live streaming transcription, signal extraction and nudge delivery | not started |

## Requirements

Python 3.12. No GPU required — speech recognition and embeddings run on CPU at
usable speed (measured real-time factor 0.4 for transcription). No `ffmpeg`
needed: the browser captures raw PCM directly.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
cp .env.example .env      # then fill in the keys you have
python scripts/smoke_test.py
```

Only `GROQ_API_KEY` is needed to start; every other provider either has a local
fallback or needs no key at all.

Run `scripts/smoke_test.py` before anything else. It verifies speech
recognition, synthesis, embeddings and the language model, reporting each with a
timing, and skips rather than fails when an optional key is absent.

## Layout

```
core/            speech, language, TTS, telemetry and knowledge-base modules
├── kb/          ingestion, cleaning, chunking, embedding, retrieval
apps/
├── voice/       turn engine and web calling interface (Q1 and Q3)
├── packs/       per-market configuration: language, prompt, rules, voice
└── nudges/      streaming pipeline and live dashboard (Q4)
data/            raw and intermediate ingestion artifacts (not committed)
deliverables/    recordings, transcripts, test results and reports per part
docs/            architecture, decisions, limitations
scripts/         build and evaluation entry points
```

## Security

No credentials, keys or real customer data are committed. `.env` is ignored;
[.env.example](.env.example) documents every variable. Personal data in the
source content is detected and masked during ingestion, and records carrying it
are flagged before they reach the index.
