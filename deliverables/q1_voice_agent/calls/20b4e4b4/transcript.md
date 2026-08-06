# Call 20b4e4b4 — Arogya First (India)

- **Market pack:** `in_health_en` (health insurance, lead qualification)
- **Started:** 2026-08-06T13:07:12+00:00
- **Turns:** 5
- **Outcome:** qualified
- **Escalated:** no
- **Captured:** members=1, age=41, city=Bengaluru, conditions=controlled diabetes
- **Response latency:** P50 708.5 ms, P95 11001.9 ms

## Transcript

**Caller:** Yes that's fine go ahead

**Asha:** Who would you like to cover — just yourself, or family members as well?

> intent `cooperative` · answer source `none_needed` · retrieval confidence 0.644
>
> Cited: `kb_process_int_005_001` (Consent) — internal://arogya_first_sales_script.md; `kb_process_int_005_003` (Recommendation) — internal://arogya_first_sales_script.md

**Caller:** Just myself, I am 41

**Asha:** And which city are you based in?

> intent `cooperative` · answer source `none_needed` · retrieval confidence 0.542 · **retrieval abstained** · captured members=1, age=41
>
> Cited: none — no factual claim made from the knowledge base

**Caller:** I'm in Bengaluru

**Asha:** Okay, so you're 41 and based in Bengaluru, what pre-existing medical conditions do you have, if any?

> intent `cooperative` · answer source `none_needed` · retrieval confidence 0.548 · **retrieval abstained** · captured city=Bengaluru
>
> Cited: none — no factual claim made from the knowledge base

**Caller:** I have controlled diabetes

**Asha:** I've noted that you have controlled diabetes. Our policy has a 36 month pre-existing disease waiting period for controlled diabetes, and the final terms will depend on underwriting. Would you like to proceed with the qualification?

> intent `cooperative` · answer source `none_needed` · retrieval confidence 0.694 · captured conditions=controlled diabetes
>
> Cited: `kb_objection_int_002_007` ("Can you guarantee my diabetes will be covered?") — internal://arogya_first_objections.md; `kb_process_int_005_002` (Qualification sequence) — internal://arogya_first_sales_script.md

**Caller:** How long does a claim take to settle?

**Asha:** Reimbursement claims are settled within 15 working days of receiving complete documents.

> intent `question` · answer source `context` · retrieval confidence 0.835
>
> Cited: `kb_faq_int_001_005` (How long does a reimbursement claim take?) — internal://arogya_first_faq.md; `kb_product_int_003_007` (Network and claims) — internal://arogya_first_product_brochure.md

## Lead record created

```json
{
  "lead_reference": "AF-2026-08-20B4E4B4",
  "created_at": "2026-08-06T13:07:26+00:00",
  "market": "in_health_en",
  "brand": "Arogya First",
  "channel": "inbound_web_call",
  "outcome": "qualified",
  "captured": {
    "members": "1",
    "age": "41",
    "city": "Bengaluru",
    "conditions": "controlled diabetes"
  },
  "missing_required": [],
  "unresolved_conflicts": [],
  "escalated": false,
  "escalation_reason": null,
  "requires_underwriter_review": false,
  "turns": 5,
  "records_cited": [
    "kb_process_int_005_001",
    "kb_process_int_005_003",
    "kb_objection_int_002_007",
    "kb_process_int_005_002",
    "kb_faq_int_001_005",
    "kb_product_int_003_007"
  ],
  "note": "Preliminary eligibility only. No cover is promised and premiums quoted on the call are indicative and subject to underwriting."
}
```

## Per-turn latency

| Turn | Retrieval | Generation | Total |
|---|---|---|---|
| 1 | 10027 ms | 975 ms | 11002 ms |
| 2 | 28 ms | 539 ms | 567 ms |
| 3 | 26 ms | 683 ms | 708 ms |
| 4 | 25 ms | 835 ms | 860 ms |
| 5 | 26 ms | 634 ms | 661 ms |

Transcription and synthesis are timed separately in the server trace log; the figures above cover the turn from transcript to generated reply.
