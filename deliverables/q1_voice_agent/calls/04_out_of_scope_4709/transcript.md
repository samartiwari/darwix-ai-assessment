# Call 04_out_of_scope_4709 — Arogya First (India)

- **Market pack:** `in_health_en` (health insurance, lead qualification)
- **Started:** 2026-08-06T13:57:52+00:00
- **Turns:** 4
- **Outcome:** qualified
- **Escalated:** no
- **Captured:** members=1, age=45, city=Chennai, conditions=none
- **Response latency:** P50 2595.5 ms, P95 2726.0 ms

## Transcript

**Caller:** Yes, I have a minute.

**Asha:** Who would you like to cover — just yourself, or family members as well?

> intent `cooperative` · answer source `none_needed` · retrieval confidence 0.608 · **retrieval abstained**
>
> Cited: none — no factual claim made from the knowledge base

**Caller:** Before that, what will the weather be like in Mumbai tomorrow?

**Asha:** That is not something I have information on, and I would rather not guess. I can have a licensed advisor confirm it for you. Would a callback tomorrow morning work?

> intent `out_of_scope` · answer source `insufficient_context` · retrieval confidence 0.483 · **retrieval abstained**
>
> Cited: none — no factual claim made from the knowledge base

**Caller:** Alright. And what is your company share price?

**Asha:** That is not something I have information on, and I would rather not guess. I can have a licensed advisor confirm it for you. Would a callback tomorrow morning work?

> intent `out_of_scope` · answer source `insufficient_context` · retrieval confidence 0.633 · **retrieval abstained**
>
> Cited: none — no factual claim made from the knowledge base

**Caller:** Fine. I am 45, just myself, based in Chennai, no conditions.

**Asha:** And what would be your approximate budget per year for the premium?

> intent `cooperative` · answer source `none_needed` · retrieval confidence 0.652 · captured members=1, age=45, city=Chennai, conditions=none
>
> Cited: `kb_qualification_int_004_002` (Age eligibility) — internal://arogya_first_qualification_rules.md; `kb_faq_int_001_010` (What tax benefit do I get?) — internal://arogya_first_faq.md

## Lead record created

```json
{
  "lead_reference": "AF-2026-08-04_OUT_OF_SCOPE_4709",
  "created_at": "2026-08-06T13:58:12+00:00",
  "market": "in_health_en",
  "brand": "Arogya First",
  "channel": "inbound_web_call",
  "outcome": "qualified",
  "captured": {
    "members": "1",
    "age": "45",
    "city": "Chennai",
    "conditions": "none"
  },
  "missing_required": [],
  "unresolved_conflicts": [],
  "escalated": false,
  "escalation_reason": null,
  "requires_underwriter_review": false,
  "turns": 4,
  "records_cited": [
    "kb_qualification_int_004_002",
    "kb_faq_int_001_010"
  ],
  "note": "Preliminary eligibility only. No cover is promised and premiums quoted on the call are indicative and subject to underwriting."
}
```

## Per-turn latency

| Turn | Retrieval | Generation | Total |
|---|---|---|---|
| 1 | 24 ms | 594 ms | 2117 ms |
| 2 | 29 ms | 703 ms | 2726 ms |
| 3 | 27 ms | 566 ms | 2215 ms |
| 4 | 28 ms | 655 ms | 2596 ms |

Transcription and synthesis are timed separately in the server trace log; the figures above cover the turn from transcript to generated reply.
