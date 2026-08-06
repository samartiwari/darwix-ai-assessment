# Design decisions

Each entry records what was chosen, what it was chosen over, and what it costs.

## One shared core rather than four separate projects

Speech recognition, language models, speech synthesis, telemetry and retrieval
are written once and consumed by all four parts. The alternative — four isolated
mini-projects — would have given better failure isolation, but at four times the
boilerplate inside a fixed deadline, and it makes the Philippines and Indonesia
agents tempting to build as copy-and-translate forks of the English one. Sharing
the engine forces localization to live in configuration where it can be
inspected.

The cost is coupling: a defect in the core reaches everything. It is contained
by building the knowledge base and the English agent as a complete working slice
first, then treating the core as stable.

## Half-duplex turns instead of full-duplex streaming conversation

The voice agents record one turn at a time rather than running continuous
bidirectional audio with barge-in. Full duplex sounds better in a demo, but
voice activity detection, interruption handling and turn-taking are the hardest
parts of the stack to debug and to reason about. Half duplex makes every stage
individually testable and every failure legible.

The cost is conversational realism: the caller cannot interrupt the agent. This
is recorded as a known limitation rather than hidden.

## Local embeddings, hosted language models

Embeddings run locally through sentence-transformers. Indexing a knowledge base
means thousands of embedding calls, which is exactly the workload a free API tier
throttles, and retrieval quality does not depend on a frontier model. Language
generation stays hosted because local models of comparable quality would not fit
the latency budget on a laptop GPU.

The effect is that retrieval — the part the assessment grades hardest — has no
external dependency and cannot be rate-limited mid-demo.

## Retrieval threshold as the anti-hallucination mechanism

Below a minimum fused score the retriever returns nothing at all, and the agent
is required to say it lacks the information. Instructing the model to be honest
is not sufficient on its own; a retriever that always returns its best guess will
eventually hand over an irrelevant record that the model then paraphrases with
confidence.

The cost is answerable questions occasionally refused when the threshold is set
too high. Threshold tuning is reported with the retrieval tests.

## The abstention threshold is measured, not chosen

`scripts/calibrate_threshold.py` runs twenty questions the knowledge base can
answer and fourteen it cannot, and reports where the two distributions sit. They
overlap: in-scope questions bottom out at 0.649 while out-of-scope questions reach
0.714, so no single similarity value separates them. The lowest total error is at
0.68, misclassifying two of thirty-four.

0.64 was chosen instead of 0.68 because the two errors are not equally costly.
Refusing an answerable question wastes a caller's time and there is no second
chance to recover it; answering an unanswerable one is caught downstream by
grounded generation, which sees the retrieved records and is instructed to say
when they do not contain the answer. At 0.64 the retriever refuses none of the
twenty answerable questions and rejects ten of the fourteen out-of-scope ones.

The residual four are reported in the retrieval results rather than tuned away.
"How many employees does Arogya First have" scores 0.714 because it is topically
close to every record about the brand — a bi-encoder measures topical closeness,
not whether a record answers a question.

## Cross-encoder reranking is available but off by default

A cross-encoder was measured as a candidate for the abstention decision, since
rerankers are better calibrated for relevance than bi-encoder similarity. It
separated off-topic questions decisively, scoring five of six at 0.002 or below.

It also scored "this is too expensive for me" at 0.024 against the record written
to answer exactly that objection, and "my father is 67, can he get cover" at
0.001. The model is trained on web-search query and passage pairs, and a
conversational utterance is not a search query. For a voice agent, where callers
speak in statements rather than queries, thresholding on it would refuse real
customers. It remains available through `RETRIEVAL_RERANK` for reordering, and is
not used for the abstention decision.

## Authoritative records are ranked among themselves

The brand's own documents are 51 records against 475 of background material that
uses the same vocabulary far more often. Three attempts were needed.

A multiplicative boost after fusion did nothing: asked "what plans do you offer
for a family", the Family Floater record never entered the candidate pool, and a
boost cannot lift a record that volume has already excluded. Reserving slots for
brand records fixed that, but gating them on the abstention threshold excluded the
same record again, because its text is a list of members and limits that scores
0.623. Selecting reserved slots by fused rank excluded it a third time, since it
has no lexical match at all.

Reserved slots are now selected by cosine similarity, with a lower inclusion bar
than the abstention threshold. Inclusion and abstention are different decisions:
one governs whether the brand's answer is visible to the model, the other whether
any answer is given.

## Hybrid retrieval with rank fusion

BM25 and dense vector search are fused rather than choosing one. Insurance
content mixes exact tokens that lexical search handles well — plan names,
section numbers, waiting periods — with paraphrased customer questions that only
semantic search matches. Reciprocal Rank Fusion needs no score calibration
between the two systems, which is what makes the combination practical.

## Two-tier signal extraction in the live pipeline

A cheap rule pass runs on every audio chunk; a language-model pass runs only on
a rolling window when the cheap pass fires or the topic shifts. Sending every
chunk to a model would be simpler and more sensitive, but it multiplies both
latency and cost, and on a free tier it would rate-limit within a single call.

The cost is reduced sensitivity to signals the rules do not anticipate. The
false-positive analysis reports the trade-off in both directions.

## Nudge suppression treated as a feature, not a filter

Confidence thresholds, duplicate fingerprinting, per-topic cooldowns and expiry
are built into the nudge path from the start rather than added once the output
becomes noisy. A pipeline that surfaces every detected signal is not useful to an
agent on a live call; the value is in what it declines to say.

## Personal data: quarantine as well as masking

Masking every detected identifier and indexing the result would have been the
simpler rule. It is also the wrong rule for a lead export: a knowledge base a
voice agent retrieves from has no legitimate reason to hold customer records, and
a masked record still discloses that a person of a given age in a given city
enquired about cover for a named condition. Documents are therefore split by
whether personal data is incidental or the substance — the first is masked and
flagged, the second is quarantined and never indexed.

The threshold is a density measure, which is crude. A short document with one
example call could in principle cross it. The report states which documents were
quarantined and why, so the decision is reviewable rather than invisible.

## Context-required detection for ambiguous identifiers

Detectors for Aadhaar numbers and bare mobile numbers require a cue word nearby;
email addresses and PANs do not, because their shape is decisive on its own.

This was not the original design. Matching on shape alone, the pipeline redacted
premium tables in a 64-page policy report as Aadhaar numbers and phone numbers —
`831 1046 1102` became three redaction tokens, and the figures were gone. The
same pass masked credited report authors and a named regulator's chairman as
customer data. Precision matters more than recall here, because a false positive
destroys content that retrieval later depends on, silently.

Recall is genuinely lower as a result: a bare Aadhaar number with no surrounding
cue is not detected. That limit is stated in the ingestion report rather than
left for a reviewer to discover.

## Contradictions are reported, not resolved

Where sources state different numbers for the same rule, both records are kept
and the conflict is listed in the ingestion report. The knowledge base found
seven different values for the pre-existing disease waiting period across public
sources and the internal documents, including a genuine 24-month against
36-month conflict between the FAQ sheet and the brochure.

Picking a winner automatically — most recent, most frequent, most authoritative
source — would produce a knowledge base that looks consistent while burying a
real error someone needs to settle. Retrieval returns both records with their
provenance so the disagreement is visible at the point of use.

## Real sources, fictional brand

The knowledge base is built from genuinely messy public content so that
extraction, cleaning and deduplication have real problems to solve, and every
record cites its real source URL. The agent presents a fictional brand and never
claims to be a real company, which keeps traceability without misrepresenting
anyone.
