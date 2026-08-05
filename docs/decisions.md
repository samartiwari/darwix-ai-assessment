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

## Real sources, fictional brand

The knowledge base is built from genuinely messy public content so that
extraction, cleaning and deduplication have real problems to solve, and every
record cites its real source URL. The agent presents a fictional brand and never
claims to be a real company, which keeps traceability without misrepresenting
anyone.
