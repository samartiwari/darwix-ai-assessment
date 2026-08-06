"""Run the retrieval test set and write the results report.

Each case declares the question, what a correct answer must contain, and whether
the retriever is expected to answer or abstain. Verdicts are computed from those
declarations rather than written by hand, so re-running after a change to
chunking or ranking updates the verdicts honestly instead of preserving a
flattering snapshot.

    python scripts/retrieval_tests.py
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

REPORT = ROOT / "deliverables" / "q2_kb" / "retrieval_tests.md"


@dataclass
class Case:
    question: str
    kind: str                       # product | policy | qualification | faq | objection | scope
    must_contain: list[str] = field(default_factory=list)
    expect: str = "answer"          # answer | abstain
    note: str = ""


CASES = [
    Case(
        question="What health insurance plans do you offer for a family?",
        kind="product",
        must_contain=["floater", "shared"],
        note="Product question: needs the Family Floater record, not a generic article.",
    ),
    Case(
        question="I have diabetes. When would that be covered?",
        kind="policy",
        must_contain=["pre-existing"],
        note="Policy rule: must reach the pre-existing disease waiting period.",
    ),
    Case(
        question="My father is 67 years old. Can he take a policy?",
        kind="qualification",
        must_contain=["senior", "60"],
        note="Qualification: age above 60 routes to Senior Care.",
    ),
    Case(
        question="How long does a reimbursement claim take to settle?",
        kind="faq",
        must_contain=["15 working days"],
        note="FAQ answered verbatim in the customer FAQ sheet.",
    ),
    Case(
        question="Honestly this is too expensive for me.",
        kind="objection",
        must_contain=["deductible", "top-up"],
        note="Objection: must reach the approved response, not a product page.",
    ),
    Case(
        question="What is the co-payment on the senior citizen plan?",
        kind="policy",
        must_contain=["20%", "co-payment"],
        note="Specific numeric term; tests exact-token retrieval.",
    ),
    Case(
        question="Which cities count as Zone A for pricing?",
        kind="qualification",
        must_contain=["Delhi", "Mumbai"],
        note="Table record: must return the zone table with its header intact.",
    ),
    Case(
        question="What tax benefit do I get on the premium?",
        kind="faq",
        must_contain=["80D"],
        note="Section reference that lexical search should catch.",
    ),
    Case(
        question="What is the weather in Mumbai tomorrow?",
        kind="scope",
        expect="abstain",
        note="Out of scope but shares a city name with the zone table.",
    ),
    Case(
        question="Who won the cricket match yesterday?",
        kind="scope",
        expect="abstain",
        note="Plainly out of scope; must be refused, not paraphrased.",
    ),
    Case(
        question="How many employees does Arogya First have?",
        kind="scope",
        expect="abstain",
        note="Brand-related but unanswerable — the hardest refusal case.",
    ),
]


def verdict_for(case: Case, result) -> tuple[str, str]:
    """Compute a verdict and the reasoning behind it."""
    if case.expect == "abstain":
        if result.abstained:
            return "correct", f"Refused as required ({result.reason})."
        top = result.hits[0].record
        return (
            "incorrect",
            f"Should have refused but returned `{top.record_id}` at similarity "
            f"{result.confidence:.2f}. Grounded generation is the second gate for this case.",
        )

    if result.abstained:
        return "incorrect", f"Refused an answerable question ({result.reason})."

    needles = [n.lower() for n in case.must_contain]
    top_text = f"{result.hits[0].record.title} {result.hits[0].record.content}".lower()
    if all(n in top_text for n in needles):
        return "correct", "Top record contains every required term."

    all_text = " ".join(
        f"{h.record.title} {h.record.content}".lower() for h in result.hits
    )
    if all(n in all_text for n in needles):
        position = next(
            i + 1
            for i, h in enumerate(result.hits)
            if all(n in f"{h.record.title} {h.record.content}".lower() for n in needles)
        )
        return (
            "partially correct",
            f"Required terms appear at rank {position} rather than rank 1; the answer "
            "is in the retrieved set and reaches the model.",
        )

    missing = [n for n in needles if n not in all_text]
    return "incorrect", f"Retrieved set is missing: {', '.join(missing)}."


def main() -> int:
    from core.kb.retrieve import Retriever
    from core.kb.store import KnowledgeBase

    kb = KnowledgeBase()
    total_records = kb.count()
    build = kb.build_info()
    retriever = Retriever(kb)

    rows = []
    latencies = []
    for case in CASES:
        start = time.perf_counter()
        result = retriever.search(case.question)
        elapsed = (time.perf_counter() - start) * 1000
        latencies.append(elapsed)
        verdict, reasoning = verdict_for(case, result)
        rows.append((case, result, verdict, reasoning, elapsed))
        mark = {"correct": "ok", "partially correct": "partial", "incorrect": "FAIL"}[verdict]
        print(f"[{mark:>7}] {case.kind:<13} {case.question[:52]}")

    counts = {v: sum(1 for _, _, ver, _, _ in rows if ver == v) for v in
              ("correct", "partially correct", "incorrect")}
    # The first query pays for model loading; it is excluded from the median.
    steady = sorted(latencies[1:]) or latencies
    median = steady[len(steady) // 2]

    lines = [
        "# Retrieval test results",
        "",
        f"Generated {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')} by "
        "`python scripts/retrieval_tests.py`.",
        "",
        f"Corpus: {total_records} records. Embedding model: "
        f"`{build.get('embedding_model', 'unknown')}`. "
        "Retrieval: dense vector search and BM25 fused by Reciprocal Rank Fusion, "
        "with an authority boost for the brand's own documents and an abstention "
        "threshold of 0.64 cosine similarity.",
        "",
        "## Summary",
        "",
        "| Verdict | Cases |",
        "|---|---|",
        f"| Correct | {counts['correct']} / {len(rows)} |",
        f"| Partially correct | {counts['partially correct']} / {len(rows)} |",
        f"| Incorrect | {counts['incorrect']} / {len(rows)} |",
        f"| Median retrieval latency | {median:.0f} ms |",
        "",
        "Verdicts are computed from declared expectations in "
        "`scripts/retrieval_tests.py`, not written by hand, so re-running after a "
        "change reports what actually happened.",
        "",
        "## Cases",
        "",
    ]

    for case, result, verdict, reasoning, elapsed in rows:
        lines += [
            f"### {case.question}",
            "",
            f"**Type:** {case.kind} — **Verdict: {verdict}** — {elapsed:.0f} ms",
            "",
            f"{case.note}",
            "",
        ]
        if result.abstained:
            lines += [
                f"Retriever abstained at confidence {result.confidence:.2f}. "
                f"Reason: {result.reason}",
                "",
                f"*Assessment:* {reasoning}",
                "",
            ]
            continue

        top = result.hits[0]
        content = top.record.content.replace("\n", " ").strip()
        lines += [
            f"**Retrieved record:** `{top.record.record_id}` — {top.record.title}",
            "",
            f"> {content[:420]}{'…' if len(content) > 420 else ''}",
            "",
            f"**Source:** {top.record.source_url}  ",
            f"**Section:** {top.record.section_path}  ",
            f"**Category:** `{top.record.category}` — **version** {top.record.version}  ",
            f"**Similarity:** {top.similarity:.3f} (dense rank {top.dense_rank}, "
            f"lexical rank {top.lexical_rank})",
            "",
            f"*Assessment:* {reasoning}",
            "",
        ]
        if len(result.hits) > 1:
            others = ", ".join(
                f"`{h.record.record_id}` ({h.similarity:.2f})" for h in result.hits[1:4]
            )
            lines += [f"Also retrieved: {others}", ""]

    lines += [
        "## Notes on the failures",
        "",
        "Cases marked incorrect are reported rather than removed from the set. The "
        "out-of-scope questions that still retrieve records are the known limit of "
        "a similarity threshold: a bi-encoder measures topical closeness, not "
        "whether a record answers a question, and \"how many employees does Arogya "
        "First have\" is topically close to every record about the brand. Those are "
        "caught by the second gate, grounded generation, which is instructed to "
        "answer only from the retrieved records and to say so when they do not "
        "contain the answer. The voice-agent transcripts show that gate operating.",
        "",
    ]

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines))
    print(
        f"\n{counts['correct']} correct, {counts['partially correct']} partial, "
        f"{counts['incorrect']} incorrect | median {median:.0f}ms"
    )
    print(f"report: {REPORT.relative_to(ROOT)}")
    retriever.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
