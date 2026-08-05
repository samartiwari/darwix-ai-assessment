"""Tests for chunking.

Two of these are regressions. Document metadata lines became records whose
entire content was a version stamp, and nine-word fragments were being indexed
as though they were answers.
"""

from core.kb.chunk import (
    MAX_WORDS,
    MIN_WORDS,
    chunk_document,
    is_answerable,
    strip_metadata_lines,
)

MARKDOWN = """# Arogya First — Customer FAQ Sheet

Version 1.9 | Last updated 2025-03-15 | Contact centre reference

## What is a waiting period?

A waiting period is the time you must hold the policy before a particular
benefit becomes claimable. Arogya First applies an initial waiting period of 30
days from policy start, except for accidental hospitalisation.

## What is a co-payment?

A co-payment is the share of an admissible claim you pay yourself. Senior Care
carries a 20% co-payment on every claim.
"""

TABLE_DOC = """# Rules

## Age eligibility

| Age band | Eligible products | Notes |
| 18 to 45 | Secure, Family Floater | Standard underwriting |
| 46 to 60 | Secure, Family Floater | Medical check-up above Rs 25 lakh |
| 61 to 80 | Senior Care only | Pre-policy check-up mandatory |
"""


def test_metadata_lines_are_stripped():
    """Regression: a version stamp became a retrievable record."""
    assert "Version 1.9" in MARKDOWN
    assert "Version 1.9" not in strip_metadata_lines(MARKDOWN)


def test_no_record_is_only_document_metadata():
    chunks = chunk_document(MARKDOWN, "int_001", "FAQ Sheet", "internal_document")
    for chunk in chunks:
        assert "Last updated" not in chunk.content
        assert not chunk.content.strip().startswith("Version")


def test_section_headings_become_the_section_path():
    chunks = chunk_document(MARKDOWN, "int_001", "FAQ Sheet", "internal_document")
    paths = {c.section_path for c in chunks}
    assert any("What is a waiting period?" in p for p in paths)
    assert any("What is a co-payment?" in p for p in paths)
    # The trail keeps the document title above the section.
    assert all(p.startswith("Arogya First") for p in paths)


def test_records_are_self_contained():
    """Regression: fragments of under ten words were being indexed alone.

    Every prose record either carries enough text to answer on its own, or
    carries its heading so the reader knows what it answers.
    """
    chunks = chunk_document(MARKDOWN, "int_001", "FAQ Sheet", "internal_document")
    prose = [c for c in chunks if c.kind == "prose"]
    assert prose
    for chunk in prose:
        heading = chunk.section_path.split(" > ")[-1]
        assert chunk.word_count >= MIN_WORDS or heading in chunk.content


def test_short_answer_gains_its_question():
    """A 23-word co-payment answer should open with the question it answers."""
    chunks = chunk_document(MARKDOWN, "int_001", "FAQ Sheet", "internal_document")
    copay = next(c for c in chunks if "co-payment is the share" in c.content)
    assert copay.content.startswith("What is a co-payment?")


def test_table_keeps_its_header_row():
    chunks = chunk_document(TABLE_DOC, "int_004", "Rules", "internal_document")
    tables = [c for c in chunks if c.kind == "table"]
    assert len(tables) == 1
    assert "Age band" in tables[0].content
    assert "61 to 80" in tables[0].content


def test_large_table_repeats_the_header_on_each_part():
    rows = "\n".join(f"| Row {i} | value {i} | note {i} |" for i in range(30))
    doc = f"# T\n\n## Big table\n\n| Col A | Col B | Col C |\n{rows}\n"
    chunks = chunk_document(doc, "d", "T", "internal_document")
    tables = [c for c in chunks if c.kind == "table"]
    assert len(tables) > 1
    assert all("Col A" in c.content for c in tables)


def test_no_record_exceeds_the_ceiling():
    long_text = "Health insurance covers hospitalisation costs. " * 400
    chunks = chunk_document(long_text, "src_001", "Long", "web_page")
    assert chunks
    assert all(c.word_count <= MAX_WORDS for c in chunks)


def test_windows_overlap_so_context_is_not_lost_at_a_boundary():
    paragraphs = "\n\n".join(
        f"Paragraph {i} discusses the sum insured and the premium payable in detail, "
        f"including how restoration applies within a policy year for member {i}."
        for i in range(20)
    )
    chunks = chunk_document(paragraphs, "src_001", "Doc", "web_page")
    assert len(chunks) > 1
    # Consecutive records share text, so a sentence split across a boundary is
    # still retrievable from one of them.
    assert any(
        set(chunks[i].content.split()) & set(chunks[i + 1].content.split())
        for i in range(len(chunks) - 1)
    )


def test_pdf_tables_passed_separately_are_indexed():
    tables = [[["Quintile", "Rural", "Urban"], ["3rd", "831", "1046"], ["4th", "487", "876"]]]
    chunks = chunk_document("Some prose about coverage gaps.", "src_009", "Report", "pdf", tables)
    table_chunks = [c for c in chunks if c.kind == "table"]
    assert len(table_chunks) == 1
    assert "Quintile" in table_chunks[0].content
    assert "831" in table_chunks[0].content


def test_ordinals_are_contiguous():
    chunks = chunk_document(MARKDOWN, "int_001", "FAQ", "internal_document")
    assert [c.ordinal for c in chunks] == list(range(len(chunks)))


class TestAnswerability:
    def test_keeps_substantive_prose(self):
        text = (
            "Pre-existing diseases are covered after thirty-six months of continuous "
            "cover under the policy, and any condition diagnosed in the forty-eight "
            "months before the start date is treated as pre-existing."
        )
        assert is_answerable(text)

    def test_keeps_a_long_paragraph_that_cites_a_few_sources(self):
        """Regression: one ISSN discarded a 250-word substantive passage.

        Density, not count: a long passage may cite three sources and still be
        prose, while a reference block is nothing but citations.
        """
        body = (
            "The private health insurance market, known in Russian as voluntary "
            "health insurance, developed alongside the compulsory scheme and now "
            "covers a substantial minority of urban employees, with employers "
            "purchasing group cover to secure faster access to specialists. "
        ) * 6
        text = body + "ISSN 0971-751X. Retrieved 2024-11-10. See also pp. 24."
        assert len(text.split()) > 200
        assert is_answerable(text)

    def test_drops_a_reference_block(self):
        text = (
            'The Hindu. ISSN 0971-751X. Archived from the original on 2024-11-12. '
            'Retrieved 2024-11-10. - ↑ Hooda, Shailender Kumar (2020-06-20). '
            '"Decoding Ayushman Bharat". Economic and Political Weekly. '
            'Retrieved 2024-02-23.'
        )
        assert not is_answerable(text)

    def test_drops_a_contents_page(self):
        text = "III. Pricing 25 ....... 7. Key Challenges ............ 30 ......... 41"
        assert not is_answerable(text)

    def test_drops_chart_axis_debris(self):
        assert not is_answerable("30%\n25% 24.0% 20.7% 20% 15% 13.0%")
        assert not is_answerable("10% 8.5%\n7.0% 7.4% 7.5% 5%")

    def test_drops_front_matter_identifiers(self):
        assert not is_answerable("978-81-949510-2-5\nISBN : DOI: 10.31219/osf.io/s2x8r")

    def test_keeps_a_short_but_readable_sentence(self):
        assert is_answerable("Accidental hospitalisation is covered from day one.")
