# Recorded call results — ph_life_taglish

Generated 2026-08-06 18:26 UTC by `python scripts/record_calls.py`.

The caller's side of each call is synthesised in a separate voice and then transcribed through the same speech-recognition path a live call uses. The transcript, not the script, is what reached the agent, so these calls exercise transcription as well as the conversation logic.

## Summary

| Measure | Value |
|---|---|
| Calls recorded | 1 |
| Turns | 3 |
| Turns answered from the knowledge base | 0 |
| Turns where the agent stated it had no information | 0 |
| Turns with an unverifiable figure (fallback triggered) | 0 |
| Distinct records cited | 2 |
| Caller turns transcribed word for word | 2/3 |
| Turn latency, live path, P50 / P95 | 1453.1 ms / 14634.0 ms |
| Turn latency including caller synthesis (harness only) | 2456.1 ms |

The live path measured here is transcription, retrieval and generation — the caller finishing speaking to the reply being ready. Speaking the reply adds a further 873 ms to first audio, measured separately, since synthesis streams and the caller hears the opening words before the rest is produced. The harness also synthesises the caller's own speech to produce the recordings, which a live call never does, so that cost is listed on its own rather than folded into the turn figure.

### Component latency, live path

| Component | P50 | P95 | Samples |
|---|---|---|---|
| asr | 370.6 ms | 665.7 ms | 3 |
| llm | 697.5 ms | 962.8 ms | 3 |
| retrieval | 119.8 ms | 13270.9 ms | 3 |

## Scenario coverage

| Scenario | Demonstrates | Outcome | Verdict |
|---|---|---|---|
| [ph_03_lapse_then_human](ph_03_lapse_then_human_36b1/transcript.md) | Lapsed-policy question, then a request for a person, staying in Filipino | incomplete | outcome was incomplete, expected escalated; escalated was False, expected True |

## Calls

### ph_03_lapse_then_human — Lapsed-policy question, then a request for a person, staying in Filipino

Audio: `deliverables/q3_multilingual/calls/ph_03_lapse_then_human_36b1/call_full.mp3` · transcript: `deliverables/q3_multilingual/calls/ph_03_lapse_then_human_36b1/transcript.md` · lead: `deliverables/q3_multilingual/calls/ph_03_lapse_then_human_36b1/lead.json`

| # | Caller (as transcribed) | Agent | Source | Confidence | Cited |
|---|---|---|---|---|---|
| 1 | Opo, kapatid po ako ng policyholder. | Sige po, Ma'am. Kayo po ba mismo ang may hawak ng policy documents, o kaya po sa policyhol | none_needed | 0.515 | `kb_objection_int_009_004`, `kb_objection_int_009_007` |
| 2 | Nalaps na po daw yung policy niya, pwede pa po ba i-reinstate? | Ma'am, may problema po sa system namin ngayon, at ayaw ko pong magbigay ng maling impormas | model_error | 0.676 | — |
| 3 | Ay, mas okay na po sa akin makausap ang tunay na tao. | Ma'am, may problema po sa system namin ngayon, at ayaw ko pong magbigay ng maling impormas | model_error | 0.582 | — |

Lead outcome: **incomplete** — captured nothing

## Transcription accuracy

Word-for-word agreement is a strict measure: punctuation and spoken numerals differ from their written form even when the meaning is carried perfectly. Every mismatch is listed so the difference can be judged rather than summarised.

| Spoken | Transcribed | Word for word |
|---|---|---|
| Opo, kapatid po ako ng policyholder. | Opo, kapatid po ako ng policyholder. | yes |
| Na-lapse na po daw yung policy niya, pwede pa po ba i-reinstate? | Nalaps na po daw yung policy niya, pwede pa po ba i-reinstate? | no |
| Ay, mas okay na po sa akin makausap ang tunay na tao. | Ay, mas okay na po sa akin makausap ang tunay na tao. | yes |

## Records cited across all calls

- `kb_objection_int_009_004`
- `kb_objection_int_009_007`
