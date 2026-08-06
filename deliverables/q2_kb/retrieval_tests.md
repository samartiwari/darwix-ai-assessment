# Retrieval test results

Generated 2026-08-06 10:20 UTC by `python scripts/retrieval_tests.py`.

Corpus: 526 records. Embedding model: `BAAI/bge-small-en-v1.5`. Retrieval: dense vector search and BM25 fused by Reciprocal Rank Fusion, with an authority boost for the brand's own documents and an abstention threshold of 0.64 cosine similarity.

## Summary

| Verdict | Cases |
|---|---|
| Correct | 9 / 11 |
| Partially correct | 1 / 11 |
| Incorrect | 1 / 11 |
| Median retrieval latency | 17 ms |

Verdicts are computed from declared expectations in `scripts/retrieval_tests.py`, not written by hand, so re-running after a change reports what actually happened.

## Cases

### What health insurance plans do you offer for a family?

**Type:** product — **Verdict: partially correct** — 9919 ms

Product question: needs the Family Floater record, not a generic article.

**Retrieved record:** `kb_process_int_005_002` — Qualification sequence

> Ask in this order. One question at a time. Do not batch. 1. "Who would you like to cover — just yourself, or family members as well?" 2. "And the age of the eldest person to be covered?" 3. "Which city are you in?" 4. "Has anyone to be covered been diagnosed with or treated for any medical    condition — diabetes, blood pressure, thyroid, anything else?" 5. "Do you have any existing health cover, including from an em…

**Source:** internal://arogya_first_sales_script.md  
**Section:** Arogya First — Outbound Lead Qualification Script > Qualification sequence  
**Category:** `process` — **version** 3.0  
**Similarity:** 0.670 (dense rank 14, lexical rank 8)

*Assessment:* Required terms appear at rank 2 rather than rank 1; the answer is in the retrieved set and reaches the model.

Also retrieved: `kb_product_int_001_006` (0.64), `kb_qualification_int_004_002` (0.62), `kb_product_int_003_002` (0.62)

### I have diabetes. When would that be covered?

**Type:** policy — **Verdict: correct** — 17 ms

Policy rule: must reach the pre-existing disease waiting period.

**Retrieved record:** `kb_objection_int_002_007` — "Can you guarantee my diabetes will be covered?"

> No guarantee may be given. State the rule: a declared pre-existing disease becomes claimable after the pre-existing disease waiting period of continuous cover, and that the final terms depend on underwriting. Offer underwriter review rather than an answer on the call.

**Source:** internal://arogya_first_objections.md  
**Section:** Arogya First — Objection Handling > "Can you guarantee my diabetes will be covered?"  
**Category:** `objection` — **version** 1.6  
**Similarity:** 0.771 (dense rank 2, lexical rank 3)

*Assessment:* Top record contains every required term.

Also retrieved: `kb_faq_int_001_001` (0.73), `kb_process_int_005_002` (0.71), `kb_qualification_int_004_004` (0.69)

### My father is 67 years old. Can he take a policy?

**Type:** qualification — **Verdict: correct** — 17 ms

Qualification: age above 60 routes to Senior Care.

**Retrieved record:** `kb_product_int_001_006` — Can I cover my parents on the same policy?

> Dependent parents can be added to an Arogya First Family Floater. If a parent is above 60, Senior Care is usually the better option because the floater's shared sum insured can be exhausted by a single senior claim.

**Source:** internal://arogya_first_faq.md  
**Section:** Arogya First — Customer FAQ Sheet > Can I cover my parents on the same policy?  
**Category:** `product` — **version** 1.9  
**Similarity:** 0.653 (dense rank 1, lexical rank 1)

*Assessment:* Top record contains every required term.

Also retrieved: `kb_qualification_int_004_002` (0.64), `kb_faq_int_001_014` (0.64), `kb_product_int_003_003` (0.60)

### How long does a reimbursement claim take to settle?

**Type:** faq — **Verdict: correct** — 18 ms

FAQ answered verbatim in the customer FAQ sheet.

**Retrieved record:** `kb_faq_int_001_005` — How long does a reimbursement claim take?

> How long does a reimbursement claim take? Reimbursement claims are settled within 15 working days of receiving complete documents. Incomplete documentation is the most common cause of delay.

**Source:** internal://arogya_first_faq.md  
**Section:** Arogya First — Customer FAQ Sheet > How long does a reimbursement claim take?  
**Category:** `faq` — **version** 1.9  
**Similarity:** 0.914 (dense rank 1, lexical rank 1)

*Assessment:* Top record contains every required term.

Also retrieved: `kb_product_int_003_007` (0.72), `kb_objection_int_002_004` (0.65), `kb_faq_int_001_000` (0.63)

### Honestly this is too expensive for me.

**Type:** objection — **Verdict: correct** — 17 ms

Objection: must reach the approved response, not a product page.

**Retrieved record:** `kb_objection_int_002_001` — "It is too expensive"

> Acknowledge the concern, then reframe against the deductible route. A Secure Top-up of Rs 5,000,000 (50 lakh) over a Rs 500,000 (5 lakh) deductible costs Rs 6,800 a year for a 35 year old, which is less than a Rs 1,000,000 (10 lakh) individual policy at Rs 9,400, because the employer or existing cover absorbs the first Rs 500,000 (5 lakh). Also mention Zone B and Zone C pricing where the caller is outside a metro, an…

**Source:** internal://arogya_first_objections.md  
**Section:** Arogya First — Objection Handling > "It is too expensive"  
**Category:** `objection` — **version** 1.6  
**Similarity:** 0.678 (dense rank 1, lexical rank 1)

*Assessment:* Top record contains every required term.

Also retrieved: `kb_objection_int_002_003` (0.58), `kb_product_src_007_063` (0.54), `kb_product_src_007_004` (0.57)

### What is the co-payment on the senior citizen plan?

**Type:** policy — **Verdict: correct** — 17 ms

Specific numeric term; tests exact-token retrieval.

**Retrieved record:** `kb_faq_int_001_011` — What is a co-payment?

> A co-payment is the share of an admissible claim you pay yourself. Senior Care carries a 20% co-payment on every claim. The other products carry no co-payment.

**Source:** internal://arogya_first_faq.md  
**Section:** Arogya First — Customer FAQ Sheet > What is a co-payment?  
**Category:** `faq` — **version** 1.9  
**Similarity:** 0.849 (dense rank 1, lexical rank 1)

*Assessment:* Top record contains every required term.

Also retrieved: `kb_objection_int_002_006` (0.72), `kb_qualification_int_004_002` (0.66), `kb_product_int_003_003` (0.65)

### Which cities count as Zone A for pricing?

**Type:** qualification — **Verdict: correct** — 164 ms

Table record: must return the zone table with its header intact.

**Retrieved record:** `kb_qualification_int_004_003` — Zone pricing

> | Zone | Cities | Premium loading | | Zone A | Delhi NCR, Mumbai, Thane, Navi Mumbai | Base rate | | Zone B | Bengaluru, Chennai, Hyderabad, Pune, Kolkata, Ahmedabad | Base less 10% | | Zone C | All other cities | Base less 20% |

**Source:** internal://arogya_first_qualification_rules.md  
**Section:** Arogya First — Lead Qualification Rules > Zone pricing  
**Category:** `qualification` — **version** 1.4  
**Similarity:** 0.762 (dense rank 1, lexical rank 1)

*Assessment:* Top record contains every required term.

Also retrieved: `kb_product_src_006_011` (0.58), `kb_product_src_006_010` (0.55), `kb_product_src_009_110` (0.52)

### What tax benefit do I get on the premium?

**Type:** faq — **Verdict: correct** — 17 ms

Section reference that lexical search should catch.

**Retrieved record:** `kb_faq_int_001_010` — What tax benefit do I get?

> Premium paid qualifies for deduction under section 80D of the Income Tax Act. The limit is Rs 25,000 for self and family, and an additional Rs 50,000 where premium is paid for parents aged 60 or above. Confirm your own position with a tax adviser.

**Source:** internal://arogya_first_faq.md  
**Section:** Arogya First — Customer FAQ Sheet > What tax benefit do I get?  
**Category:** `faq` — **version** 1.9  
**Similarity:** 0.798 (dense rank 1, lexical rank 1)

*Assessment:* Top record contains every required term.

Also retrieved: `kb_objection_int_002_003` (0.67), `kb_objection_int_002_001` (0.66), `kb_process_int_005_008` (0.65)

### What is the weather in Mumbai tomorrow?

**Type:** scope — **Verdict: correct** — 16 ms

Out of scope but shares a city name with the zone table.

Retriever abstained at confidence 0.52. Reason: best similarity 0.52 is below the 0.64 threshold, so no record is offered

*Assessment:* Refused as required (best similarity 0.52 is below the 0.64 threshold, so no record is offered).

### Who won the cricket match yesterday?

**Type:** scope — **Verdict: correct** — 16 ms

Plainly out of scope; must be refused, not paraphrased.

Retriever abstained at confidence 0.55. Reason: best similarity 0.55 is below the 0.64 threshold, so no record is offered

*Assessment:* Refused as required (best similarity 0.55 is below the 0.64 threshold, so no record is offered).

### How many employees does Arogya First have?

**Type:** scope — **Verdict: incorrect** — 17 ms

Brand-related but unanswerable — the hardest refusal case.

**Retrieved record:** `kb_faq_int_001_004` — How large is the cashless hospital network?

> Arogya First has a cashless network of 8,700 hospitals across 480 cities. Pre-authorisation for cashless treatment is decided within 60 minutes once complete documents are received.

**Source:** internal://arogya_first_faq.md  
**Section:** Arogya First — Customer FAQ Sheet > How large is the cashless hospital network?  
**Category:** `faq` — **version** 1.9  
**Similarity:** 0.684 (dense rank 1, lexical rank 3)

*Assessment:* Should have refused but returned `kb_faq_int_001_004` at similarity 0.68. Grounded generation is the second gate for this case.

Also retrieved: `kb_product_int_003_000` (0.68), `kb_objection_int_002_000` (0.62), `kb_product_int_003_003` (0.60)

## Notes on the failures

Cases marked incorrect are reported rather than removed from the set. The out-of-scope questions that still retrieve records are the known limit of a similarity threshold: a bi-encoder measures topical closeness, not whether a record answers a question, and "how many employees does Arogya First have" is topically close to every record about the brand. Those are caught by the second gate, grounded generation, which is instructed to answer only from the retrieved records and to say so when they do not contain the answer. The voice-agent transcripts show that gate operating.
