"""Stage timing for every request, in one place.

A trace records when each stage of a request finished. The voice agent uses it to
report response time per turn; the live pipeline uses the same traces to report
P50 and P95 per component. Measuring latency is not a reporting step bolted on at
the end — it is a property of every request, recorded as the request happens.

Durations are derived from a monotonic clock, so they are unaffected by wall-clock
adjustments. Wall-clock time is recorded separately, once per trace, for ordering
traces in a log a human reads.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "logs"


@dataclass
class Trace:
    """Timing for one request, from arrival to delivery."""

    kind: str
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    started_at: float = field(default_factory=time.perf_counter)
    started_wall: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat(timespec="milliseconds")
    )
    marks: list[tuple[str, float]] = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    def mark(self, stage: str) -> float:
        """Record that a stage has finished. Returns elapsed ms since arrival."""
        elapsed = (time.perf_counter() - self.started_at) * 1000
        self.marks.append((stage, elapsed))
        return elapsed

    def note(self, **fields) -> None:
        """Attach context to the trace: provider used, fallback taken, sizes."""
        self.meta.update(fields)

    @property
    def total_ms(self) -> float:
        return self.marks[-1][1] if self.marks else 0.0

    def stage_durations(self) -> dict[str, float]:
        """Time attributable to each stage, not cumulative time to that point.

        The difference matters. Cumulative marks answer "when did transcription
        finish"; these answer "how long did transcription take", which is what a
        component breakdown needs.
        """
        durations: dict[str, float] = {}
        previous = 0.0
        for stage, elapsed in self.marks:
            durations[stage] = round(elapsed - previous, 2)
            previous = elapsed
        return durations

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "kind": self.kind,
            "started_wall": self.started_wall,
            "total_ms": round(self.total_ms, 2),
            "stages": self.stage_durations(),
            "cumulative": {stage: round(ms, 2) for stage, ms in self.marks},
            **self.meta,
        }


class TraceLog:
    """Appends traces to a JSONL file and summarises them."""

    def __init__(self, name: str, directory: Path | None = None) -> None:
        self.path = (directory or LOG_DIR) / f"{name}.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, trace: Trace) -> None:
        with self.path.open("a") as handle:
            handle.write(json.dumps(trace.to_dict()) + "\n")

    def read(self) -> list[dict]:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text().splitlines():
            if line.strip():
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # a partially written final line is not fatal
        return out

    def clear(self) -> None:
        if self.path.exists():
            self.path.unlink()

    def summary(self) -> dict:
        return summarise(self.read())


def percentile(values: list[float], fraction: float) -> float:
    """Nearest-rank percentile.

    Interpolation is avoided deliberately: with the tens of samples a test call
    produces, an interpolated P95 reports a latency that was never observed.
    """
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(int(round(fraction * (len(ordered) - 1))), len(ordered) - 1)
    return ordered[index]


def summarise(traces: list[dict]) -> dict:
    """Aggregate end-to-end and per-stage latency across traces."""
    if not traces:
        return {"count": 0, "stages": {}}

    totals = [t["total_ms"] for t in traces if "total_ms" in t]

    by_stage: dict[str, list[float]] = {}
    for trace in traces:
        for stage, ms in (trace.get("stages") or {}).items():
            by_stage.setdefault(stage, []).append(ms)

    return {
        "count": len(traces),
        "end_to_end": {
            "p50": round(percentile(totals, 0.50), 1),
            "p95": round(percentile(totals, 0.95), 1),
            "min": round(min(totals), 1) if totals else 0.0,
            "max": round(max(totals), 1) if totals else 0.0,
        },
        "stages": {
            stage: {
                "p50": round(percentile(values, 0.50), 1),
                "p95": round(percentile(values, 0.95), 1),
                "samples": len(values),
            }
            for stage, values in sorted(by_stage.items())
        },
    }


def markdown_table(summary: dict, title: str = "Latency") -> str:
    """Render a summary as a markdown section for a report deliverable."""
    if not summary.get("count"):
        return f"## {title}\n\nNo traces recorded.\n"

    end = summary["end_to_end"]
    lines = [
        f"## {title}",
        "",
        f"{summary['count']} traces.",
        "",
        "| Measure | P50 | P95 | Min | Max |",
        "|---|---|---|---|---|",
        f"| End to end | {end['p50']} ms | {end['p95']} ms | {end['min']} ms | {end['max']} ms |",
        "",
        "| Component | P50 | P95 | Samples |",
        "|---|---|---|---|",
    ]
    for stage, values in summary["stages"].items():
        lines.append(
            f"| {stage.replace('_', ' ')} | {values['p50']} ms | "
            f"{values['p95']} ms | {values['samples']} |"
        )
    lines.append("")
    return "\n".join(lines)


def enabled() -> bool:
    return os.getenv("TELEMETRY", "true").lower() not in ("0", "false", "no")
