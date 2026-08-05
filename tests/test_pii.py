"""Tests for personal-data detection and masking.

The false-positive cases are regressions. An earlier version redacted premium
tables in a policy report as Aadhaar and phone numbers, and masked credited
report authors as customers. Both destroyed real content, so both are pinned.
"""

from core.kb.pii import csv_to_text, scan_and_mask


class TestDetection:
    def test_masks_email_and_phone_with_country_code(self):
        text = "Contact rajesh.kumar1982@gmail.com or +91 98210 45566 for details."
        result = scan_and_mask(text)
        assert "rajesh.kumar1982@gmail.com" not in result.text
        assert "98210" not in result.text
        assert "EMAIL" in result.kinds
        assert "PHONE" in result.kinds

    def test_masks_pan_without_needing_context(self):
        result = scan_and_mask("PAN collected at advisor stage: ABCPK1234F.")
        assert "ABCPK1234F" not in result.text
        assert result.kinds == ["PAN"]

    def test_masks_policy_and_lead_references(self):
        result = scan_and_mask("Lead reference AF-2025-03-14421, policy AF-H-0098231.")
        assert "AF-2025-03-14421" not in result.text
        assert "AF-H-0098231" not in result.text
        assert set(result.kinds) == {"LEAD_REF", "POLICY_NUMBER"}

    def test_masks_bare_phone_number_when_a_cue_is_present(self):
        result = scan_and_mask("His contact number 9821045566 was captured.")
        assert "9821045566" not in result.text
        assert "PHONE" in result.kinds

    def test_masks_aadhaar_when_a_cue_is_present(self):
        result = scan_and_mask("Aadhaar 2345 6789 0123 was verified.")
        assert "2345 6789 0123" not in result.text
        assert "AADHAAR" in result.kinds

    def test_masks_customer_name_after_a_role_cue(self):
        result = scan_and_mask("Caller: Rajesh Kumar, 42, Pune.")
        assert "Rajesh Kumar" not in result.text
        assert "Caller:" in result.text
        assert "NAME" in result.kinds


class TestFalsePositives:
    def test_statistical_table_digits_are_not_aadhaar(self):
        """Regression: quintile figures in a policy report were being redacted."""
        text = (
            "Rural Urban Rural Urban 3rd quintile 831 1046 1102 "
            "4th quintile 487 876 1150 1204 5th quintile 931 1329 1402"
        )
        result = scan_and_mask(text)
        assert "REDACTED" not in result.text
        assert result.kinds == []

    def test_premium_amounts_are_not_phone_numbers(self):
        """Regression: 'Rs 27270 25245' was matching the mobile pattern."""
        text = "Tenure 1 year subject to lifelong renewal 03911 72705 25245 27270 25000 20000"
        result = scan_and_mask(text)
        assert "REDACTED" not in result.text

    def test_credited_authors_are_not_masked(self):
        """Regression: report acknowledgements were treated as customer data."""
        text = (
            "We acknowledge contributions to this report. 1. Dr K Madan Gopal, "
            "Senior Consultant, NITI Aayog 2. Ms Anjali Sharma, Chief Manager, "
            "Oriental Insurance company ltd."
        )
        result = scan_and_mask(text)
        assert "Madan Gopal" in result.text
        assert "Anjali Sharma" in result.text

    def test_public_official_in_encyclopedic_text_is_not_masked(self):
        text = "At present the authority is chaired by Mr. Ajay Seth and its members are listed."
        result = scan_and_mask(text)
        assert "Ajay Seth" in result.text

    def test_product_names_are_not_treated_as_people(self):
        text = "Optima Secure and Arogya First Family Floater both restore the sum insured."
        result = scan_and_mask(text)
        assert "REDACTED" not in result.text


class TestQuarantine:
    def test_records_export_is_quarantined_not_merely_masked(self):
        rows = "\n".join(
            f"name: Person {i}; phone: 98210455{i:02d}; "
            f"email: person{i}@example.com; pan: ABCPK12{i:02d}F"
            for i in range(10)
        )
        result = scan_and_mask(rows)
        assert result.quarantined
        assert "records export" in result.reason

    def test_prose_with_one_example_is_masked_but_kept(self):
        text = (
            "The script guides the agent through qualification. " * 40
            + "Example: caller: Rajesh Kumar, contact number 9821045566."
        )
        result = scan_and_mask(text)
        assert result.has_pii
        assert not result.quarantined

    def test_clean_document_is_neither_flagged_nor_quarantined(self):
        text = "Pre-existing diseases are covered after thirty-six months of continuous cover."
        result = scan_and_mask(text)
        assert not result.has_pii
        assert not result.quarantined


def test_csv_is_rendered_with_labels_so_cues_are_visible():
    raw = "name,phone\nRajesh Kumar,9821045566"
    text = csv_to_text(raw)
    assert "name: Rajesh Kumar" in text
    assert "phone: 9821045566" in text
    # The labels are what let the context-required detectors fire.
    assert scan_and_mask(text).has_pii
