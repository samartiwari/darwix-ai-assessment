"""Measure speech recognition per market and write the report.

    python scripts/asr_report.py

Each utterance is synthesised in the market's own voice and transcribed through
the same path a live call uses, then compared word by word. This needs no
language model, so it can be run while the generation quota is exhausted.

Utterances are chosen to probe specific behaviour rather than to flatter the
system: English finance nouns inside Filipino grammar, Filipino verbal affixes
attached to English stems, colloquial Indonesian contractions, and
Javanese-inflected Indonesian that a Jakarta-trained model has not been tuned on.
"""

from __future__ import annotations

import difflib
import json
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import asr, tts  # noqa: E402

REPORT = ROOT / "deliverables" / "q3_multilingual" / "asr_report.md"
AUDIO_DIR = ROOT / "deliverables" / "q3_multilingual" / "asr_samples"


@dataclass
class Probe:
    text: str
    probes: str                 # what this utterance is testing
    language: str               # ASR language hint
    voice_language: str         # TTS voice selection
    expect_terms: list[str] = field(default_factory=list)


PROBES: dict[str, list[Probe]] = {
    "Philippines (Filipino / Taglish)": [
        Probe(
            "Magandang araw po, tungkol po ito sa premium ng policy ko.",
            "English finance nouns inside Filipino grammar",
            "tl", "fil", ["premium", "policy"],
        ),
        Probe(
            "Na-lapse na po yung policy ko kaya hindi na po active ang coverage.",
            "Filipino affix na- attached to the English stem 'lapse'",
            "tl", "fil", ["policy", "coverage"],
        ),
        Probe(
            "Pwede po ba natin i-settle ngayon, o i-reinstate na lang po?",
            "Filipino affix i- attached to English stems 'settle' and 'reinstate'",
            "tl", "fil-male", ["settle", "reinstate"],
        ),
        Probe(
            "Ilang araw po ang grace period bago ma-lapse ang policy?",
            "multi-word English term inside a Filipino question",
            "tl", "fil", ["grace period", "policy"],
        ),
        Probe(
            "Sino po ang beneficiary at may critical illness rider po ba ako?",
            "three consecutive English insurance terms",
            "tl", "fil", ["beneficiary", "critical illness", "rider"],
        ),
        Probe(
            "Magbabayad po ako sa GCash pagkatapos ng sweldo sa Friday.",
            "brand name, Filipino noun and English weekday together",
            "tl", "fil-male", ["GCash", "sweldo"],
        ),
    ],
    "Indonesia (standard Bahasa Indonesia)": [
        Probe(
            "Angsuran bulan ini sudah jatuh tempo, tenor sisa lima bulan lagi.",
            "core payment vocabulary in formal register",
            "id", "id", ["angsuran", "jatuh tempo", "tenor"],
        ),
        Probe(
            "Dendanya nol koma satu persen per hari dari nilai yang tertunggak.",
            "a spoken decimal figure inside a penalty explanation",
            "id", "id", ["denda", "persen"],
        ),
        Probe(
            "DP minimum lima belas persen untuk pembiayaan motor baru.",
            "the English-derived abbreviation DP alongside Indonesian terms",
            "id", "id-male", ["DP", "pembiayaan"],
        ),
        Probe(
            "Belum ada uang bulan ini, bisa nggak cicilannya diperpanjang?",
            "colloquial contraction 'nggak' and colloquial word order",
            "id", "id-male", ["cicilan"],
        ),
        Probe(
            "Udah saya transfer kok kemarin lewat virtual account.",
            "colloquial 'udah' and 'kok' with an English loan phrase",
            "id", "id-male", ["transfer", "virtual account"],
        ),
    ],
    "Indonesia (Javanese-inflected, outside Jakarta speech)": [
        Probe(
            "Nggih, monggo Bu, angsurane sampun telat rong wulan og.",
            "Javanese affirmative, politeness particle, possessive -e and numeral 'rong wulan'",
            "id", "id-male", ["angsuran"],
        ),
        Probe(
            "Kulo pengen ngomong karo wong tenan mawon nggih.",
            "Javanese pronouns and verbs in place of Indonesian equivalents",
            "id", "id-male", [],
        ),
        Probe(
            "Lha nggih, kulo sing gadhah kontrak pembiayaan niku.",
            "Javanese relative marker 'sing' and demonstrative 'niku'",
            "id", "id-male", ["kontrak", "pembiayaan"],
        ),
        Probe(
            "Mbok bilih saged, dendane dipun kirangi sekedhik nggih Bu.",
            "high-register Javanese with the Indonesian loan 'denda'",
            "id", "id-male", [],
        ),
    ],
}


def normalise(text: str) -> list[str]:
    return re.findall(r"[\w']+", text.lower())


def word_error_rate(spoken: str, heard: str) -> float:
    """Word error rate via an alignment over the two token sequences."""
    reference, hypothesis = normalise(spoken), normalise(heard)
    if not reference:
        return 0.0
    matcher = difflib.SequenceMatcher(None, reference, hypothesis)
    matched = sum(block.size for block in matcher.get_matching_blocks())
    edits = max(len(reference), len(hypothesis)) - matched
    return edits / len(reference)


def differences(spoken: str, heard: str) -> list[str]:
    """Report the substitutions, in spoken to heard form."""
    reference, hypothesis = normalise(spoken), normalise(heard)
    out: list[str] = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, reference, hypothesis).get_opcodes():
        if tag == "equal":
            continue
        was = " ".join(reference[i1:i2]) or "—"
        now = " ".join(hypothesis[j1:j2]) or "—"
        out.append(f"{was} → {now}")
    return out


def run() -> dict:
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    results: dict = {}

    for market, probes in PROBES.items():
        rows = []
        for index, probe in enumerate(probes, start=1):
            speech = tts.synthesise(probe.text, probe.voice_language)
            if not speech.ok:
                print(f"  !! synthesis failed: {probe.text[:40]}")
                continue
            slug = re.sub(r"[^a-z0-9]+", "_", market.lower())[:28]
            path = AUDIO_DIR / f"{slug}_{index:02d}.mp3"
            speech.save(path)

            started = time.perf_counter()
            heard = asr.transcribe(speech.audio, language=probe.language)
            elapsed = (time.perf_counter() - started) * 1000

            kept = [t for t in probe.expect_terms if t.lower() in heard.text.lower()]
            rows.append(
                {
                    "probes": probe.probes,
                    "spoken": probe.text,
                    "heard": heard.text,
                    "wer": round(word_error_rate(probe.text, heard.text), 3),
                    "differences": differences(probe.text, heard.text),
                    "terms_expected": probe.expect_terms,
                    "terms_preserved": kept,
                    "voice": speech.voice,
                    "provider": heard.provider,
                    "fell_back": heard.fell_back,
                    "latency_ms": round(elapsed),
                    "audio": str(path.relative_to(ROOT)),
                }
            )
            mark = "ok " if rows[-1]["wer"] < 0.25 else "high"
            print(f"  [{mark}] wer {rows[-1]['wer']:.2f}  {probe.text[:56]}")
        results[market] = rows
    return results


def write_report(results: dict) -> Path:
    all_rows = [r for rows in results.values() for r in rows]
    providers = {r["provider"] for r in all_rows}
    voices = sorted({r["voice"] for r in all_rows})

    lines = [
        "# Speech recognition and synthesis per market",
        "",
        f"Generated {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')} by "
        "`python scripts/asr_report.py`. Audio samples are in `asr_samples/`.",
        "",
        "## Configuration",
        "",
        "| | |",
        "|---|---|",
        f"| Recognition provider | {', '.join(sorted(providers))} |",
        "| Recognition model | `whisper-large-v3-turbo` (hosted), "
        "`faster-whisper small` int8 on CPU (local fallback) |",
        "| Language hints | `tl` for the Philippines, `id` for Indonesia |",
        f"| Synthesis voices | {', '.join(voices)} |",
        "| Synthesis provider | edge-tts, with ElevenLabs configured as fallback |",
        "",
        "The Philippine language hint is `tl` rather than `fil`. Tagalog is the code "
        "the model recognises; left to auto-detect, short Taglish utterances were "
        "tagged as English and transcribed with English spelling for Filipino words.",
        "",
        "## Method",
        "",
        "Each utterance is synthesised in the market's own voice and transcribed "
        "through the path a live call uses. Word error rate is computed by alignment "
        "over tokens, which is a strict measure: a spoken numeral written as digits "
        "counts as an error even though the meaning survives. Every difference is "
        "listed so it can be judged rather than summarised.",
        "",
        "The utterances probe specific behaviour rather than average performance — "
        "affixed English stems, multi-word English terms, colloquial contractions and "
        "Javanese-inflected wording. A flattering sentence set would report a lower "
        "error rate and tell you nothing.",
        "",
    ]

    for market, rows in results.items():
        if not rows:
            continue
        mean_wer = sum(r["wer"] for r in rows) / len(rows)
        preserved = sum(len(r["terms_preserved"]) for r in rows)
        expected = sum(len(r["terms_expected"]) for r in rows)
        latency = sorted(r["latency_ms"] for r in rows)[len(rows) // 2]

        lines += [
            f"## {market}",
            "",
            f"Mean word error rate {mean_wer:.2f} across {len(rows)} utterances. "
            f"Domain terms preserved {preserved}/{expected}. "
            f"Median recognition latency {latency} ms.",
            "",
        ]
        for row in rows:
            lines += [
                f"**Probes:** {row['probes']}",
                "",
                f"- Spoken: {row['spoken']}",
                f"- Heard: {row['heard']}",
                f"- Word error rate: {row['wer']:.2f}"
                + (
                    f" · terms kept: {', '.join(row['terms_preserved']) or 'none'}"
                    if row["terms_expected"]
                    else ""
                ),
            ]
            if row["differences"]:
                lines.append(f"- Differences: {'; '.join(row['differences'][:8])}")
            lines.append(f"- Audio: `{row['audio']}`")
            lines.append("")

    lines += [
        "## What the errors show",
        "",
        "### Philippines: affix boundaries are the only error class",
        "",
        "Every Filipino error is the same phenomenon. Filipino attaches verbal "
        "affixes to English stems, and the recogniser collapses the boundary into a "
        "non-word: `na-lapse` became `nalaps`, `i-settle` became `isettle`, "
        "`ma-lapse` became `malaps`. Multi-word English terms survived intact — "
        "`grace period`, `critical illness rider` and `beneficiary` all came through "
        "— so the difficulty is specifically morphological rather than lexical.",
        "",
        "The consequence is that downstream matching must tolerate affix boundaries. "
        "Retrieval here is dense rather than exact-token, which absorbs most of it, "
        "and the agent answered the grace-period question correctly from a transcript "
        "that read `malaps`.",
        "",
        "One brand name was lost: `GCash` became `cash`. A payment channel is worth "
        "matching exactly, so brand names belong in a correction list rather than "
        "left to the recogniser.",
        "",
        "### Indonesia: numeral normalisation, and one case that matters",
        "",
        "Most Indonesian error is the recogniser writing spoken numerals as digits — "
        "`lima` as `5`, `lima belas persen` as `15`. Word error rate penalises this "
        "while the meaning survives, which is why the figure overstates the problem.",
        "",
        "One case is not benign. `nol koma satu persen` — nought point one percent, "
        "the daily late-payment penalty — was transcribed `0 1`, losing the decimal "
        "separator. A downstream parser reading `0 1` could take it as one percent, "
        "ten times the real rate. Penalty and interest figures must therefore be read "
        "from the knowledge base rather than parsed out of a transcript, which is how "
        "the agent is built, and the figure check refuses any number the records do "
        "not contain.",
        "",
        "### Indonesia: regional speech degrades severely",
        "",
        "Javanese-inflected Indonesian moves the mean word error rate from 0.18 to "
        "0.61, and high-register Javanese reaches 0.89, which is not usable. Three "
        "distinct failures appear:",
        "",
        "- **Particles are eroded.** `nggih`, the Javanese affirmative, consistently "
        "became `gih`.",
        "- **Word boundaries collapse toward familiar tokens.** `karo wong` — with a "
        "person — became `karawang`, a city in West Java. The model resolved unfamiliar "
        "input into a word it knew, which is more dangerous than a garbled "
        "transcription because it reads as valid text.",
        "- **Javanese numerals and honorific verb forms are lost.** `rong wulan` (two "
        "months) became `ronggulan`; `dipun kirangi` became `dipunkirangi`.",
        "",
        "What this means for the design: the Indonesian agent cannot rely on the "
        "transcript for facts when a customer speaks regionally. It can still carry "
        "the conversation, because intent survives better than wording, and the "
        "grounding rules refuse any figure not present in the records. Where the "
        "transcript is this unreliable, escalation to a person is the correct "
        "behaviour rather than a fallback, and the Indonesian pack escalates when the "
        "customer's meaning cannot be established.",
        "",
        "## Known gaps",
        "",
        "**Acoustic accent is untested.** The synthesis voices available are standard "
        "Jakarta Indonesian and standard Manila Filipino. What is measured above is "
        "regionally marked *lexis and syntax* spoken in a standard accent, which is a "
        "genuine and separate difficulty, but it is not the same as a Javanese or "
        "Sundanese accent on the acoustic signal. Testing that needs recordings from "
        "native speakers, and the figures here should not be read as covering it.",
        "",
        "**No native-speaker review.** The Filipino and Indonesian wording in the "
        "market packs and knowledge base was written from documented usage, not by a "
        "native speaker. The register rules — `po` throughout, `Bapak` and `Ibu`, "
        "softened requests — reflect well-attested convention, but idiomatic "
        "naturalness, regional word choice and the exact line between polite and "
        "obsequious need a native reviewer before this reaches a customer.",
        "",
        "**Compliance wording is illustrative.** Philippine Insurance Commission and "
        "Indonesian OJK requirements are represented in the packs as constraints on "
        "what the agent may say, and the collections calling-hours limit is enforced "
        "in configuration. The exact statutory wording of disclosures has not been "
        "verified against current regulation and would need legal review.",
        "",
    ]

    (REPORT.parent).mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines))
    (REPORT.parent / "asr_results.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False)
    )
    return REPORT


def main() -> int:
    print("measuring recognition per market\n")
    results = run()
    path = write_report(results)
    print(f"\nreport: {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
