# Ingestion report

Generated 2026-08-06 18:15 UTC by `python scripts/build_kb.py --stage collect`.

## Summary

| Measure | Value |
|---|---|
| Inputs attempted | 4 |
| Documents collected | 4 |
| Excluded (failed, refused, quarantined, duplicate) | 0 |
| Words after cleaning | 2,868 |
| Tables extracted | 0 |
| Documents containing masked personal data | 0 |
| Terminology substitutions applied | 0 |
| Dates converted to ISO 8601 | 0 |
| Currency amounts standardised | 0 |

## Documents collected

| ID | Source | Type | Words | Tables | Personal data |
|---|---|---|---|---|---|
| `int_009` | Kalinga Life — Objection Handling and Approved Wordi | internal document | 909 | 0 | none |
| `int_008` | Kalinga Life — Product and Policy Reference (Philipp | internal document | 723 | 0 | none |
| `int_007` | Amanah Finance — Penanganan Keberatan dan Naskah Dis | internal document | 694 | 0 | none |
| `int_006` | Amanah Finance — Referensi Produk dan Ketentuan (Ind | internal document | 542 | 0 | none |

## Excluded

Recorded rather than dropped silently. A pipeline that discards these without comment reports success on a knowledge base with holes in it.

| Input | Stage | Reason |
|---|---|---|

## Contradictions between sources

None detected.

## Personal data handling

Two outcomes, not one. Documents with incidental personal data — an example call written into a script — are masked in place and flagged. A document whose substance *is* personal data, such as a lead export, is quarantined and never indexed: a knowledge base a voice agent retrieves from has no legitimate need for customer records.

Detected classes: email, phone, PAN, Aadhaar, policy number, lead reference, and names where a cue word makes the role explicit.

Known limit: names are only detected after a cue such as "Caller:" or an honorific. Detecting names by capitalisation alone would flag product names like "Optima Secure" as people, so recall is traded for precision.
