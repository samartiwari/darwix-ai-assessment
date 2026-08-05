# Ingestion report

Generated 2026-08-05 15:20 UTC by `python scripts/build_kb.py --stage collect`.

## Summary

| Sources attempted | 13 |
|---|---|
| Collected | 9 |
| Failed or refused | 4 |
| Words after cleaning | 53,691 |
| Tables extracted | 35 |

## Collected

| Source | Type | Words | Tables | Chrome lines removed |
|---|---|---|---|---|
| [HealthInsurance forIndiasMissingMiddle 28 10 2021](https://www.niti.gov.in/sites/default/files/2021-10/HealthInsurance-forIndiasMissingMiddle_28-10-2021.pdf) | PDF, 64 pages | 17,565 | 35 | 178 |
| [Health insurance - Wikipedia](https://en.wikipedia.org/wiki/Health_insurance) | web page | 10,761 | 0 | 49 |
| [Health Insurance \| Get Medical Insurance Online @ ₹17/Day](https://www.nivabupa.com/health-insurance-plans.html) | web page | 9,308 | 0 | 48 |
| [Health insurance marketplace - Wikipedia](https://en.wikipedia.org/wiki/Health_insurance_marketplace) | web page | 6,981 | 0 | 24 |
| [Ayushman Bharat Yojana - Wikipedia](https://en.wikipedia.org/wiki/Ayushman_Bharat_Yojana) | web page | 3,455 | 0 | 5 |
| [Pre-existing condition - Wikipedia](https://en.wikipedia.org/wiki/Pre-existing_condition) | web page | 2,467 | 0 | 24 |
| [Insurance Regulatory and Development Authority - Wikipedia](https://en.wikipedia.org/wiki/Insurance_Regulatory_and_Development_Authority) | web page | 1,539 | 0 | 6 |
| [Health insurance in India - Wikipedia](https://en.wikipedia.org/wiki/Health_insurance_in_India) | web page | 1,033 | 0 | 3 |
| [Health Insurance \| Buy Medical Insurance Plans @ Rs 27/Day](https://www.hdfcergo.com/health-insurance) | web page | 582 | 0 | 0 |

## Failed or refused

Recorded rather than skipped silently. A pipeline that drops these without comment reports success on a knowledge base with holes in it.

| Source | Stage | Reason |
|---|---|---|
| `https://www.nivabupa.com/frequently-asked-questions.html` | fetch | HTTP 404 |
| `https://www.hdfcergo.com/customer-care/faqs` | fetch | TooManyRedirects: Exceeded maximum allowed redirects. |
| `https://www.careinsurance.com/frequently-asked-questions.html` | fetch | HTTP 404 |
| `https://irdai.gov.in/consumer-education` | robots | disallowed by robots.txt |

## Site-wide repeated lines removed

2 lines appeared in three or more documents and were removed as headers, footers or navigation. A sample:

- `History`
- `[edit]`
