# Knowledge-base schema and records

Generated 2026-08-05 17:23 UTC by `python scripts/build_kb.py --stage build`.

## Build summary

| Measure | Value |
|---|---|
| Documents chunked | 14 |
| Chunks produced | 590 |
| Unanswerable fragments removed | 61 |
| Near-duplicate records removed | 3 |
| Records indexed | 526 |
| Table records | 48 |
| Records carrying masked personal data | 9 |
| Embedding model | `BAAI/bge-small-en-v1.5` (384 dimensions) |
| Median record length | 58 words |

## Taxonomy

Six categories, chosen to match the question types a caller actually asks. Retrieval can filter by category, so the conversation stage narrows the search: an objection turn searches objections and policy rules before product pages.

| Category | Records | Purpose |
|---|---|---|
| `product` | 194 | plans, cover amounts, premiums, benefits |
| `policy_rule` | 281 | waiting periods, exclusions, regulatory and renewal terms |
| `qualification` | 17 | eligibility bands, zones, declared conditions, budget guidance |
| `faq` | 12 | questions asked in the caller's own words |
| `objection` | 10 | approved responses to resistance |
| `process` | 12 | call flow, consent, escalation, compliance requirements |

## Field definitions

| Field | Type | Purpose |
|---|---|---|
| `record_id` | text, primary key | stable citation target; encodes category and source document |
| `title` | text | the record's own heading, read aloud when citing |
| `content` | text | the retrievable passage, cleaned, normalized and masked |
| `category` | text | one of the six taxonomy values |
| `source_url` | text | provenance; a real URL for public sources, `internal://` for authored documents |
| `source_type` | text | `web_page`, `pdf`, `internal_document`, `internal_data` |
| `section_path` | text | heading trail within the source, giving a human the location |
| `version` | text | taken from the source document's own version line |
| `effective_date` | date | when the stated terms took effect, ISO 8601 |
| `checksum` | text | content hash; a changed hash means a new version of the record |
| `superseded_by` | text | set when a newer record replaces this one |
| `pii` | boolean | whether personal data was found and masked |
| `pii_types` | text | which classes were masked |
| `lang` | text | `en`, `fil`, `id` |
| `kind` | text | `prose` or `table`; tables keep their header row |
| `doc_id` | text | the source document this record came from |
| `ordinal` | integer | position within the document, for reading neighbours |
| `word_count` | integer | length, used to check retrieval budget |
| `ingested_at` | timestamp | audit trail |

## Versioning

`version` and `effective_date` are read from the source document rather than invented, so a record states the authority it came from. `checksum` is the content hash: a re-ingest that changes a passage produces a different checksum, which is how a superseding record is identified. `superseded_by` then points forward, so an answer given last month can still be traced to the record that produced it.

## Sample records

### A product record

| Field | Value |
|---|---|
| `record_id` | `kb_product_int_001_006` |
| `title` | Can I cover my parents on the same policy? |
| `content` | Dependent parents can be added to an Arogya First Family Floater. If a parent is above 60, Senior Care is usually the better option because the floater's shared sum insured can be exhausted by a single senior claim. |
| `category` | `product` |
| `source_url` | internal://arogya_first_faq.md |
| `source_type` | `internal_document` |
| `section_path` | Arogya First — Customer FAQ Sheet > Can I cover my parents on the same policy? |
| `version` / `effective_date` | 1.9 / 2025-03-15 |
| `checksum` | `0093ed879475433b` |
| `pii` / `pii_types` | false / — |
| `lang` / `kind` | en / `prose` |
| `doc_id` / `ordinal` | `int_001` / 6 |
| `word_count` | 38 |

### A policy rule

| Field | Value |
|---|---|
| `record_id` | `kb_policy_rule_int_003_005` |
| `title` | Waiting periods (all products) |
| `content` | - Initial waiting period: 30 days from policy start, accidents excepted - Pre-existing disease waiting period: 36 months of continuous cover - Specified illness waiting period: 24 months, covering cataract, hernia,   joint replacement, and benign prostate conditions - Maternity waiting period: 36 mo… |
| `category` | `policy_rule` |
| `source_url` | internal://arogya_first_product_brochure.md |
| `source_type` | `internal_document` |
| `section_path` | Arogya First — Product Brochure > Waiting periods (all products) |
| `version` / `effective_date` | 2.1 / 2025-04-01 |
| `checksum` | `54e623e971d3a88e` |
| `pii` / `pii_types` | false / — |
| `lang` / `kind` | en / `prose` |
| `doc_id` / `ordinal` | `int_003` / 5 |
| `word_count` | 43 |

### A qualification table

| Field | Value |
|---|---|
| `record_id` | `kb_qualification_int_004_001` |
| `title` | Required information before a quote |
| `content` | \| Field \| Requirement \| If missing \| \| Age of eldest member \| Mandatory \| Cannot quote, ask again \| \| City / pin code \| Mandatory \| Cannot quote, affects zone pricing \| \| Family members to cover \| Mandatory \| Cannot quote \| \| Existing medical conditions \| Mandatory, self-declared \| Cannot quote \| \| … |
| `category` | `qualification` |
| `source_url` | internal://arogya_first_qualification_rules.md |
| `source_type` | `internal_document` |
| `section_path` | Arogya First — Lead Qualification Rules > Required information before a quote |
| `version` / `effective_date` | 1.4 / 2025-04-01 |
| `checksum` | `7ab32f5ce98f7fda` |
| `pii` / `pii_types` | false / — |
| `lang` / `kind` | en / `table` |
| `doc_id` / `ordinal` | `int_004` / 1 |
| `word_count` | 78 |

### An objection response

| Field | Value |
|---|---|
| `record_id` | `kb_objection_int_002_000` |
| `title` | Arogya First — Objection Handling |
| `content` | Arogya First — Objection Handling Approved responses only. Each response must stay factual and must not guarantee claim outcomes. Where a caller pushes beyond these answers, escalate. |
| `category` | `objection` |
| `source_url` | internal://arogya_first_objections.md |
| `source_type` | `internal_document` |
| `section_path` | Arogya First — Objection Handling |
| `version` / `effective_date` | 1.6 / 2025-04-01 |
| `checksum` | `32828350fee1d263` |
| `pii` / `pii_types` | false / — |
| `lang` / `kind` | en / `prose` |
| `doc_id` / `ordinal` | `int_002` / 0 |
| `word_count` | 27 |

### A record with masked personal data

| Field | Value |
|---|---|
| `record_id` | `kb_process_int_005_000` |
| `title` | Opening |
| `content` | "Good morning, this is Asha, an automated assistant calling from Arogya First about your health insurance enquiry. This call is recorded for quality purposes. Is now a good time to talk for two minutes?" If no: offer a callback slot and end. If yes: proceed. |
| `category` | `process` |
| `source_url` | internal://arogya_first_sales_script.md |
| `source_type` | `internal_document` |
| `section_path` | Arogya First — Outbound Lead Qualification Script > Opening |
| `version` / `effective_date` | 3.0 / 2025-04-01 |
| `checksum` | `9529671cbd035229` |
| `pii` / `pii_types` | true / EMAIL, LEAD_REF, NAME, PAN, PHONE |
| `lang` / `kind` | en / `prose` |
| `doc_id` / `ordinal` | `int_005` / 0 |
| `word_count` | 45 |

## Near-duplicate records removed

The same fact stated in two places produces two records that compete for the same retrieval slot. Similarity is Jaccard overlap over five-word shingles; the longer record is kept.

| Kept | Removed | Similarity |
|---|---|---|
| `kb_policy_rule_src_009_252` | `kb_policy_rule_src_009_044` | 0.86 (near) |
| `kb_policy_rule_src_009_260` | `kb_policy_rule_src_009_106` | 0.88 (near) |
| `kb_policy_rule_src_009_247` | `kb_policy_rule_src_009_281` | 1.00 (near) |
