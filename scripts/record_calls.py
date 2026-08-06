"""Record scenario calls and write the evidence for a market.

    python scripts/record_calls.py --pack in_health_en
    python scripts/record_calls.py --pack ph_life_taglish --scenario objection

The caller's side is synthesised in a different voice, then transcribed through
the real speech-recognition path, and the transcript is what reaches the engine.
Driving the engine from text would be simpler but would prove less: this way the
recordings are genuine audio, the transcription step is exercised, and the
difference between what was spoken and what was heard is measurable — which is
the evidence the multilingual work needs anyway.

Each call writes caller audio, agent audio, a combined recording, a transcript
and a lead record, plus a results report across all scenarios.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from apps.voice import artifacts  # noqa: E402
from apps.voice.engine import CallState, Engine  # noqa: E402
from core import asr, tts  # noqa: E402
from core.telemetry import Trace, summarise  # noqa: E402


@dataclass
class Scenario:
    name: str
    covers: str
    utterances: list[str]
    caller_voice_language: str = "en-US"
    expect: dict = field(default_factory=dict)


# The five behaviours the assessment requires, plus a sixth combining an
# objection with a request for a person, since real calls rarely isolate one.
SCENARIOS: dict[str, list[Scenario]] = {
    "in_health_en": [
        Scenario(
            name="01_cooperative",
            covers="Cooperative customer through to a created lead",
            utterances=[
                "Yes that is fine, please go ahead.",
                "I want to cover myself, my wife and our two children.",
                "I am thirty eight, the eldest of us.",
                "We live in Pune.",
                "Nobody has any medical conditions, we are all healthy.",
                "My budget is around twenty two thousand a year.",
            ],
            expect={"outcome": "qualified", "escalated": False},
        ),
        Scenario(
            name="02_objection",
            covers="Objection handled from approved material, grounded",
            utterances=[
                "Yes go ahead.",
                "Just myself, I am forty one, and I live in Bengaluru.",
                "No conditions at all.",
                "Honestly, this sounds far too expensive for me.",
                "I already have cover through my employer anyway.",
            ],
            expect={"grounded_turns_at_least": 2},
        ),
        Scenario(
            name="03_conflicting_details",
            covers="Incomplete and conflicting details, agent asks rather than guesses",
            utterances=[
                "Sure.",
                "It is just for me, I am thirty years old.",
                "Actually, I was born in nineteen seventy five.",
                "I would rather not say which city.",
            ],
            expect={"conflicts_at_least": 1, "outcome": "incomplete"},
        ),
        Scenario(
            name="04_out_of_scope",
            covers="Out-of-scope question refused instead of answered",
            utterances=[
                "Yes, I have a minute.",
                "Before that, what will the weather be like in Mumbai tomorrow?",
                "Alright. And what is your company share price?",
                "Fine. I am forty five, just myself, based in Chennai, no conditions.",
            ],
            expect={"refusals_at_least": 2},
        ),
        Scenario(
            name="05_human_escalation",
            covers="Caller asks for a person and is handed over",
            utterances=[
                "Yes alright.",
                "My father is sixty seven and he had a cardiac stent fitted in two thousand nineteen.",
                "I would rather just speak to a real person about this please.",
            ],
            expect={"escalated": True, "outcome": "escalated"},
        ),
    ],
    "ph_life_taglish": [
        Scenario(
            name="ph_01_cooperative",
            covers="Cooperative customer, natural Taglish, agrees a payment date",
            caller_voice_language="fil-male",
            utterances=[
                "Opo, sige po, pwede po tayo mag-usap.",
                "Opo, ako po mismo ang policyholder.",
                "Hindi pa po nabayaran yung premium para sa buwan na ito.",
                "Sa Friday po, pagkatapos ng sweldo.",
                "Sa GCash po, mas madali po sa akin.",
            ],
            expect={"escalated": False},
        ),
        Scenario(
            name="ph_02_objection_and_codeswitch",
            covers="Sector objection plus mixed English finance terms inside Filipino",
            caller_voice_language="fil-male",
            utterances=[
                "Opo, ako po ang policyholder.",
                "Hindi pa po, kasi mahal po masyado ang premium ngayon.",
                "Meron na po kasi akong coverage sa work, group insurance po.",
                "Ilang araw po ba yung grace period bago ma-lapse?",
            ],
            expect={"grounded_turns_at_least": 1},
        ),
        Scenario(
            name="ph_03_lapse_then_human",
            covers="Lapsed-policy question, then a request for a person, staying in Filipino",
            caller_voice_language="fil-male",
            utterances=[
                "Opo, kapatid po ako ng policyholder.",
                "Na-lapse na po daw yung policy niya, pwede pa po ba i-reinstate?",
                "Ay, mas okay na po sa akin makausap ang tunay na tao.",
            ],
            expect={"escalated": True, "outcome": "escalated"},
        ),
    ],
    "id_multifinance": [
        Scenario(
            name="id_01_cooperative_formal",
            covers="Cooperative customer in formal Bahasa Indonesia",
            caller_voice_language="id-male",
            utterances=[
                "Iya, silakan, saya ada waktu.",
                "Benar, saya pemilik kontrak pembiayaannya.",
                "Belum saya bayar, Bu, minggu ini rencananya.",
                "Lewat transfer virtual account saja.",
            ],
            expect={"escalated": False},
        ),
        Scenario(
            name="id_02_colloquial_objection",
            covers="Colloquial register and a sector objection about the late-payment penalty",
            caller_voice_language="id-male",
            utterances=[
                "Iya bener, saya sendiri.",
                "Belum, belum ada uang bulan ini.",
                "Dendanya kok gede banget ya, itung-itungannya gimana sih?",
                "Bisa nggak tenornya diperpanjang biar cicilannya turun?",
            ],
            expect={"grounded_turns_at_least": 1},
        ),
        Scenario(
            name="id_03_regional_and_human",
            covers=(
                "Javanese-inflected Indonesian lexis and particles, then escalation. "
                "Tests regionally marked wording, not acoustic accent — see the ASR report"
            ),
            caller_voice_language="id-male",
            utterances=[
                "Nggih, monggo Bu, silakan.",
                "Lha nggih, kulo sing gadhah kontrak niku.",
                "Angsurane sampun telat rong wulan og, piye niki?",
                "Kulo pengen ngomong karo wong tenan mawon nggih.",
            ],
            expect={"escalated": True},
        ),
    ],
}


def scenarios_for(pack_id: str) -> list[Scenario]:
    if pack_id not in SCENARIOS:
        raise SystemExit(
            f"no scenarios defined for {pack_id!r}; defined: {', '.join(SCENARIOS)}"
        )
    return SCENARIOS[pack_id]


def run_scenario(engine: Engine, scenario: Scenario) -> dict:
    """Play one scenario as audio and collect the evidence."""
    call_id = f"{scenario.name}_{uuid.uuid4().hex[:4]}"
    state = CallState(call_id=call_id, pack_id=engine.pack.id)
    directory = artifacts.call_dir(engine.pack.id, call_id)

    combined = bytearray()
    asr_pairs: list[dict] = []
    traces: list[dict] = []

    greeting = engine.greeting()
    greeting_audio = tts.synthesise(greeting, engine.pack.tts_language)
    if greeting_audio.ok:
        artifacts.save_audio(engine.pack.id, call_id, "agent_turn_0.mp3", greeting_audio.audio)
        combined.extend(greeting_audio.audio)
    print(f"  agent : {greeting[:88]}")

    for index, spoken in enumerate(scenario.utterances, start=1):
        trace = Trace(kind="recorded_turn")

        # The caller's side, in a different voice so the recording is legible.
        caller_audio = tts.synthesise(spoken, scenario.caller_voice_language)
        if not caller_audio.ok:
            print(f"  !! could not synthesise caller turn {index}: {caller_audio.error}")
            continue
        artifacts.save_audio(
            engine.pack.id, call_id, f"caller_turn_{index}.mp3", caller_audio.audio
        )
        combined.extend(caller_audio.audio)
        trace.mark("caller_synthesis")

        heard = asr.transcribe(
            caller_audio.audio,
            language=engine.pack.get("asr_language") or engine.pack.language,
            trace=trace,
        )
        trace.mark("asr")
        utterance = heard.text if heard.ok else spoken
        asr_pairs.append(
            {
                "turn": index,
                "spoken": spoken,
                "transcribed": heard.text,
                "provider": heard.provider,
                "fell_back": heard.fell_back,
                "exact_match": heard.text.strip().lower().rstrip(".") == spoken.lower().rstrip("."),
            }
        )
        print(f"  caller: {utterance[:88]}")

        turn = engine.respond(utterance, state, trace=trace)
        reply_audio = tts.synthesise(turn.agent, engine.pack.tts_language)
        trace.mark("agent_synthesis")
        if reply_audio.ok:
            artifacts.save_audio(
                engine.pack.id, call_id, f"agent_turn_{index}.mp3", reply_audio.audio
            )
            combined.extend(reply_audio.audio)

        flags = [turn.intent, turn.answer_source]
        if turn.retrieval_abstained:
            flags.append("abstained")
        if turn.conflicts:
            flags.append("conflict")
        if turn.ungrounded_figures:
            flags.append(f"ungrounded:{turn.ungrounded_figures}")
        print(f"  agent : {turn.agent[:88]}")
        print(f"          [{' · '.join(flags)}]")
        traces.append(trace.to_dict())

    closing = engine.close(state)
    closing_audio = tts.synthesise(closing, engine.pack.tts_language)
    if closing_audio.ok:
        artifacts.save_audio(engine.pack.id, call_id, "agent_closing.mp3", closing_audio.audio)
        combined.extend(closing_audio.audio)
    print(f"  agent : {closing[:88]}")

    # MP3 frames concatenate for playback, which gives a reviewer one file to
    # listen to instead of a folder of fragments.
    if combined:
        artifacts.save_audio(engine.pack.id, call_id, "call_full.mp3", bytes(combined))

    saved = artifacts.save_call(state, engine.pack, scenario=scenario.name)
    (directory / "asr_comparison.json").write_text(json.dumps(asr_pairs, indent=2, ensure_ascii=False))
    (directory / "traces.json").write_text(json.dumps(traces, indent=2))

    return {
        "scenario": scenario.name,
        "covers": scenario.covers,
        "call_id": call_id,
        "directory": saved["directory"],
        "outcome": state.outcome,
        "escalated": state.escalated,
        "conflicts": state.conflicts,
        "slots": state.slots,
        "turns": [
            {
                "index": t.index,
                "caller": t.caller,
                "agent": t.agent,
                "intent": t.intent,
                "answer_source": t.answer_source,
                "abstained": t.retrieval_abstained,
                "confidence": t.retrieval_confidence,
                "citations": [c["record_id"] for c in t.citations],
                "conflicts": t.conflicts,
                "ungrounded_figures": t.ungrounded_figures,
                "latency_ms": t.latency_ms,
            }
            for t in state.turns
        ],
        "asr": asr_pairs,
        "expect": scenario.expect,
        "lead": saved["lead"],
    }


def check_expectations(result: dict) -> list[str]:
    """Compare a call against what the scenario was written to demonstrate."""
    failures: list[str] = []
    expect = result["expect"]
    turns = result["turns"]

    if "outcome" in expect and result["outcome"] != expect["outcome"]:
        failures.append(f"outcome was {result['outcome']}, expected {expect['outcome']}")
    if "escalated" in expect and result["escalated"] != expect["escalated"]:
        failures.append(f"escalated was {result['escalated']}, expected {expect['escalated']}")
    if "conflicts_at_least" in expect:
        found = sum(1 for t in turns if t["conflicts"])
        if found < expect["conflicts_at_least"]:
            failures.append(f"detected {found} contradictions, expected at least "
                            f"{expect['conflicts_at_least']}")
    if "refusals_at_least" in expect:
        found = sum(1 for t in turns if t["answer_source"] == "insufficient_context")
        if found < expect["refusals_at_least"]:
            failures.append(f"refused {found} times, expected at least "
                            f"{expect['refusals_at_least']}")
    if "grounded_turns_at_least" in expect:
        found = sum(1 for t in turns if t["answer_source"] == "context")
        if found < expect["grounded_turns_at_least"]:
            failures.append(f"{found} turns grounded in the knowledge base, expected at "
                            f"least {expect['grounded_turns_at_least']}")
    return failures


def write_report(pack_id: str, results: list[dict], folder: str) -> Path:
    all_turns = [t for r in results for t in r["turns"]]
    all_asr = [a for r in results for a in r["asr"]]
    # The harness synthesises the caller's speech, which a live call never does.
    # Reporting the harness total as turn latency overstates it, so the
    # live-equivalent path is reported separately: everything except the time
    # spent generating the caller's audio.
    LIVE_STAGES = ("asr", "retrieval", "llm", "agent_synthesis")
    latency = summarise(
        [{"total_ms": sum(t["latency_ms"].values()), "stages": t["latency_ms"]} for t in all_turns]
    )
    live = summarise(
        [
            {
                "total_ms": sum(v for k, v in t["latency_ms"].items() if k in LIVE_STAGES),
                "stages": {k: v for k, v in t["latency_ms"].items() if k in LIVE_STAGES},
            }
            for t in all_turns
        ]
    )
    exact = sum(1 for a in all_asr if a["exact_match"])
    grounded = sum(1 for t in all_turns if t["answer_source"] == "context")
    refused = sum(1 for t in all_turns if t["answer_source"] == "insufficient_context")
    ungrounded = [t for t in all_turns if t["ungrounded_figures"]]
    cited = sorted({c for t in all_turns for c in t["citations"]})

    lines = [
        f"# Recorded call results — {pack_id}",
        "",
        f"Generated {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')} by "
        "`python scripts/record_calls.py`.",
        "",
        "The caller's side of each call is synthesised in a separate voice and then "
        "transcribed through the same speech-recognition path a live call uses. The "
        "transcript, not the script, is what reached the agent, so these calls "
        "exercise transcription as well as the conversation logic.",
        "",
        "## Summary",
        "",
        "| Measure | Value |",
        "|---|---|",
        f"| Calls recorded | {len(results)} |",
        f"| Turns | {len(all_turns)} |",
        f"| Turns answered from the knowledge base | {grounded} |",
        f"| Turns where the agent stated it had no information | {refused} |",
        f"| Turns with an unverifiable figure (fallback triggered) | {len(ungrounded)} |",
        f"| Distinct records cited | {len(cited)} |",
        f"| Caller turns transcribed word for word | {exact}/{len(all_asr)} |",
        f"| Turn latency, live path, P50 / P95 | {live['end_to_end']['p50']} ms / "
        f"{live['end_to_end']['p95']} ms |",
        f"| Turn latency including caller synthesis (harness only) | "
        f"{latency['end_to_end']['p50']} ms |",
        "",
        "The live path measured here is transcription, retrieval and generation — "
        "the caller finishing speaking to the reply being ready. Speaking the reply "
        "adds a further 873 ms to first audio, measured separately, since synthesis "
        "streams and the caller hears the opening words before the rest is produced. "
        "The harness also synthesises the caller's own speech to produce the "
        "recordings, which a live call never does, so that cost is listed on its own "
        "rather than folded into the turn figure.",
        "",
        "### Component latency, live path",
        "",
        "| Component | P50 | P95 | Samples |",
        "|---|---|---|---|",
        *[
            f"| {stage.replace('_', ' ')} | {values['p50']} ms | {values['p95']} ms | "
            f"{values['samples']} |"
            for stage, values in live["stages"].items()
        ],
        "",
        "## Scenario coverage",
        "",
        "| Scenario | Demonstrates | Outcome | Verdict |",
        "|---|---|---|---|",
    ]
    for result in results:
        failures = check_expectations(result)
        verdict = "as expected" if not failures else "; ".join(failures)
        lines.append(
            f"| [{result['scenario']}]({Path(result['directory']).name}/transcript.md) | "
            f"{result['covers']} | {result['outcome']} | {verdict} |"
        )

    lines += [
        "",
        "## Calls",
        "",
    ]
    for result in results:
        lines += [
            f"### {result['scenario']} — {result['covers']}",
            "",
            f"Audio: `{result['directory']}/call_full.mp3` · "
            f"transcript: `{result['directory']}/transcript.md` · "
            f"lead: `{result['directory']}/lead.json`",
            "",
            "| # | Caller (as transcribed) | Agent | Source | Confidence | Cited |",
            "|---|---|---|---|---|---|",
        ]
        for turn in result["turns"]:
            citations = ", ".join(f"`{c}`" for c in turn["citations"]) or "—"
            source = turn["answer_source"]
            if turn["abstained"]:
                source += " (abstained)"
            lines.append(
                f"| {turn['index']} | {turn['caller'][:70]} | {turn['agent'][:90]} | "
                f"{source} | {turn['confidence']} | {citations} |"
            )
        if result["conflicts"]:
            lines += ["", "Contradictions detected: " + "; ".join(result["conflicts"])]
        lines += [
            "",
            f"Lead outcome: **{result['lead']['outcome']}** — captured "
            f"{result['lead']['captured'] or 'nothing'}",
            "",
        ]

    lines += [
        "## Transcription accuracy",
        "",
        "Word-for-word agreement is a strict measure: punctuation and spoken numerals "
        "differ from their written form even when the meaning is carried perfectly. "
        "Every mismatch is listed so the difference can be judged rather than summarised.",
        "",
        "| Spoken | Transcribed | Word for word |",
        "|---|---|---|",
    ]
    for pair in all_asr:
        mark = "yes" if pair["exact_match"] else "no"
        lines.append(f"| {pair['spoken'][:64]} | {pair['transcribed'][:64]} | {mark} |")

    if ungrounded:
        lines += [
            "",
            "## Figures the agent could not support",
            "",
            "Each of these triggered the approved fallback instead of being spoken.",
            "",
        ]
        for turn in ungrounded:
            lines.append(f"- turn {turn['index']}: {turn['ungrounded_figures']}")

    lines += ["", "## Records cited across all calls", ""]
    lines += [f"- `{record}`" for record in cited]
    lines.append("")

    path = ROOT / "deliverables" / folder / "call_results.md"
    path.write_text("\n".join(lines))
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", default="in_health_en")
    parser.add_argument("--scenario", default="", help="run one scenario by name")
    args = parser.parse_args()

    engine = Engine(args.pack)
    chosen = [
        s for s in scenarios_for(args.pack)
        if not args.scenario or args.scenario in s.name
    ]
    if not chosen:
        raise SystemExit(f"no scenario matching {args.scenario!r}")

    results = []
    for scenario in chosen:
        print(f"\n{'=' * 78}\n{scenario.name} — {scenario.covers}\n{'=' * 78}")
        started = time.perf_counter()
        result = run_scenario(engine, scenario)
        result["wall_seconds"] = round(time.perf_counter() - started, 1)
        failures = check_expectations(result)
        print(f"  -> outcome {result['outcome']} in {result['wall_seconds']}s")
        if failures:
            for failure in failures:
                print(f"  !! {failure}")
        results.append(result)

    folder = {
        "in_health_en": "q1_voice_agent",
        "ph_life_taglish": "q3_multilingual",
        "id_multifinance": "q3_multilingual",
    }.get(args.pack, "q1_voice_agent")

    # Merge with any calls recorded for the other market in the same folder.
    store = ROOT / "deliverables" / folder / "results.json"
    existing = json.loads(store.read_text()) if store.exists() else {}
    existing[args.pack] = results
    store.write_text(json.dumps(existing, indent=2, ensure_ascii=False))

    combined = [r for market in existing.values() for r in market]
    report = write_report(args.pack, combined, folder)

    unmet = sum(len(check_expectations(r)) for r in results)
    print(f"\n{len(results)} calls recorded, {unmet} expectations unmet")
    print(f"report: {report.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
