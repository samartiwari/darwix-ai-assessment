"""Tests for the conversation engine's deterministic logic.

Slot merging, conflict detection, stage transitions and prompt construction are
pure functions and are tested offline. Model behaviour is exercised by the
recorded scenario calls instead, since asserting on generated wording pins
phrasing rather than correctness.
"""

import pytest

from apps.voice.engine import (
    CallState,
    Pack,
    _category_for,
    _merge_slots,
    _next_stage,
    build_system_prompt,
    unsupported_figures,
)


@pytest.fixture
def pack():
    return Pack.load("in_health_en")


@pytest.fixture
def state():
    return CallState(call_id="test", pack_id="in_health_en")


class TestPack:
    def test_loads_and_exposes_required_slots(self, pack):
        assert pack.id == "in_health_en"
        assert pack.language == "en"
        assert set(pack.required_slots) == {"members", "age", "city", "conditions"}

    def test_block_folded_wording_becomes_one_spoken_line(self, pack):
        greeting = pack.text("greeting")
        assert "\n" not in greeting
        assert "recorded for quality" in greeting

    def test_holds_no_product_facts(self, pack):
        """A pack carries conversation policy; facts belong in the knowledge base.

        Hardcoding FAQs, objections or policy terms here is the failure this
        separation exists to prevent.
        """
        blob = str(pack.data).lower()
        for leaked in ("36 month", "15 working days", "8,700 hospitals", "80d", "20%"):
            assert leaked not in blob

    def test_an_unknown_pack_names_the_available_ones(self):
        with pytest.raises(FileNotFoundError, match="in_health_en"):
            Pack.load("no_such_market")


class TestSlotMerging:
    def test_captures_a_newly_stated_value(self, state):
        captured, conflicts = _merge_slots(state, {"age": "38", "city": "Pune"})
        assert captured == {"age": "38", "city": "Pune"}
        assert conflicts == []
        assert state.slots["age"] == "38"

    def test_ignores_empty_and_placeholder_values(self, state):
        captured, _ = _merge_slots(
            state, {"age": None, "city": "", "budget": "null", "members": "unknown"}
        )
        assert captured == {}
        assert state.slots == {}

    def test_a_disagreeing_value_is_reported_not_overwritten(self, state):
        _merge_slots(state, {"age": "30"})
        captured, conflicts = _merge_slots(state, {"age": "51"})
        assert captured == {}
        assert state.slots["age"] == "30", "the original value must survive for review"
        assert conflicts and "30" in conflicts[0] and "51" in conflicts[0]

    def test_restating_the_same_value_is_not_a_conflict(self, state):
        _merge_slots(state, {"city": "Pune"})
        _, conflicts = _merge_slots(state, {"city": "pune"})
        assert conflicts == []

    def test_missing_required_shrinks_as_slots_fill(self, state, pack):
        assert len(state.missing_required(pack)) == 4
        _merge_slots(state, {"age": "38", "city": "Pune"})
        assert set(state.missing_required(pack)) == {"members", "conditions"}


class TestStageTransitions:
    def test_greeting_moves_into_qualifying(self, state, pack):
        assert _next_stage(state, pack, "cooperative") == "qualifying"

    def test_an_escalation_request_closes_the_call(self, state, pack):
        state.stage = "qualifying"
        assert _next_stage(state, pack, "escalation_request") == "closed"

    def test_a_question_mid_qualification_diverts_to_answering(self, state, pack):
        state.stage = "qualifying"
        assert _next_stage(state, pack, "question") == "answering"

    def test_qualification_completes_into_the_action_stage(self, state, pack):
        state.stage = "qualifying"
        _merge_slots(state, {"members": "4", "age": "38", "city": "Pune", "conditions": "none"})
        assert _next_stage(state, pack, "cooperative") == "action"

    def test_answering_returns_to_qualifying_while_slots_remain(self, state, pack):
        state.stage = "answering"
        assert _next_stage(state, pack, "cooperative") == "qualifying"


class TestRetrievalCategory:
    def test_an_objection_biases_search_to_objections(self, pack):
        assert _category_for(pack, "honestly this is too expensive") == "objection"
        assert _category_for(pack, "I already have cover from my employer") == "objection"

    def test_a_plain_question_is_not_category_restricted(self, pack):
        assert _category_for(pack, "how long does a claim take") is None


class TestSystemPrompt:
    def test_states_the_grounding_rule_and_the_current_date(self, state, pack):
        prompt = build_system_prompt(pack, state)
        assert "CONTEXT is the only source you may use for facts" in prompt
        assert "Today's date is" in prompt

    def test_carries_conversation_state_forward(self, state, pack):
        _merge_slots(state, {"age": "38"})
        prompt = build_system_prompt(pack, state)
        assert "age=38" in prompt
        assert "Still needed" in prompt

    def test_names_the_next_question_to_ask(self, state, pack):
        prompt = build_system_prompt(pack, state)
        assert "Who would you like to cover" in prompt

    def test_surfaces_an_unresolved_contradiction(self, state, pack):
        state.conflicts = ["age was given as '30' and now as '51'"]
        prompt = build_system_prompt(pack, state)
        assert "Unresolved contradiction" in prompt
        assert "51" in prompt

    def test_contains_no_product_facts(self, state, pack):
        """The prompt must not become a place where policy terms are hardcoded."""
        prompt = build_system_prompt(pack, state).lower()
        for leaked in ("36 month", "15 working days", "8,700", "rs 9,400"):
            assert leaked not in prompt


class TestFigureGrounding:
    """A mechanical check on policy figures, independent of the model's self-report.

    The model reported a turn stating "a 36 month pre-existing disease waiting
    period" as making no factual claim, so its own report cannot be the only
    guard. A wrong waiting period is exactly what a caller would act on.
    """

    CONTEXT = (
        "Pre-existing diseases are covered after 36 months of continuous cover. "
        "Senior Care carries a 20% co-payment. Reimbursement within 15 working "
        "days. Sum insured Rs 1,000,000 (10 lakh)."
    )

    def test_accepts_figures_present_in_context(self):
        for reply in (
            "The waiting period is 36 months of continuous cover.",
            "Senior Care carries a 20% co-payment.",
            "Cover of 10 lakh is available.",
            "Settled within 15 working days.",
        ):
            assert unsupported_figures(reply, self.CONTEXT, []) == []

    def test_flags_an_invented_waiting_period(self):
        assert unsupported_figures("The waiting period is 24 months.", self.CONTEXT, []) == [
            "24 months"
        ]

    def test_flags_an_invented_percentage(self):
        """Regression: a word boundary after '%' never matches, so 35% went unchecked."""
        assert unsupported_figures("There is a 35% co-payment.", self.CONTEXT, []) == ["35%"]
        assert unsupported_figures("There is a 40 percent co-payment.", self.CONTEXT, []) == [
            "40 percent"
        ]

    def test_flags_an_invented_premium(self):
        assert unsupported_figures("That would be Rs 7,250 a year.", self.CONTEXT, []) == [
            "Rs 7,250"
        ]

    def test_flags_an_invented_sum_insured(self):
        assert unsupported_figures("Cover of 75 lakh is available.", self.CONTEXT, []) == [
            "75 lakh"
        ]

    def test_restating_the_callers_own_number_is_not_a_claim(self):
        """The agent echoing an age the caller gave is not a policy assertion."""
        assert unsupported_figures("So you are 41 years old.", self.CONTEXT, ["41"]) == []

    def test_a_reply_with_no_figures_passes(self):
        assert unsupported_figures("Which city are you in?", self.CONTEXT, []) == []
