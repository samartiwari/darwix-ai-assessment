# Recorded call results — in_health_en

Generated 2026-08-06 17:52 UTC by `python scripts/record_calls.py`.

The caller's side of each call is synthesised in a separate voice and then transcribed through the same speech-recognition path a live call uses. The transcript, not the script, is what reached the agent, so these calls exercise transcription as well as the conversation logic.

## Summary

| Measure | Value |
|---|---|
| Calls recorded | 5 |
| Turns | 22 |
| Turns answered from the knowledge base | 2 |
| Turns where the agent stated it had no information | 2 |
| Turns with an unverifiable figure (fallback triggered) | 0 |
| Distinct records cited | 8 |
| Caller turns transcribed word for word | 13/22 |
| Turn latency, live path, P50 / P95 | 1056.9 ms / 1771.1 ms |
| Turn latency including caller synthesis (harness only) | 2264.9 ms |

The live path measured here is transcription, retrieval and generation — the caller finishing speaking to the reply being ready. Speaking the reply adds a further 873 ms to first audio, measured separately, since synthesis streams and the caller hears the opening words before the rest is produced. The harness also synthesises the caller's own speech to produce the recordings, which a live call never does, so that cost is listed on its own rather than folded into the turn figure.

### Component latency, live path

| Component | P50 | P95 | Samples |
|---|---|---|---|
| asr | 391.4 ms | 483.0 ms | 22 |
| llm | 610.8 ms | 1110.9 ms | 22 |
| retrieval | 26.2 ms | 29.1 ms | 22 |

## Scenario coverage

| Scenario | Demonstrates | Outcome | Verdict |
|---|---|---|---|
| [01_cooperative](01_cooperative_9bb9/transcript.md) | Cooperative customer through to a created lead | qualified | as expected |
| [02_objection](02_objection_c3e3/transcript.md) | Objection handled from approved material, grounded | qualified | as expected |
| [03_conflicting_details](03_conflicting_details_3083/transcript.md) | Incomplete and conflicting details, agent asks rather than guesses | incomplete | as expected |
| [04_out_of_scope](04_out_of_scope_4709/transcript.md) | Out-of-scope question refused instead of answered | qualified | as expected |
| [05_human_escalation](05_human_escalation_0b57/transcript.md) | Caller asks for a person and is handed over | escalated | as expected |

## Calls

### 01_cooperative — Cooperative customer through to a created lead

Audio: `deliverables/q1_voice_agent/calls/01_cooperative_9bb9/call_full.mp3` · transcript: `deliverables/q1_voice_agent/calls/01_cooperative_9bb9/transcript.md` · lead: `deliverables/q1_voice_agent/calls/01_cooperative_9bb9/lead.json`

| # | Caller (as transcribed) | Agent | Source | Confidence | Cited |
|---|---|---|---|---|---|
| 1 | Yes that is fine, please go ahead. | Who would you like to cover — just yourself, or family members as well? | none_needed | 0.65 | `kb_process_int_005_001`, `kb_qualification_int_004_002` |
| 2 | I want to cover myself, my wife and our two children. | Alright, so there are four members in your family to be covered. And the age of the eldest | none_needed (abstained) | 0.634 | — |
| 3 | I am 38, the eldest of us. | Which city are you in? | none_needed (abstained) | 0.535 | — |
| 4 | We live in Pune. | Has anyone to be covered been diagnosed with or treated for any medical condition — diabet | none_needed (abstained) | 0.539 | — |
| 5 | Nobody has any medical conditions, we are all healthy. | That's great to hear. Can you please tell me what kind of budget you have in mind for the  | none_needed (abstained) | 0.633 | — |
| 6 | My budget is around $22,000 a year. | I've noted that, however, I'd like to clarify that our conversation is in Indian rupees, s | none_needed | 0.641 | `kb_qualification_int_004_005`, `kb_objection_int_002_001` |

Lead outcome: **qualified** — captured {'members': '4', 'age': '38', 'city': 'Pune', 'conditions': 'none', 'budget': 'Rs 18 lakhs'}

### 02_objection — Objection handled from approved material, grounded

Audio: `deliverables/q1_voice_agent/calls/02_objection_c3e3/call_full.mp3` · transcript: `deliverables/q1_voice_agent/calls/02_objection_c3e3/transcript.md` · lead: `deliverables/q1_voice_agent/calls/02_objection_c3e3/lead.json`

| # | Caller (as transcribed) | Agent | Source | Confidence | Cited |
|---|---|---|---|---|---|
| 1 | Yes, go ahead. | Who would you like to cover — just yourself, or family members as well? | none_needed (abstained) | 0.638 | — |
| 2 | Just myself, I am 41, and I live in Bangalore. | Alright, so you're 41 years old and based in Bangalore, and you're looking to cover just y | none_needed (abstained) | 0.5 | — |
| 3 | No conditions at all. | Alright, so you don't have any pre-existing medical conditions. What's your approximate bu | none_needed | 0.658 | `kb_qualification_int_004_004`, `kb_objection_int_002_009` |
| 4 | Honestly, this sounds far too expensive for me. | I understand your concern about the cost, but let me ask, have you considered a top-up pla | context | 0.648 | `kb_objection_int_002_001` |
| 5 | I already have cover through my employer anyway. | That's great that you have employer cover, but keep in mind that it usually ends when your | context | 0.745 | `kb_objection_int_002_002` |

Lead outcome: **qualified** — captured {'members': '1', 'age': '41', 'city': 'Bangalore', 'conditions': 'None'}

### 03_conflicting_details — Incomplete and conflicting details, agent asks rather than guesses

Audio: `deliverables/q1_voice_agent/calls/03_conflicting_details_3083/call_full.mp3` · transcript: `deliverables/q1_voice_agent/calls/03_conflicting_details_3083/transcript.md` · lead: `deliverables/q1_voice_agent/calls/03_conflicting_details_3083/lead.json`

| # | Caller (as transcribed) | Agent | Source | Confidence | Cited |
|---|---|---|---|---|---|
| 1 | Sure. | Who would you like to cover — just yourself, or family members as well? | none_needed (abstained) | 0.605 | — |
| 2 | It is just for me, I am 30 years old. | Alright, so it's just you, and you're 30 years old. Where are you based in India? | none_needed (abstained) | 0.579 | — |
| 3 | Actually, I was born in 1975. | I've noted that. Which city are you in? | none_needed (abstained) | 0.48 | — |
| 4 | I would rather not say which city. | That's okay, let's move on. Has anyone to be covered been diagnosed with or treated for an | none_needed (abstained) | 0.58 | — |

Contradictions detected: age was given as '30' and now as '51'; age: 30 does not match implied age from birth year 1975; age was given as '30' and now as '51'; age: 30 does not match implied age from birth year 1975

Lead outcome: **incomplete** — captured {'members': '1', 'age': '30'}

### 04_out_of_scope — Out-of-scope question refused instead of answered

Audio: `deliverables/q1_voice_agent/calls/04_out_of_scope_4709/call_full.mp3` · transcript: `deliverables/q1_voice_agent/calls/04_out_of_scope_4709/transcript.md` · lead: `deliverables/q1_voice_agent/calls/04_out_of_scope_4709/lead.json`

| # | Caller (as transcribed) | Agent | Source | Confidence | Cited |
|---|---|---|---|---|---|
| 1 | Yes, I have a minute. | Who would you like to cover — just yourself, or family members as well? | none_needed (abstained) | 0.608 | — |
| 2 | Before that, what will the weather be like in Mumbai tomorrow? | That is not something I have information on, and I would rather not guess. I can have a li | insufficient_context (abstained) | 0.483 | — |
| 3 | Alright. And what is your company share price? | That is not something I have information on, and I would rather not guess. I can have a li | insufficient_context (abstained) | 0.633 | — |
| 4 | Fine. I am 45, just myself, based in Chennai, no conditions. | And what would be your approximate budget per year for the premium? | none_needed | 0.652 | `kb_qualification_int_004_002`, `kb_faq_int_001_010` |

Lead outcome: **qualified** — captured {'members': '1', 'age': '45', 'city': 'Chennai', 'conditions': 'none'}

### 05_human_escalation — Caller asks for a person and is handed over

Audio: `deliverables/q1_voice_agent/calls/05_human_escalation_0b57/call_full.mp3` · transcript: `deliverables/q1_voice_agent/calls/05_human_escalation_0b57/transcript.md` · lead: `deliverables/q1_voice_agent/calls/05_human_escalation_0b57/lead.json`

| # | Caller (as transcribed) | Agent | Source | Confidence | Cited |
|---|---|---|---|---|---|
| 1 | Yes, all right. | Who would you like to cover — just yourself, or family members as well? | none_needed (abstained) | 0.514 | — |
| 2 | My father is 67 and he had a cardiac stent fitted in 2019. | I've noted that your father is 67 and had a cardiac stent fitted in 2019. And how many peo | none_needed (abstained) | 0.61 | — |
| 3 | I would rather just speak to a real person about this please. | Of course. I will arrange for a licensed advisor to speak with you. They will call you bac | none_needed (abstained) | 0.633 | — |

Lead outcome: **escalated** — captured {'age': '67', 'conditions': 'cardiac stent fitted in 2019'}

## Transcription accuracy

Word-for-word agreement is a strict measure: punctuation and spoken numerals differ from their written form even when the meaning is carried perfectly. Every mismatch is listed so the difference can be judged rather than summarised.

| Spoken | Transcribed | Word for word |
|---|---|---|
| Yes that is fine, please go ahead. | Yes that is fine, please go ahead. | yes |
| I want to cover myself, my wife and our two children. | I want to cover myself, my wife and our two children. | yes |
| I am thirty eight, the eldest of us. | I am 38, the eldest of us. | no |
| We live in Pune. | We live in Pune. | yes |
| Nobody has any medical conditions, we are all healthy. | Nobody has any medical conditions, we are all healthy. | yes |
| My budget is around twenty two thousand a year. | My budget is around $22,000 a year. | no |
| Yes go ahead. | Yes, go ahead. | no |
| Just myself, I am forty one, and I live in Bengaluru. | Just myself, I am 41, and I live in Bangalore. | no |
| No conditions at all. | No conditions at all. | yes |
| Honestly, this sounds far too expensive for me. | Honestly, this sounds far too expensive for me. | yes |
| I already have cover through my employer anyway. | I already have cover through my employer anyway. | yes |
| Sure. | Sure. | yes |
| It is just for me, I am thirty years old. | It is just for me, I am 30 years old. | no |
| Actually, I was born in nineteen seventy five. | Actually, I was born in 1975. | no |
| I would rather not say which city. | I would rather not say which city. | yes |
| Yes, I have a minute. | Yes, I have a minute. | yes |
| Before that, what will the weather be like in Mumbai tomorrow? | Before that, what will the weather be like in Mumbai tomorrow? | yes |
| Alright. And what is your company share price? | Alright. And what is your company share price? | yes |
| Fine. I am forty five, just myself, based in Chennai, no conditi | Fine. I am 45, just myself, based in Chennai, no conditions. | no |
| Yes alright. | Yes, all right. | no |
| My father is sixty seven and he had a cardiac stent fitted in tw | My father is 67 and he had a cardiac stent fitted in 2019. | no |
| I would rather just speak to a real person about this please. | I would rather just speak to a real person about this please. | yes |

## Records cited across all calls

- `kb_faq_int_001_010`
- `kb_objection_int_002_001`
- `kb_objection_int_002_002`
- `kb_objection_int_002_009`
- `kb_process_int_005_001`
- `kb_qualification_int_004_002`
- `kb_qualification_int_004_004`
- `kb_qualification_int_004_005`
