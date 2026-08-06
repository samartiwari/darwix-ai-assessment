# Call 03_conflicting_details_3083 — Arogya First (India)

- **Market pack:** `in_health_en` (health insurance, lead qualification)
- **Started:** 2026-08-06T13:57:33+00:00
- **Turns:** 4
- **Outcome:** incomplete
- **Escalated:** no
- **Captured:** members=1, age=30
- **Unresolved contradictions:** age was given as '30' and now as '51'; age: 30 does not match implied age from birth year 1975; age was given as '30' and now as '51'; age: 30 does not match implied age from birth year 1975
- **Response latency:** P50 2293.4 ms, P95 2378.7 ms

## Transcript

**Caller:** Sure.

**Asha:** Who would you like to cover — just yourself, or family members as well?

> intent `cooperative` · answer source `none_needed` · retrieval confidence 0.605 · **retrieval abstained**
>
> Cited: none — no factual claim made from the knowledge base

**Caller:** It is just for me, I am 30 years old.

**Asha:** Alright, so it's just you, and you're 30 years old. Where are you based in India?

> intent `cooperative` · answer source `none_needed` · retrieval confidence 0.579 · **retrieval abstained** · captured members=1, age=30
>
> Cited: none — no factual claim made from the knowledge base

**Caller:** Actually, I was born in 1975.

**Asha:** I've noted that. Which city are you in?

> intent `cooperative` · answer source `none_needed` · retrieval confidence 0.48 · **retrieval abstained** · **contradiction detected**
>
> Cited: none — no factual claim made from the knowledge base

**Caller:** I would rather not say which city.

**Asha:** That's okay, let's move on. Has anyone to be covered been diagnosed with or treated for any medical condition — diabetes, blood pressure, thyroid, anything else?

> intent `cooperative` · answer source `none_needed` · retrieval confidence 0.58 · **retrieval abstained** · **contradiction detected**
>
> Cited: none — no factual claim made from the knowledge base

## Lead record created

```json
{
  "lead_reference": "AF-2026-08-03_CONFLICTING_DETAILS_3083",
  "created_at": "2026-08-06T13:57:52+00:00",
  "market": "in_health_en",
  "brand": "Arogya First",
  "channel": "inbound_web_call",
  "outcome": "incomplete",
  "captured": {
    "members": "1",
    "age": "30"
  },
  "missing_required": [
    "city",
    "conditions"
  ],
  "unresolved_conflicts": [
    "age was given as '30' and now as '51'",
    "age: 30 does not match implied age from birth year 1975",
    "age was given as '30' and now as '51'; age: 30 does not match implied age from birth year 1975"
  ],
  "escalated": false,
  "escalation_reason": null,
  "requires_underwriter_review": false,
  "turns": 4,
  "records_cited": [],
  "note": "Preliminary eligibility only. No cover is promised and premiums quoted on the call are indicative and subject to underwriting."
}
```

## Per-turn latency

| Turn | Retrieval | Generation | Total |
|---|---|---|---|
| 1 | 25 ms | 540 ms | 1906 ms |
| 2 | 25 ms | 595 ms | 2293 ms |
| 3 | 24 ms | 539 ms | 2154 ms |
| 4 | 26 ms | 678 ms | 2379 ms |

Transcription and synthesis are timed separately in the server trace log; the figures above cover the turn from transcript to generated reply.
