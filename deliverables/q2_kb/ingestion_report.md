# Ingestion report

Generated 2026-08-05 16:47 UTC by `python scripts/build_kb.py --stage collect`.

## Summary

| Measure | Value |
|---|---|
| Inputs attempted | 19 |
| Documents collected | 14 |
| Excluded (failed, refused, quarantined, duplicate) | 5 |
| Words after cleaning | 55,680 |
| Tables extracted | 35 |
| Documents containing masked personal data | 1 |
| Terminology substitutions applied | 74 |
| Dates converted to ISO 8601 | 521 |
| Currency amounts standardised | 200 |

## Documents collected

| ID | Source | Type | Words | Tables | Personal data |
|---|---|---|---|---|---|
| `src_009` | [HealthInsurance forIndiasMissingMiddle 28 10 2021](https://www.niti.gov.in/sites/default/files/2021-10/HealthInsurance-forIndiasMissingMiddle_28-10-2021.pdf) | PDF, 64 pages | 17,615 | 35 | none |
| `src_001` | [Health insurance - Wikipedia](https://en.wikipedia.org/wiki/Health_insurance) | web page | 10,501 | 0 | none |
| `src_007` | [Health Insurance \| Get Medical Insurance Online @ ₹1](https://www.nivabupa.com/health-insurance-plans.html) | web page | 9,375 | 0 | none |
| `src_006` | [Health insurance marketplace - Wikipedia](https://en.wikipedia.org/wiki/Health_insurance_marketplace) | web page | 6,648 | 0 | none |
| `src_005` | [Ayushman Bharat Yojana - Wikipedia](https://en.wikipedia.org/wiki/Ayushman_Bharat_Yojana) | web page | 3,256 | 0 | none |
| `src_003` | [Pre-existing condition - Wikipedia](https://en.wikipedia.org/wiki/Pre-existing_condition) | web page | 2,347 | 0 | none |
| `src_004` | [Insurance Regulatory and Development Authority - Wik](https://en.wikipedia.org/wiki/Insurance_Regulatory_and_Development_Authority) | web page | 1,493 | 0 | none |
| `src_002` | [Health insurance in India - Wikipedia](https://en.wikipedia.org/wiki/Health_insurance_in_India) | web page | 1,005 | 0 | none |
| `int_004` | Arogya First — Lead Qualification Rules | internal document | 627 | 0 | none |
| `src_008` | [Health Insurance \| Buy Medical Insurance Plans @ Rs ](https://www.hdfcergo.com/health-insurance) | web page | 588 | 0 | none |
| `int_002` | Arogya First — Objection Handling | internal document | 583 | 0 | none |
| `int_001` | Arogya First — Customer FAQ Sheet | internal document | 563 | 0 | none |
| `int_003` | Arogya First — Product Brochure | internal document | 561 | 0 | none |
| `int_005` | Arogya First — Outbound Lead Qualification Script | internal document | 518 | 0 | EMAIL, LEAD_REF, NAME, PAN, PHONE |

## Excluded

Recorded rather than dropped silently. A pipeline that discards these without comment reports success on a knowledge base with holes in it.

| Input | Stage | Reason |
|---|---|---|
| https://www.nivabupa.com/frequently-asked-questions.html | fetch | HTTP 404 |
| https://www.hdfcergo.com/customer-care/faqs | fetch | TooManyRedirects: Exceeded maximum allowed redirects. |
| https://www.careinsurance.com/frequently-asked-questions.html | fetch | HTTP 404 |
| https://irdai.gov.in/consumer-education | robots | disallowed by robots.txt |
| `internal://sample_leads.csv` | pii | 56 personal-data matches across 315 words (17.8%) — treated as a records export, not reference content |

## Contradictions between sources

Reported, not resolved. Choosing a value silently would bury a source error that a person needs to settle. Retrieval surfaces both records with their provenance so the conflict is visible.

| Topic | Conflicting values |
|---|---|
| pre-existing disease waiting period | **6 months** in `src_003` vs **18 months** in `src_003` vs **3 years** in `src_007` vs **36 months** in `src_007, int_003, int_004` vs **48 months** in `src_007` vs **2 years** in `src_007` vs **24 months** in `int_001` |
| maternity waiting period | **9 months** in `src_007` vs **36 months** in `int_001, int_003` |
| co-payment share | **80** in `src_001` vs **5** in `src_009` vs **20** in `int_003` |

## Terminology standardisation

Sources use different words for the same concept. Retrieval degrades when a concept is spelled three ways, so one canonical form is applied.

| Substitution | Occurrences |
|---|---|
| pre-existing condition -> pre-existing disease | 36 |
| cover amount -> sum insured | 13 |
| PED -> pre-existing disease | 7 |
| NCB -> no claim bonus | 6 |
| co-pay -> co-payment | 3 |
| cumulative bonus -> no claim bonus | 2 |
| coverage limit -> sum insured | 2 |
| cooling period -> waiting period | 2 |
| copayment -> co-payment | 1 |
| policy price -> premium | 1 |
| policy cost -> premium | 1 |

## Site-wide repeated lines removed

2 lines appeared in three or more web documents and were removed as headers, footers or navigation.

- `History`
- `[edit]`

## Personal data handling

Two outcomes, not one. Documents with incidental personal data — an example call written into a script — are masked in place and flagged. A document whose substance *is* personal data, such as a lead export, is quarantined and never indexed: a knowledge base a voice agent retrieves from has no legitimate need for customer records.

Detected classes: email, phone, PAN, Aadhaar, policy number, lead reference, and names where a cue word makes the role explicit.

Known limit: names are only detected after a cue such as "Caller:" or an honorific. Detecting names by capitalisation alone would flag product names like "Optima Secure" as people, so recall is traded for precision.
