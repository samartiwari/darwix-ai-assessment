# Call 05_human_escalation_0b57 — Arogya First (India)

- **Market pack:** `in_health_en` (health insurance, lead qualification)
- **Started:** 2026-08-06T13:58:12+00:00
- **Turns:** 3
- **Outcome:** escalated
- **Escalated:** yes — caller asked for a person
- **Captured:** age=67, conditions=cardiac stent fitted in 2019
- **Response latency:** P50 2460.5 ms, P95 2571.6 ms

## Transcript

**Caller:** Yes, all right.

**Asha:** Who would you like to cover — just yourself, or family members as well?

> intent `cooperative` · answer source `none_needed` · retrieval confidence 0.514 · **retrieval abstained**
>
> Cited: none — no factual claim made from the knowledge base

**Caller:** My father is 67 and he had a cardiac stent fitted in 2019.

**Asha:** I've noted that your father is 67 and had a cardiac stent fitted in 2019. And how many people would you like to cover under the policy?

> intent `cooperative` · answer source `none_needed` · retrieval confidence 0.61 · **retrieval abstained** · captured age=67, conditions=cardiac stent fitted in 2019
>
> Cited: none — no factual claim made from the knowledge base

**Caller:** I would rather just speak to a real person about this please.

**Asha:** Of course. I will arrange for a licensed advisor to speak with you. They will call you back at the number you are speaking from.

> intent `escalation_request` · answer source `none_needed` · retrieval confidence 0.633 · **retrieval abstained**
>
> Cited: none — no factual claim made from the knowledge base

## Lead record created

```json
{
  "lead_reference": "AF-2026-08-05_HUMAN_ESCALATION_0B57",
  "created_at": "2026-08-06T13:58:28+00:00",
  "market": "in_health_en",
  "brand": "Arogya First",
  "channel": "inbound_web_call",
  "outcome": "escalated",
  "captured": {
    "age": "67",
    "conditions": "cardiac stent fitted in 2019"
  },
  "missing_required": [
    "members",
    "city"
  ],
  "unresolved_conflicts": [],
  "escalated": true,
  "escalation_reason": "caller asked for a person",
  "requires_underwriter_review": true,
  "turns": 3,
  "records_cited": [],
  "note": "Preliminary eligibility only. No cover is promised and premiums quoted on the call are indicative and subject to underwriting."
}
```

## Per-turn latency

| Turn | Retrieval | Generation | Total |
|---|---|---|---|
| 1 | 26 ms | 509 ms | 2068 ms |
| 2 | 28 ms | 651 ms | 2461 ms |
| 3 | 28 ms | 685 ms | 2572 ms |

Transcription and synthesis are timed separately in the server trace log; the figures above cover the turn from transcript to generated reply.
