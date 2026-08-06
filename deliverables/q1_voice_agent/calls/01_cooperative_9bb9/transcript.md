# Call 01_cooperative_9bb9 — Arogya First (India)

- **Market pack:** `in_health_en` (health insurance, lead qualification)
- **Started:** 2026-08-06T13:56:30+00:00
- **Turns:** 6
- **Outcome:** qualified
- **Escalated:** no
- **Captured:** members=4, age=38, city=Pune, conditions=none, budget=Rs 18 lakhs
- **Response latency:** P50 2195.3 ms, P95 13277.6 ms

## Transcript

**Caller:** Yes that is fine, please go ahead.

**Asha:** Who would you like to cover — just yourself, or family members as well?

> intent `cooperative` · answer source `none_needed` · retrieval confidence 0.65
>
> Cited: `kb_process_int_005_001` (Consent) — internal://arogya_first_sales_script.md; `kb_qualification_int_004_002` (Age eligibility) — internal://arogya_first_qualification_rules.md

**Caller:** I want to cover myself, my wife and our two children.

**Asha:** Alright, so there are four members in your family to be covered. And the age of the eldest person to be covered?

> intent `cooperative` · answer source `none_needed` · retrieval confidence 0.634 · **retrieval abstained** · captured members=4
>
> Cited: none — no factual claim made from the knowledge base

**Caller:** I am 38, the eldest of us.

**Asha:** Which city are you in?

> intent `cooperative` · answer source `none_needed` · retrieval confidence 0.535 · **retrieval abstained** · captured age=38
>
> Cited: none — no factual claim made from the knowledge base

**Caller:** We live in Pune.

**Asha:** Has anyone to be covered been diagnosed with or treated for any medical condition — diabetes, blood pressure, thyroid, anything else?

> intent `cooperative` · answer source `none_needed` · retrieval confidence 0.539 · **retrieval abstained** · captured city=Pune
>
> Cited: none — no factual claim made from the knowledge base

**Caller:** Nobody has any medical conditions, we are all healthy.

**Asha:** That's great to hear. Can you please tell me what kind of budget you have in mind for the premium?

> intent `cooperative` · answer source `none_needed` · retrieval confidence 0.633 · **retrieval abstained** · captured conditions=none
>
> Cited: none — no factual claim made from the knowledge base

**Caller:** My budget is around $22,000 a year.

**Asha:** I've noted that, however, I'd like to clarify that our conversation is in Indian rupees, so I'll assume you meant around Rs 18 lakhs per year. Let me summarize what we've discussed so far.

> intent `cooperative` · answer source `none_needed` · retrieval confidence 0.641 · captured budget=Rs 18 lakhs
>
> Cited: `kb_qualification_int_004_005` (Budget guidance) — internal://arogya_first_qualification_rules.md; `kb_objection_int_002_001` ("It is too expensive") — internal://arogya_first_objections.md

## Lead record created

```json
{
  "lead_reference": "AF-2026-08-01_COOPERATIVE_9BB9",
  "created_at": "2026-08-06T13:57:10+00:00",
  "market": "in_health_en",
  "brand": "Arogya First",
  "channel": "inbound_web_call",
  "outcome": "qualified",
  "captured": {
    "members": "4",
    "age": "38",
    "city": "Pune",
    "conditions": "none",
    "budget": "Rs 18 lakhs"
  },
  "missing_required": [],
  "unresolved_conflicts": [],
  "escalated": false,
  "escalation_reason": null,
  "requires_underwriter_review": false,
  "turns": 6,
  "records_cited": [
    "kb_process_int_005_001",
    "kb_qualification_int_004_002",
    "kb_qualification_int_004_005",
    "kb_objection_int_002_001"
  ],
  "note": "Preliminary eligibility only. No cover is promised and premiums quoted on the call are indicative and subject to underwriting."
}
```

## Per-turn latency

| Turn | Retrieval | Generation | Total |
|---|---|---|---|
| 1 | 10272 ms | 560 ms | 13278 ms |
| 2 | 26 ms | 521 ms | 2159 ms |
| 3 | 27 ms | 551 ms | 2155 ms |
| 4 | 24 ms | 625 ms | 2195 ms |
| 5 | 27 ms | 611 ms | 2214 ms |
| 6 | 26 ms | 1111 ms | 2800 ms |

Transcription and synthesis are timed separately in the server trace log; the figures above cover the turn from transcript to generated reply.
