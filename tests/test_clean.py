"""Tests for the cleaning heuristics.

These run offline and cover the cases that caused real damage during
development: navigation blocks surviving, and PDF prose being mistaken for
navigation.
"""

from core.kb.clean import clean_text, drop_repeated_across_documents


def test_removes_navigation_run_from_web_page():
    text = "\n".join(
        [
            "Health Insurance Plans",
            "Health insurance covers hospitalisation costs up to the sum insured.",
            "Quick Links",
            "Network Hospital",
            "Family Health Insurance",
            "Senior Citizen Plans",
            "Renew Policy",
            "A waiting period of 36 months applies to pre-existing conditions.",
        ]
    )
    result = clean_text(text, source_type="web_page")
    assert "Quick Links" not in result.text
    assert "Network Hospital" not in result.text
    assert "waiting period of 36 months" in result.text
    assert "Health insurance covers hospitalisation" in result.text


def test_keeps_isolated_heading():
    """A lone short line is a heading and chunking depends on it."""
    text = "\n".join(
        [
            "Waiting Periods",
            "Pre-existing diseases are covered after thirty-six months of continuous cover.",
            "Room Rent Limits",
            "Room rent is capped at one percent of the sum insured per day.",
        ]
    )
    result = clean_text(text, source_type="web_page")
    assert "Waiting Periods" in result.text
    assert "Room Rent Limits" in result.text


def test_pdf_prose_is_not_treated_as_navigation():
    """PDF extraction yields short lines; they are content, not a menu."""
    lines = [
        "The missing middle comprises",
        "about thirty percent of the",
        "population without any form",
        "of financial protection for",
        "health expenditure in India",
    ]
    text = "\n".join(lines)
    web = clean_text(text, source_type="web_page")
    pdf = clean_text(text, source_type="pdf")
    assert pdf.text.count("\n") == len(lines) - 1
    assert len(pdf.text.split()) > len(web.text.split())


def test_table_rows_are_never_dropped():
    text = "\n".join(
        [
            "Menu",
            "| Parameter | Optima Secure | Optima Lite |",
            "| Coverage Area | India | India |",
            "| Plan Type | Comprehensive | Base |",
        ]
    )
    result = clean_text(text, source_type="web_page")
    assert result.text.count("|") >= 9
    assert "Optima Secure" in result.text


def test_removes_marketing_calls_to_action():
    text = "\n".join(
        [
            "Coverage begins after the policy is issued and the premium is received.",
            "With Niva Bupa Today!",
            "Rated by mint as India's Best Health Insurer 2024",
            "Terms apply*",
            "The sum insured may be restored once per policy year.",
        ]
    )
    result = clean_text(text, source_type="web_page")
    assert "Today!" not in result.text
    assert "Rated by" not in result.text
    assert "sum insured may be restored" in result.text


def test_drops_lines_repeated_across_documents():
    shared = "Toll free 1800 123 4567"
    docs = {
        "a": f"Waiting periods apply.\n{shared}",
        "b": f"Room rent is capped.\n{shared}",
        "c": f"Cashless claims are settled directly.\n{shared}",
    }
    trimmed, repeated = drop_repeated_across_documents(docs, min_documents=3)
    assert shared in repeated
    assert all(shared not in text for text in trimmed.values())
    assert "Waiting periods apply." in trimmed["a"]


def test_reports_how_many_lines_were_dropped():
    text = "\n".join(["Menu", "Login", "Contact Us", "Real content sentence here."])
    result = clean_text(text, source_type="web_page")
    assert result.lines_in == 4
    assert result.lines_dropped >= 2
