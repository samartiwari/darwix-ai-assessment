"""Write the evidence a call produces: audio, transcript, lead record, latency.

Every call writes its own folder. The recordings and transcripts the assessment
asks for are therefore a by-product of running the system rather than something
assembled by hand afterwards.

Transcripts are masked before they are written. A caller states their name, their
city and sometimes a phone number, and these files are committed to a public
repository. The masking is the same module the knowledge base uses, which is the
point of having it in the core layer.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from core.kb.pii import scan_and_mask
from core.telemetry import summarise

ROOT = Path(__file__).resolve().parents[2]


def call_dir(market: str, call_id: str) -> Path:
    """Where a call's artifacts live, keyed by market so Q1 and Q3 stay separate."""
    folder = {
        "in_health_en": "q1_voice_agent",
        "ph_life_taglish": "q3_multilingual",
        "id_multifinance": "q3_multilingual",
    }.get(market, "q1_voice_agent")
    path = ROOT / "deliverables" / folder / "calls" / call_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_audio(market: str, call_id: str, name: str, data: bytes) -> Path:
    path = call_dir(market, call_id) / name
    path.write_bytes(data)
    return path


def _mask(text: str) -> str:
    return scan_and_mask(text).text if text else text


def build_lead(state, pack) -> dict:
    """The mock CRM record a qualified or referred call produces.

    Outcome mirrors the qualification rules: a complete call with no condition
    needing review is qualified; a declared condition that does need review is
    referred; anything missing or contradictory is incomplete.
    """
    slots = dict(state.slots)
    review_terms = ("cardiac", "stroke", "cancer", "kidney", "liver", "stent")
    conditions = (slots.get("conditions") or "").lower()
    needs_review = any(term in conditions for term in review_terms)

    if state.escalated:
        outcome = "escalated"
    elif state.missing_required(pack) or state.conflicts:
        outcome = "incomplete"
    elif needs_review:
        outcome = "referred"
    else:
        outcome = "qualified"

    return {
        "lead_reference": f"AF-{datetime.now(UTC).strftime('%Y-%m')}-{state.call_id.upper()}",
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "market": pack.id,
        "brand": pack["brand"],
        "channel": "inbound_web_call",
        "outcome": outcome,
        "captured": {k: _mask(str(v)) for k, v in slots.items()},
        "missing_required": state.missing_required(pack),
        "unresolved_conflicts": [_mask(c) for c in state.conflicts],
        "escalated": state.escalated,
        "escalation_reason": state.escalation_reason or None,
        "requires_underwriter_review": needs_review,
        "turns": len(state.turns),
        "records_cited": [c["record_id"] for c in state.all_citations],
        "note": (
            "Preliminary eligibility only. No cover is promised and premiums quoted "
            "on the call are indicative and subject to underwriting."
        ),
    }


def transcript_markdown(state, pack, lead: dict) -> str:
    """A readable transcript with grounding and citations shown per turn."""
    latency = summarise(
        [{"total_ms": sum(t.latency_ms.values()), "stages": t.latency_ms} for t in state.turns]
    )

    lines = [
        f"# Call {state.call_id} — {pack['brand']} ({pack['market']})",
        "",
        f"- **Market pack:** `{pack.id}` ({pack['sector'].replace('_', ' ')}, "
        f"{pack['flow'].replace('_', ' ')})",
        f"- **Started:** {state.started_at}",
        f"- **Turns:** {len(state.turns)}",
        f"- **Outcome:** {lead['outcome']}",
        f"- **Escalated:** {'yes — ' + (state.escalation_reason or '') if state.escalated else 'no'}",
        f"- **Captured:** "
        + (", ".join(f"{k}={_mask(str(v))}" for k, v in state.slots.items()) or "nothing"),
    ]
    if state.conflicts:
        lines.append(
            "- **Unresolved contradictions:** " + "; ".join(_mask(c) for c in state.conflicts)
        )
    if latency.get("count"):
        lines.append(
            f"- **Response latency:** P50 {latency['end_to_end']['p50']} ms, "
            f"P95 {latency['end_to_end']['p95']} ms"
        )

    lines += ["", "## Transcript", ""]
    for turn in state.turns:
        lines += [
            f"**Caller:** {_mask(turn.caller)}",
            "",
            f"**{pack['agent_name']}:** {_mask(turn.agent)}",
            "",
        ]
        flags = [
            f"intent `{turn.intent}`",
            f"answer source `{turn.answer_source}`",
            f"retrieval confidence {turn.retrieval_confidence}",
        ]
        if turn.retrieval_abstained:
            flags.append("**retrieval abstained**")
        if turn.slots_captured:
            flags.append(
                "captured " + ", ".join(f"{k}={_mask(str(v))}" for k, v in turn.slots_captured.items())
            )
        if turn.conflicts:
            flags.append("**contradiction detected**")
        lines.append(f"> {' · '.join(flags)}")
        if turn.citations:
            cited = "; ".join(
                f"`{c['record_id']}` ({c['title']}) — {c['source_url']}" for c in turn.citations
            )
            lines.append(f">")
            lines.append(f"> Cited: {cited}")
        else:
            lines.append(">")
            lines.append("> Cited: none — no factual claim made from the knowledge base")
        lines.append("")

    lines += [
        "## Lead record created",
        "",
        "```json",
        json.dumps(lead, indent=2, ensure_ascii=False),
        "```",
        "",
        "## Per-turn latency",
        "",
        "| Turn | Retrieval | Generation | Total |",
        "|---|---|---|---|",
    ]
    for turn in state.turns:
        stages = turn.latency_ms or {}
        lines.append(
            f"| {turn.index} | {stages.get('retrieval', 0):.0f} ms | "
            f"{stages.get('llm', 0):.0f} ms | {sum(stages.values()):.0f} ms |"
        )
    lines.append("")
    lines.append(
        "Transcription and synthesis are timed separately in the server trace log; "
        "the figures above cover the turn from transcript to generated reply."
    )
    lines.append("")
    return "\n".join(lines)


def save_call(state, pack, scenario: str = "") -> dict:
    """Write every artifact for a finished call and return the paths."""
    directory = call_dir(pack.id, state.call_id)
    lead = build_lead(state, pack)

    masked_state = asdict(state)
    for key in ("conflicts", "escalation_reason"):
        value = masked_state.get(key)
        if isinstance(value, list):
            masked_state[key] = [_mask(v) for v in value]
        elif isinstance(value, str):
            masked_state[key] = _mask(value)
    for turn in masked_state.get("turns", []):
        turn["caller"] = _mask(turn.get("caller", ""))
        turn["agent"] = _mask(turn.get("agent", ""))
    masked_state["slots"] = {k: _mask(str(v)) for k, v in masked_state.get("slots", {}).items()}

    payload = {
        "scenario": scenario,
        "pack": pack.id,
        "market": pack["market"],
        "brand": pack["brand"],
        "state": masked_state,
        "citations": state.all_citations,
        "lead": lead,
    }

    (directory / "transcript.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False)
    )
    (directory / "transcript.md").write_text(transcript_markdown(state, pack, lead))
    (directory / "lead.json").write_text(json.dumps(lead, indent=2, ensure_ascii=False))

    return {
        "directory": str(directory.relative_to(ROOT)),
        "transcript_md": str((directory / "transcript.md").relative_to(ROOT)),
        "lead": lead,
    }
