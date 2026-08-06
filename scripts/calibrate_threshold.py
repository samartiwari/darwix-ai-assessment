"""Calibrate the retrieval abstention threshold from measured separation.

The threshold decides when the agent says it does not know. Set too low it
invents answers from irrelevant records; set too high it refuses questions the
knowledge base can answer. Neither failure is acceptable, so the value is
measured rather than guessed.

Two labelled query sets are run: questions the knowledge base should answer, and
questions it should refuse. The script reports the confidence distribution of
each and the threshold that best separates them.

    python scripts/calibrate_threshold.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Questions a caller would ask that the knowledge base does contain an answer to.
IN_SCOPE = [
    "when will my diabetes be covered",
    "how long does a reimbursement claim take",
    "this is too expensive for me",
    "what is the premium for Arogya First Senior Care",
    "my father is 67, can he get cover",
    "what is the waiting period for pre-existing conditions",
    "is maternity covered under the family floater",
    "how many hospitals are in your cashless network",
    "what happens if I miss my renewal date",
    "can I port my existing policy to you",
    "do I need a medical check-up before the policy starts",
    "what is a co-payment",
    "I already have insurance from my employer",
    "what tax benefit do I get on the premium",
    "is treatment abroad covered",
    "what is the room rent limit on senior care",
    "can I add my parents to the same policy",
    "what does restoration of cover mean",
    "which cities are in zone A",
    "I am young and healthy, why do I need this",
]

# Questions outside the knowledge base. The agent must refuse these rather than
# paraphrase whatever is nearest. Several deliberately share vocabulary with the
# corpus — a city name, a tax term, a medical word — because those are the cases
# a naive similarity threshold gets wrong.
OUT_OF_SCOPE = [
    "what is the weather in Mumbai tomorrow",
    "can you help me file my income tax return for capital gains",
    "what is the share price of your company",
    "who won the cricket match yesterday",
    "can you recommend a good cardiologist in Delhi",
    "what is my current account balance",
    "should I invest in mutual funds or fixed deposits",
    "how do I apply for a home loan",
    "what medication should I take for my blood pressure",
    "can you book me a hospital appointment",
    "what is the exchange rate for dollars",
    "do you sell car insurance in Bengaluru",
    "what are your office holidays this year",
    "how many employees does Arogya First have",
]


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(int(fraction * (len(ordered) - 1)), len(ordered) - 1)
    return ordered[index]


def main() -> int:
    from core.kb.retrieve import Retriever

    retriever = Retriever()

    # A threshold of zero disables abstention, so raw confidence is observed.
    def confidence(query: str) -> float:
        return retriever.search(query, min_score=0.0).confidence

    in_scores = [(q, confidence(q)) for q in IN_SCOPE]
    out_scores = [(q, confidence(q)) for q in OUT_OF_SCOPE]

    print("In-scope queries (should be answered)")
    print("-" * 78)
    for query, score in sorted(in_scores, key=lambda kv: kv[1]):
        print(f"  {score:.3f}  {query}")

    print("\nOut-of-scope queries (should be refused)")
    print("-" * 78)
    for query, score in sorted(out_scores, key=lambda kv: -kv[1]):
        print(f"  {score:.3f}  {query}")

    ins = [s for _, s in in_scores]
    outs = [s for _, s in out_scores]

    print("\nDistribution")
    print("-" * 78)
    print(f"  in-scope     min {min(ins):.3f}  p10 {percentile(ins, 0.1):.3f}  "
          f"median {percentile(ins, 0.5):.3f}  max {max(ins):.3f}")
    print(f"  out-of-scope min {min(outs):.3f}  median {percentile(outs, 0.5):.3f}  "
          f"p90 {percentile(outs, 0.9):.3f}  max {max(outs):.3f}")
    print(f"  overlap: in-scope min {min(ins):.3f} vs out-of-scope max {max(outs):.3f} "
          f"-> {'SEPARABLE' if min(ins) > max(outs) else 'OVERLAPPING'}")

    # Sweep candidate thresholds and report the cost of each in both directions.
    print("\nThreshold sweep")
    print("-" * 78)
    print(f"  {'thresh':>7}  {'refused in-scope':>17}  {'answered out-of-scope':>22}  {'total errors':>12}")
    best = None
    for step in range(40, 86, 2):
        threshold = step / 100
        false_refusals = sum(1 for s in ins if s < threshold)
        false_answers = sum(1 for s in outs if s >= threshold)
        errors = false_refusals + false_answers
        marker = ""
        if best is None or errors < best[1]:
            best = (threshold, errors)
            marker = "  <- best so far"
        print(
            f"  {threshold:>7.2f}  {false_refusals:>10}/{len(ins):<6}  "
            f"{false_answers:>14}/{len(outs):<7}  {errors:>12}{marker}"
        )

    print(f"\n  lowest total error at threshold {best[0]:.2f} with {best[1]} misclassified")
    print("\n  A refusal costs a caller an answer the knowledge base held; a wrong")
    print("  answer costs trust and may mislead on policy terms. The threshold is")
    print("  set toward refusal where the two are close.")
    retriever.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
