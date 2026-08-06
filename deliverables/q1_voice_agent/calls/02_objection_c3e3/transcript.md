# Call 02_objection_c3e3 — Arogya First (India)

- **Market pack:** `in_health_en` (health insurance, lead qualification)
- **Started:** 2026-08-06T13:57:10+00:00
- **Turns:** 5
- **Outcome:** qualified
- **Escalated:** no
- **Captured:** members=1, age=41, city=Bangalore, conditions=None
- **Response latency:** P50 2473.9 ms, P95 2830.5 ms

## Transcript

**Caller:** Yes, go ahead.

**Asha:** Who would you like to cover — just yourself, or family members as well?

> intent `cooperative` · answer source `none_needed` · retrieval confidence 0.638 · **retrieval abstained**
>
> Cited: none — no factual claim made from the knowledge base

**Caller:** Just myself, I am 41, and I live in Bangalore.

**Asha:** Alright, so you're 41 years old and based in Bangalore, and you're looking to cover just yourself. Do you have any pre-existing medical conditions I should know about?

> intent `cooperative` · answer source `none_needed` · retrieval confidence 0.5 · **retrieval abstained** · captured members=1, age=41, city=Bangalore
>
> Cited: none — no factual claim made from the knowledge base

**Caller:** No conditions at all.

**Asha:** Alright, so you don't have any pre-existing medical conditions. What's your approximate budget for the premium, per year?

> intent `cooperative` · answer source `none_needed` · retrieval confidence 0.658 · captured conditions=None
>
> Cited: `kb_qualification_int_004_004` (Declared conditions) — internal://arogya_first_qualification_rules.md; `kb_objection_int_002_009` ("I do not want to share my medical details on a recorded call") — internal://arogya_first_objections.md

**Caller:** Honestly, this sounds far too expensive for me.

**Asha:** I understand your concern about the cost, but let me ask, have you considered a top-up plan, which could be more affordable, especially since you're already in a relatively lower-priced zone like Bangalore, and you can also claim a tax deduction under Section 80D?

> intent `objection` · answer source `context` · retrieval confidence 0.648
>
> Cited: `kb_objection_int_002_001` ("It is too expensive") — internal://arogya_first_objections.md

**Caller:** I already have cover through my employer anyway.

**Asha:** That's great that you have employer cover, but keep in mind that it usually ends when your employment ends, and the cover amount is often limited to around 5 lakhs. A personal policy like ours can provide continuity and higher coverage, and you might consider a Secure Top-up to raise your total limit.

> intent `objection` · answer source `context` · retrieval confidence 0.745
>
> Cited: `kb_objection_int_002_002` ("I already have cover from my employer") — internal://arogya_first_objections.md

## Lead record created

```json
{
  "lead_reference": "AF-2026-08-02_OBJECTION_C3E3",
  "created_at": "2026-08-06T13:57:33+00:00",
  "market": "in_health_en",
  "brand": "Arogya First",
  "channel": "inbound_web_call",
  "outcome": "qualified",
  "captured": {
    "members": "1",
    "age": "41",
    "city": "Bangalore",
    "conditions": "None"
  },
  "missing_required": [],
  "unresolved_conflicts": [],
  "escalated": false,
  "escalation_reason": null,
  "requires_underwriter_review": false,
  "turns": 5,
  "records_cited": [
    "kb_qualification_int_004_004",
    "kb_objection_int_002_009",
    "kb_objection_int_002_001",
    "kb_objection_int_002_002"
  ],
  "note": "Preliminary eligibility only. No cover is promised and premiums quoted on the call are indicative and subject to underwriting."
}
```

## Per-turn latency

| Turn | Retrieval | Generation | Total |
|---|---|---|---|
| 1 | 27 ms | 520 ms | 2013 ms |
| 2 | 29 ms | 641 ms | 2581 ms |
| 3 | 25 ms | 726 ms | 2265 ms |
| 4 | 29 ms | 761 ms | 2474 ms |
| 5 | 24 ms | 1322 ms | 2831 ms |

Transcription and synthesis are timed separately in the server trace log; the figures above cover the turn from transcript to generated reply.
