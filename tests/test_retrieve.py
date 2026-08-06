"""Tests for retrieval.

These need a built knowledge base and are skipped when one is absent, so the
offline suite still runs on a fresh clone. Build it with:

    python scripts/build_kb.py
"""

import pytest

from core.kb.retrieve import _fts_query
from core.kb.store import db_path, faiss_path

needs_kb = pytest.mark.skipif(
    not (db_path().exists() and faiss_path().exists()),
    reason="no knowledge base built; run scripts/build_kb.py",
)


class TestFtsQuery:
    """FTS5 treats punctuation as syntax, so caller phrasing must be sanitised."""

    def test_apostrophes_and_hyphens_do_not_break_the_query(self):
        expression = _fts_query("what's the pre-existing disease waiting period?")
        assert '"pre"' in expression
        assert "'" not in expression
        assert "?" not in expression

    def test_tokens_are_or_joined_so_one_rare_word_excludes_nothing(self):
        assert " OR " in _fts_query("zone A pricing Bengaluru")

    def test_empty_and_punctuation_only_queries_are_safe(self):
        assert _fts_query("") == ""
        assert _fts_query("???  ...") == ""


@needs_kb
class TestRetrieval:
    @pytest.fixture(scope="class")
    def retriever(self):
        from core.kb.retrieve import Retriever

        r = Retriever()
        yield r
        r.close()

    def test_finds_the_waiting_period_rule_from_a_paraphrase(self, retriever):
        """Dense search must bridge 'diabetes' to 'pre-existing disease'."""
        result = retriever.search("when will my diabetes be covered")
        assert not result.abstained
        text = " ".join(h.record.content.lower() for h in result.hits)
        assert "pre-existing" in text

    def test_finds_an_exact_numeric_term(self, retriever):
        result = retriever.search("what is the co-payment on the senior citizen plan")
        assert not result.abstained
        assert any("20%" in h.record.content for h in result.hits)

    def test_returns_a_table_record_with_its_header(self, retriever):
        result = retriever.search("which cities count as zone A for pricing")
        assert not result.abstained
        tables = [h for h in result.hits if h.record.kind == "table"]
        assert tables, "expected the zone table"
        assert "Zone" in tables[0].record.content

    def test_abstains_on_a_plainly_out_of_scope_question(self, retriever):
        result = retriever.search("who won the cricket match yesterday")
        assert result.abstained
        assert not result.hits
        assert "threshold" in result.reason

    def test_abstains_when_a_shared_place_name_is_the_only_overlap(self, retriever):
        """Regression: 'weather in Mumbai' matched the zone table on one token."""
        result = retriever.search("what is the weather in Mumbai tomorrow")
        assert result.abstained

    def test_abstains_on_an_empty_query(self, retriever):
        assert retriever.search("   ").abstained

    def test_brand_records_are_not_crowded_out_by_background_volume(self, retriever):
        """Regression: the brand's own records lost to marketing prose on volume.

        The corpus holds roughly ten times more background material than brand
        documents, using the same vocabulary.
        """
        result = retriever.search("what health insurance plans do you offer for a family")
        assert not result.abstained
        internal = [h for h in result.hits if h.record.source_type == "internal_document"]
        assert internal, "expected at least one record from the brand's own documents"
        assert any("floater" in h.record.content.lower() for h in result.hits)

    def test_every_hit_carries_a_citation(self, retriever):
        result = retriever.search("how long does a reimbursement claim take")
        assert not result.abstained
        for citation in result.citations():
            assert citation["record_id"]
            assert citation["source_url"]
            assert citation["title"]

    def test_category_filter_restricts_results(self, retriever):
        result = retriever.search("this is too expensive", category="objection")
        if not result.abstained:
            assert all(h.record.category == "objection" for h in result.hits)

    def test_context_rendering_labels_each_record(self, retriever):
        result = retriever.search("what is a co-payment")
        assert not result.abstained
        context = result.as_context()
        assert result.hits[0].record.record_id in context
        assert "source:" in context

    def test_a_masked_record_never_leaks_personal_data(self, retriever):
        """The sales script holds an example call; retrieval must return it masked."""
        result = retriever.search("example of a completed qualification call")
        for hit in result.hits:
            assert "9821045566" not in hit.record.content
            assert "rajesh.kumar1982@gmail.com" not in hit.record.content
