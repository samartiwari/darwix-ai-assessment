"""The conversation engine, shared by every market.

One turn is: retrieve, then generate once. Retrieval runs on every caller
utterance because it costs about 30ms, which is cheaper than asking a model
whether searching is worthwhile. Generation then does extraction, intent
classification and reply writing in a single JSON response, so a turn costs one
model call rather than three round trips a caller would hear.

Grounding is enforced in two places. Retrieval refuses to return anything below
its confidence threshold, and the prompt permits factual claims only from the
records supplied. When neither yields an answer the engine uses the market pack's
own fallback wording rather than letting the model improvise a refusal.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import yaml

from core import llm
from core.kb.retrieve import RetrievalResult, Retriever
from core.telemetry import Trace

PACK_DIR = Path(__file__).resolve().parent.parent / "packs"

STAGES = ("greeting", "consent", "qualifying", "answering", "action", "closed")


@dataclass
class Pack:
    """A market's conversation policy, loaded from YAML."""

    data: dict

    @classmethod
    def load(cls, pack_id: str) -> Pack:
        path = PACK_DIR / f"{pack_id}.yaml"
        if not path.exists():
            available = ", ".join(sorted(p.stem for p in PACK_DIR.glob("*.yaml")))
            raise FileNotFoundError(f"no pack {pack_id!r}; available: {available}")
        return cls(yaml.safe_load(path.read_text()))

    def __getitem__(self, key: str):
        return self.data[key]

    def get(self, key: str, default=None):
        return self.data.get(key, default)

    @property
    def id(self) -> str:
        return self.data["id"]

    @property
    def language(self) -> str:
        return self.data.get("language", "en")

    @property
    def tts_language(self) -> str:
        return self.data.get("tts_language", self.language)

    @property
    def slots(self) -> list[dict]:
        return self.data.get("slots", [])

    @property
    def required_slots(self) -> list[str]:
        return [s["name"] for s in self.slots if s.get("required")]

    def question_for(self, slot: str) -> str:
        for entry in self.slots:
            if entry["name"] == slot:
                return " ".join(entry.get("question", "").split())
        return ""

    def text(self, key: str) -> str:
        """Pack wording, with YAML block folding collapsed to one spoken line."""
        return " ".join((self.data.get(key) or "").split())


@dataclass
class Turn:
    index: int
    caller: str
    agent: str
    intent: str = "unknown"
    grounded: bool = True
    answer_source: str = "none_needed"
    stage: str = ""
    citations: list[dict] = field(default_factory=list)
    retrieval_confidence: float = 0.0
    retrieval_abstained: bool = False
    slots_captured: dict = field(default_factory=dict)
    conflicts: list[str] = field(default_factory=list)
    latency_ms: dict = field(default_factory=dict)
    provider: str = ""


@dataclass
class CallState:
    call_id: str
    pack_id: str
    stage: str = "greeting"
    slots: dict = field(default_factory=dict)
    turns: list[Turn] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    escalated: bool = False
    escalation_reason: str = ""
    asked: list[str] = field(default_factory=list)
    outcome: str = "in_progress"  # in_progress | qualified | referred | incomplete | escalated
    started_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds")
    )

    def missing_required(self, pack: Pack) -> list[str]:
        return [s for s in pack.required_slots if not self.slots.get(s)]

    @property
    def all_citations(self) -> list[dict]:
        seen, out = set(), []
        for turn in self.turns:
            for citation in turn.citations:
                if citation["record_id"] not in seen:
                    seen.add(citation["record_id"])
                    out.append(citation)
        return out


SCHEMA_INSTRUCTION = """Reply with a single JSON object and nothing else:

{
  "intent": one of "cooperative", "question", "objection", "escalation_request",
            "out_of_scope", "refusal", "conflicting",
  "slots": {"members": str|null, "age": str|null, "city": str|null,
            "conditions": str|null, "existing_cover": str|null, "budget": str|null},
  "conflicts": [str],
  "answer_source": one of "none_needed", "context", "insufficient_context",
  "cited_records": [record ids from CONTEXT you actually used],
  "reply": what you say next, spoken aloud
}

"answer_source" describes where the facts in your reply came from:
- "none_needed"  — the caller did not ask anything factual. They answered your
                   question, agreed, greeted you or gave a detail. Your reply
                   asks the next question or acknowledges them. Most turns in a
                   qualification call are this.
- "context"      — the caller asked something factual and CONTEXT answered it.
                   Every fact in your reply comes from CONTEXT.
- "insufficient_context" — the caller asked something factual and CONTEXT does
                   not answer it. Leave "reply" empty; approved wording is used
                   instead. Never fill the gap from your own knowledge.

Set a slot only when the caller stated it. Never guess a value.

Report a contradiction in "conflicts" whenever a new detail disagrees with one
already captured, and say what disagrees with what. A stated birth year implies
an age: if the caller gave an age earlier and a birth year now, work out whether
they agree and report the conflict if they do not. The same applies to a changed
number of members, or a condition first declared and later denied."""


def build_system_prompt(pack: Pack, state: CallState) -> str:
    """Assemble the per-turn instructions.

    Facts are never placed here. This describes who the agent is, how it speaks,
    what it must not say, and where it is in the conversation. Everything factual
    arrives as retrieved context, which is what keeps a knowledge-base correction
    from needing a prompt edit.
    """
    style = "\n".join(f"- {line}" for line in pack.get("style", []))
    never = "\n".join(f"- {line}" for line in pack.get("never", []))
    escalate = "\n".join(f"- {line}" for line in pack.get("escalate_when", []))

    captured = ", ".join(f"{k}={v}" for k, v in state.slots.items() if v) or "nothing yet"
    missing = ", ".join(state.missing_required(pack)) or "none"
    next_question = ""
    for slot in state.missing_required(pack):
        if slot not in state.asked:
            next_question = pack.question_for(slot)
            break

    # The model has no clock. Asked to reconcile "I'm 30" with "born in 1975" it
    # produced 48, because it guessed the year. Any turn that reasons about an
    # age, a due date or a waiting period needs today's date stated.
    today = datetime.now(UTC).date().isoformat()

    sections = [
        f"You are {pack['agent_name']}, an automated voice assistant for "
        f"{pack['brand']}, a {pack['sector'].replace('_', ' ')} provider in "
        f"{pack['market']}. You are on a live phone call doing "
        f"{pack['flow'].replace('_', ' ')}.",
        "",
        "HOW YOU SPEAK",
        style,
        "",
        "WHAT YOU MUST NEVER DO",
        never,
        "",
        "WHEN TO HAND OVER TO A PERSON",
        escalate,
        "If any of these apply, set intent to escalation_request.",
        "",
        "GROUNDING RULE",
        "Every factual claim you make about products, premiums, waiting periods, "
        "eligibility or policy terms must come from the CONTEXT records supplied "
        "with this turn. CONTEXT is the only source you may use for facts. If "
        "CONTEXT does not contain the answer, set grounded to false and leave "
        "reply empty. Do not answer from memory, and do not approximate.",
        "",
        "CONVERSATION STATE",
        f"- Today's date is {today}. Use it for any age or date arithmetic.",
        f"- Stage: {state.stage}",
        f"- Captured so far: {captured}",
        f"- Still needed: {missing}",
    ]
    if next_question:
        sections.append(f"- The next question to ask is: {next_question}")
    if state.conflicts:
        sections.append(
            "- Unresolved contradiction: "
            + "; ".join(state.conflicts)
            + f". {pack.text('clarify_conflict')}"
        )
    sections += ["", SCHEMA_INSTRUCTION]
    return "\n".join(sections)


def _history(state: CallState, limit: int = 6) -> list[dict]:
    messages: list[dict] = []
    for turn in state.turns[-limit:]:
        messages.append({"role": "user", "content": turn.caller})
        if turn.agent:
            messages.append({"role": "assistant", "content": turn.agent})
    return messages


def _category_for(pack: Pack, utterance: str) -> str | None:
    """Bias retrieval by what the caller appears to be doing.

    A rule rather than a model call: the classification is only a search hint, and
    a wrong hint costs a slightly worse ranking rather than a wrong answer.
    """
    mapping = pack.get("retrieval_categories") or {}
    lowered = utterance.lower()
    objection_markers = (
        "expensive", "costly", "too much", "already have", "don't need",
        "do not need", "reject", "think about it", "not interested", "why should",
    )
    if any(marker in lowered for marker in objection_markers):
        return mapping.get("objection")
    return mapping.get("question")


def _merge_slots(state: CallState, extracted: dict) -> tuple[dict, list[str]]:
    """Apply newly stated slot values and report contradictions.

    A new value does not overwrite an existing one silently. Disagreement is
    recorded so the agent can ask, which is the behaviour the assessment's
    conflicting-details scenario is checking for.
    """
    captured: dict = {}
    conflicts: list[str] = []

    for name, value in (extracted or {}).items():
        if value in (None, "", "null", "unknown"):
            continue
        value = str(value).strip()
        existing = state.slots.get(name)
        if existing and existing.lower() != value.lower():
            conflicts.append(f"{name} was given as {existing!r} and now as {value!r}")
            continue
        if not existing:
            state.slots[name] = value
            captured[name] = value

    return captured, conflicts


def _next_stage(state: CallState, pack: Pack, intent: str) -> str:
    if intent == "escalation_request":
        return "closed"
    if state.stage == "greeting":
        return "qualifying"
    if state.stage in ("consent", "qualifying"):
        if state.missing_required(pack):
            return "answering" if intent in ("question", "objection") else "qualifying"
        return "action"
    if state.stage == "answering":
        return "qualifying" if state.missing_required(pack) else "action"
    if state.stage == "action":
        return "closed"
    return state.stage


class Engine:
    """Runs one conversational turn for a given market pack."""

    def __init__(self, pack_id: str, retriever: Retriever | None = None) -> None:
        self.pack = Pack.load(pack_id)
        self.retriever = retriever or Retriever()

    def greeting(self) -> str:
        return self.pack.text("greeting")

    def retrieve(self, utterance: str, state: CallState) -> RetrievalResult:
        category = _category_for(self.pack, utterance)
        result = self.retriever.search(utterance, category=category)
        # A category hint that finds nothing is a hint, not a verdict: search
        # again unfiltered rather than refusing on the strength of a guess.
        if result.abstained and category:
            result = self.retriever.search(utterance)
        return result

    def respond(
        self, utterance: str, state: CallState, trace: Trace | None = None
    ) -> Turn:
        pack = self.pack
        trace = trace or Trace(kind="voice_turn")

        retrieval = self.retrieve(utterance, state)
        trace.mark("retrieval")

        context = retrieval.as_context() if not retrieval.abstained else "(no records found)"
        messages = [
            {"role": "system", "content": build_system_prompt(pack, state)},
            *_history(state),
            {
                "role": "user",
                "content": f"CONTEXT:\n{context}\n\nThe caller just said: {utterance}",
            },
        ]

        reply = llm.chat(messages, temperature=0.2, max_tokens=500, json_mode=True, trace=trace)
        trace.mark("llm")

        parsed = reply.as_json() or {}
        intent = str(parsed.get("intent") or "unknown")
        source = str(parsed.get("answer_source") or "none_needed")
        spoken = " ".join(str(parsed.get("reply") or "").split())

        captured, conflicts = _merge_slots(state, parsed.get("slots") or {})
        conflicts += [str(c) for c in (parsed.get("conflicts") or []) if c]

        # A turn that asserts no facts needs no grounding. Treating "made no
        # factual claim" and "made an unsupported claim" alike made the agent
        # answer "I don't have that information" to a caller stating their age.
        asked_something_factual = intent in ("question", "objection", "out_of_scope")
        unsupported = source == "insufficient_context" or (
            asked_something_factual and retrieval.abstained
        )

        # Approved wording replaces model output where improvising is the failure
        # mode: an unanswerable question, and a handover.
        if intent == "escalation_request":
            spoken = pack.text("escalation")
            state.escalated = True
            state.escalation_reason = state.escalation_reason or "caller asked for a person"
            state.outcome = "escalated"
        elif unsupported or not spoken:
            spoken = pack.text("fallback_no_information")
            source = "insufficient_context"

        grounded = source != "insufficient_context"

        if conflicts:
            state.conflicts = list(dict.fromkeys(state.conflicts + conflicts))

        for slot in state.missing_required(pack):
            question = pack.question_for(slot)
            if question and question.lower()[:24] in spoken.lower():
                state.asked.append(slot)
                break

        cited = [
            c
            for c in retrieval.citations()
            if c["record_id"] in set(parsed.get("cited_records") or [])
        ] or (retrieval.citations(2) if grounded and not retrieval.abstained else [])

        turn = Turn(
            index=len(state.turns) + 1,
            caller=utterance,
            agent=spoken,
            intent=intent,
            grounded=grounded,
            answer_source=source,
            stage=state.stage,
            citations=cited,
            retrieval_confidence=round(retrieval.confidence, 3),
            retrieval_abstained=retrieval.abstained,
            slots_captured=captured,
            conflicts=conflicts,
            latency_ms=trace.stage_durations(),
            provider=reply.provider,
        )
        state.turns.append(turn)
        state.stage = _next_stage(state, pack, intent)
        return turn

    def close(self, state: CallState) -> str:
        """Decide the outcome and return the closing line."""
        if state.escalated:
            state.outcome = "escalated"
            return self.pack.text("escalation")
        if state.missing_required(self.pack) or state.conflicts:
            state.outcome = "incomplete"
            return self.pack.text("closing_incomplete")
        state.outcome = "qualified"
        return self.pack.text("closing_qualified")

    def transcript(self, state: CallState) -> dict:
        return {
            **asdict(state),
            "pack": self.pack.id,
            "brand": self.pack["brand"],
            "citations": state.all_citations,
        }

    def transcript_json(self, state: CallState) -> str:
        return json.dumps(self.transcript(state), indent=2, ensure_ascii=False)
