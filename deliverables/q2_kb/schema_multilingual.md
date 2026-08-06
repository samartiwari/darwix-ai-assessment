# Knowledge-base schema and records

Generated 2026-08-06 18:15 UTC by `python scripts/build_kb.py --stage build`.

## Build summary

| Measure | Value |
|---|---|
| Documents chunked | 4 |
| Chunks produced | 38 |
| Unanswerable fragments removed | 0 |
| Near-duplicate records removed | 0 |
| Records indexed | 38 |
| Table records | 0 |
| Records carrying masked personal data | 0 |
| Corpus | `multilingual` |
| Embedding model | `BAAI/bge-m3` (1024 dimensions) |
| Median record length | 62 words |

## Taxonomy

Six categories, chosen to match the question types a caller actually asks. Retrieval can filter by category, so the conversation stage narrows the search: an objection turn searches objections and policy rules before product pages.

| Category | Records | Purpose |
|---|---|---|
| `product` | 17 | plans, cover amounts, premiums, benefits |
| `policy_rule` | 1 | waiting periods, exclusions, regulatory and renewal terms |
| `qualification` | 0 | eligibility bands, zones, declared conditions, budget guidance |
| `faq` | 0 | questions asked in the caller's own words |
| `objection` | 20 | approved responses to resistance |
| `process` | 0 | call flow, consent, escalation, compliance requirements |

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
| `record_id` | `kb_product_int_006_000` |
| `title` | Amanah Finance — Referensi Produk dan Ketentuan (Indonesia) |
| `content` | Versi 1.4 \| Berlaku 2025-04-01 \| Multifinance, kanal langsung dan dealer Amanah Finance adalah perusahaan multifinance fiktif yang dipakai untuk prototipe ini. Angka bersifat ilustratif dan mengikuti ketentuan pembiayaan konsumen Indonesia pada umumnya. Catatan istilah: nasabah dan petugas memakai i… |
| `category` | `product` |
| `source_url` | internal://id_amanah_finance_products.md |
| `source_type` | `internal_document` |
| `section_path` | Amanah Finance — Referensi Produk dan Ketentuan (Indonesia) |
| `version` / `effective_date` | 1.0 / — |
| `checksum` | `ce358effbbf271e9` |
| `pii` / `pii_types` | false / — |
| `lang` / `kind` | id / `prose` |
| `doc_id` / `ordinal` | `int_006` / 0 |
| `word_count` | 73 |

### A policy rule

| Field | Value |
|---|---|
| `record_id` | `kb_policy_rule_int_008_004` |
| `title` | Lapse and reinstatement |
| `content` | - A policy lapses when a premium remains unpaid after the 31-day grace period. - Coverage is not active while a policy is lapsed. A claim during lapse is not   payable. - Reinstatement is possible within 3 years of the lapse date, subject to:   payment of all overdue premiums with interest of 10% pe… |
| `category` | `policy_rule` |
| `source_url` | internal://ph_kalinga_life_products.md |
| `source_type` | `internal_document` |
| `section_path` | Kalinga Life — Product and Policy Reference (Philippines) > Lapse and reinstatement |
| `version` / `effective_date` | 1.3 / 2025-04-01 |
| `checksum` | `0f6bd6ac9c744822` |
| `pii` / `pii_types` | false / — |
| `lang` / `kind` | fil / `prose` |
| `doc_id` / `ordinal` | `int_008` / 4 |
| `word_count` | 116 |

### An objection response

| Field | Value |
|---|---|
| `record_id` | `kb_objection_int_007_000` |
| `title` | Amanah Finance — Penanganan Keberatan dan Naskah Disetujui (Indonesia) |
| `content` | Jawaban yang disetujui untuk pengingat angsuran, tindak lanjut keterlambatan, dan dukungan pembayaran. Aturan register yang berlaku untuk semua jawaban di bawah: - Sapa nasabah dengan `Bapak` atau `Ibu`, bukan `Anda` saja, dan bukan nama   depan. `Anda` terasa dingin dan seperti surat resmi, bukan p… |
| `category` | `objection` |
| `source_url` | internal://id_amanah_objections.md |
| `source_type` | `internal_document` |
| `section_path` | Amanah Finance — Penanganan Keberatan dan Naskah Disetujui (Indonesia) |
| `version` / `effective_date` | 1.0 / — |
| `checksum` | `510badd38bb07c3d` |
| `pii` / `pii_types` | false / — |
| `lang` / `kind` | id / `prose` |
| `doc_id` / `ordinal` | `int_007` / 0 |
| `word_count` | 129 |

