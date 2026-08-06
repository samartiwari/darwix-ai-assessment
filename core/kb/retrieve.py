"""Hybrid retrieval with an abstention threshold.

Two searches run over the same records and their rankings are fused:

* dense vector search finds paraphrases, which is most of what a caller says —
  "when does my diabetes get covered" never matches "pre-existing disease
  waiting period" lexically;
* BM25 lexical search finds exact tokens, which dense search is weak at — plan
  names, section numbers, "80D", "Rs 25 lakh".

Reciprocal Rank Fusion combines them. It needs no score calibration between the
two systems, which is what makes the combination workable: BM25 scores and
cosine similarities are not comparable quantities.

The threshold is the part that matters most. Below a minimum confidence the
retriever returns nothing rather than its best guess, and the caller is told the
information is not available. A retriever that always returns its top result will
eventually hand over an irrelevant record that the model then paraphrases
confidently, which is the failure this design exists to prevent.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from core.kb.embed import encode_query
from core.kb.store import KnowledgeBase, Record

# Rank-fusion constant. 60 is the value from the original RRF work and is not
# sensitive: it damps the contribution of low ranks without erasing them.
RRF_K = 60

CANDIDATES_PER_SEARCH = 25

# The brand's own documents are authoritative for questions about the brand.
# They are also 51 records against 475 of background material that uses the same
# vocabulary far more often, so they are ranked among themselves rather than
# against the whole corpus.
#
# A multiplicative boost alone was tried first and did not work. Asked "what
# plans do you offer for a family", the Family Floater record never entered the
# candidate list at all: hundreds of marketing paragraphs matched "family health
# insurance" more strongly, and a boost cannot lift a record that volume has
# already crowded out of the pool.
AUTHORITATIVE_TYPES = ("internal_document",)
AUTHORITY_BOOST = 1.35

# Slots reserved for authoritative records.
# Reserved slots are selected by cosine similarity rather than by fused rank.
# Rank fusion exists to reconcile two incomparable rankings across a large
# corpus; inside a 51-record pool that problem does not arise, and fusion instead
# favoured records that happened to also match lexically. The Family Floater
# record has the fourth-highest similarity among brand records for "what plans do
# you offer for a family" but no lexical hit at all, because its text is a list of
# members and limits.
RESERVED_AUTHORITATIVE_SLOTS = 4

# The dense pass covers the whole corpus rather than a top slice. Similarity is
# only known for records the dense search returns, and gating reserved slots on
# it silently excluded any record the slice missed: with 526 records and tightly
# clustered similarities, the Family Floater record at 0.623 fell outside a
# 150-record slice and reached the pool through lexical search alone, carrying a
# similarity of zero. A flat index over a corpus this size is exhaustive at no
# measurable cost; the cap exists so the behaviour degrades predictably if the
# corpus grows by orders of magnitude.
DEEP_CANDIDATES = 5000

# Inclusion bar for a reserved slot, set below the corpus's own abstention
# threshold rather than at an absolute value. The two are different decisions: a
# reserved slot decides whether the brand's own answer is visible to the model,
# while abstention is decided by the best hit overall. Gating inclusion at the
# abstention threshold defeated the mechanism — the Family Floater record scores
# 0.623 because its text is a list of members and limits and never says "health
# insurance plan", so it was excluded from the very slot that existed to surface it.
#
# The margin is relative because an absolute value silently became the effective
# threshold for another corpus. In the Philippine and Indonesian index every record
# is an internal document, so the background pool is empty and every record is
# ranked as authoritative; a hardcoded 0.58 calibrated against English embeddings
# then discarded most of a corpus whose model scores on a different scale, and
# retrieval returned nothing at all for thirteen of thirty queries.
AUTHORITATIVE_MARGIN = 0.06


@dataclass
class Hit:
    record: Record
    score: float          # fused, boosted ranking score
    similarity: float     # dense cosine similarity, comparable across queries
    dense_rank: int | None = None
    lexical_rank: int | None = None
    rerank_score: float | None = None

    @property
    def citation(self) -> str:
        return f"{self.record.title} [{self.record.record_id}]"


@dataclass
class RetrievalResult:
    query: str
    hits: list[Hit] = field(default_factory=list)
    confidence: float = 0.0
    abstained: bool = False
    reason: str = ""
    category_filter: str | None = None

    @property
    def record_ids(self) -> list[str]:
        return [h.record.record_id for h in self.hits]

    def as_context(self, max_records: int = 4) -> str:
        """Render hits for a language model, each labelled with its citation."""
        parts = []
        for hit in self.hits[:max_records]:
            parts.append(
                f"[{hit.record.record_id}] {hit.record.title}\n"
                f"source: {hit.record.source_url}\n"
                f"{hit.record.content}"
            )
        return "\n\n---\n\n".join(parts)

    def citations(self, max_records: int = 4) -> list[dict]:
        return [
            {
                "record_id": h.record.record_id,
                "title": h.record.title,
                "source_url": h.record.source_url,
                "section_path": h.record.section_path,
                "category": h.record.category,
                "version": h.record.version,
                "similarity": round(h.similarity, 3),
            }
            for h in self.hits[:max_records]
        ]


def _min_score() -> float:
    return float(os.getenv("RETRIEVAL_MIN_SCORE", "0.64"))


def _rerank_enabled() -> bool:
    return os.getenv("RETRIEVAL_RERANK", "false").lower() in ("1", "true", "yes")


_reranker = None


def _load_reranker():
    """Cross-encoder used for ranking only, never for the abstention decision.

    Measured on 34 labelled queries, it separates off-topic questions decisively
    but scores conversational utterances near zero — "this is too expensive for
    me" scored 0.024 against a record written to answer exactly that objection.
    Thresholding on it would refuse real callers, so it reorders and nothing more.
    """
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder

        _reranker = CrossEncoder(
            os.getenv("RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L6-v2"),
            device="cpu",
            max_length=512,
        )
    return _reranker


def _top_k() -> int:
    return int(os.getenv("RETRIEVAL_TOP_K", "6"))


def _fts_query(text: str) -> str:
    """Build a safe FTS5 query.

    FTS5 treats punctuation as syntax, so an apostrophe or hyphen in a caller's
    question becomes a parse error. Tokens are extracted and OR-ed, which also
    stops one unusual word from excluding every record.
    """
    tokens = re.findall(r"[A-Za-z0-9]+", text.lower())
    tokens = [t for t in tokens if len(t) > 1][:24]
    if not tokens:
        return ""
    return " OR ".join(f'"{t}"' for t in tokens)


class Retriever:
    def __init__(
        self,
        kb: KnowledgeBase | None = None,
        multilingual: bool = False,
        min_score: float | None = None,
    ) -> None:
        self.kb = kb or KnowledgeBase()
        self.multilingual = multilingual
        # Each corpus carries its own threshold. Similarity scales differ between
        # embedding models, so one number cannot serve both.
        self.min_score = min_score
        self._order = self.kb.record_ids_in_vector_order()

    def _dense(self, query: str, limit: int) -> list[tuple[str, float]]:
        vector = encode_query(query, multilingual=self.multilingual).reshape(1, -1)
        scores, positions = self.kb.faiss_index.search(vector, min(limit, len(self._order)))
        out: list[tuple[str, float]] = []
        for score, position in zip(scores[0], positions[0], strict=False):
            if position < 0:
                continue
            out.append((self._order[position], float(score)))
        return out

    def _lexical(self, query: str, limit: int) -> list[tuple[str, float]]:
        expression = _fts_query(query)
        if not expression:
            return []
        try:
            rows = self.kb.conn.execute(
                "SELECT record_id, bm25(records_fts) AS score FROM records_fts "
                "WHERE records_fts MATCH ? ORDER BY score LIMIT ?",
                (expression, limit),
            ).fetchall()
        except Exception:  # noqa: BLE001 - a malformed query must not end a call
            return []
        # bm25() returns a negative score where more negative is better.
        return [(r["record_id"], -float(r["score"])) for r in rows]

    def search(
        self,
        query: str,
        top_k: int | None = None,
        category: str | None = None,
        min_score: float | None = None,
    ) -> RetrievalResult:
        top_k = top_k or _top_k()
        if min_score is not None:
            threshold = min_score
        elif self.min_score is not None:
            threshold = self.min_score
        else:
            threshold = _min_score()

        if not query.strip():
            return RetrievalResult(
                query=query, abstained=True, reason="empty query", category_filter=category
            )

        # A deep dense pass so authoritative records can be found even when
        # background material dominates the top of the ranking.
        dense = self._dense(query, min(DEEP_CANDIDATES, len(self._order)))
        lexical = self._lexical(query, CANDIDATES_PER_SEARCH)

        similarity = dict(dense)
        records = self.kb.get([rid for rid, _ in dense] + [rid for rid, _ in lexical])

        def eligible(rid: str) -> bool:
            record = records.get(rid)
            if record is None:
                return False
            return not category or record.category == category

        def is_authoritative(rid: str) -> bool:
            record = records.get(rid)
            return record is not None and record.source_type in AUTHORITATIVE_TYPES

        def fuse(pool_dense: list[str], pool_lexical: list[str]) -> dict[str, float]:
            """Reciprocal Rank Fusion over ranks within one pool."""
            scores: dict[str, float] = {}
            for rank, rid in enumerate(pool_dense, start=1):
                scores[rid] = scores.get(rid, 0.0) + 1.0 / (RRF_K + rank)
            for rank, rid in enumerate(pool_lexical, start=1):
                scores[rid] = scores.get(rid, 0.0) + 1.0 / (RRF_K + rank)
            return scores

        dense_ids = [rid for rid, _ in dense if eligible(rid)]
        lexical_ids = [rid for rid, _ in lexical if eligible(rid)]

        # Ranks within the whole corpus, kept for reporting.
        dense_rank = {rid: i + 1 for i, rid in enumerate(dense_ids)}
        lexical_rank = {rid: i + 1 for i, rid in enumerate(lexical_ids)}

        background = fuse(
            [r for r in dense_ids[:CANDIDATES_PER_SEARCH] if not is_authoritative(r)],
            [r for r in lexical_ids if not is_authoritative(r)],
        )
        authoritative = fuse(
            [r for r in dense_ids if is_authoritative(r)],
            [r for r in lexical_ids if is_authoritative(r)],
        )

        if not background and not authoritative:
            return RetrievalResult(
                query=query,
                abstained=True,
                reason=(
                    f"no records in category {category!r}"
                    if category
                    else "no candidate records matched"
                ),
                category_filter=category,
            )

        def to_hits(scores: dict[str, float], boost: float) -> list[Hit]:
            out = [
                Hit(
                    record=records[rid],
                    score=score * boost,
                    similarity=similarity.get(rid, 0.0),
                    dense_rank=dense_rank.get(rid),
                    lexical_rank=lexical_rank.get(rid),
                )
                for rid, score in scores.items()
                if rid in records
            ]
            out.sort(key=lambda h: -h.score)
            return out

        # Authoritative records take at most a few slots, and only when they
        # individually clear the relevance threshold. Reserving slots
        # unconditionally would spend them on brand documents that do not answer
        # a general question.
        authoritative_hits = to_hits(authoritative, AUTHORITY_BOOST)
        authoritative_hits.sort(key=lambda h: -h.similarity)
        authoritative_min = max(0.0, threshold - AUTHORITATIVE_MARGIN)
        reserved = [
            h for h in authoritative_hits if h.similarity >= authoritative_min
        ][:RESERVED_AUTHORITATIVE_SLOTS]

        chosen_ids = {h.record.record_id for h in reserved}
        remainder = [
            h for h in to_hits(background, 1.0) if h.record.record_id not in chosen_ids
        ]

        # Reserved hits keep their similarity ordering and sit ahead of
        # background hits, whose fused scores are on a different scale.
        remainder.sort(key=lambda h: -h.score)
        hits = reserved + remainder

        if _rerank_enabled() and len(hits) > 1:
            pairs = [(query, h.record.content[:1200]) for h in hits]
            relevance = _load_reranker().predict(pairs)
            for hit, value in zip(hits, relevance, strict=False):
                hit.rerank_score = float(value)
            hits.sort(key=lambda h: -(h.rerank_score or 0.0))

        hits = hits[:top_k]

        # Confidence is the best dense cosine similarity among the returned
        # records. Cosine is comparable across queries, so one fixed threshold
        # means the same thing every time; a fused rank score would not, since it
        # depends on how many systems retrieved the record.
        confidence = max((h.similarity for h in hits), default=0.0)

        if confidence < threshold:
            return RetrievalResult(
                query=query,
                hits=[],
                confidence=confidence,
                abstained=True,
                reason=(
                    f"best similarity {confidence:.2f} is below the {threshold:.2f} "
                    "threshold, so no record is offered"
                ),
                category_filter=category,
            )

        return RetrievalResult(
            query=query, hits=hits, confidence=confidence, category_filter=category
        )

    def close(self) -> None:
        self.kb.close()


_retriever: Retriever | None = None


def get_retriever() -> Retriever:
    """Shared retriever. Loading the index and model per turn would be wasteful."""
    global _retriever
    if _retriever is None:
        _retriever = Retriever()
    return _retriever


def search(query: str, **kwargs) -> RetrievalResult:
    return get_retriever().search(query, **kwargs)
