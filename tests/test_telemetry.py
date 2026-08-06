"""Tests for stage timing.

Latency reporting is graded, so the arithmetic behind it is pinned rather than
trusted.
"""

import time

from core.telemetry import Trace, TraceLog, markdown_table, percentile, summarise


class TestTrace:
    def test_stage_durations_are_per_stage_not_cumulative(self):
        """The distinction the component breakdown depends on."""
        trace = Trace(kind="test")
        trace.marks = [("asr", 400.0), ("retrieval", 430.0), ("llm", 800.0)]
        durations = trace.stage_durations()
        assert durations["asr"] == 400.0
        assert durations["retrieval"] == 30.0
        assert durations["llm"] == 370.0
        assert trace.total_ms == 800.0

    def test_marks_increase_monotonically(self):
        trace = Trace(kind="test")
        first = trace.mark("one")
        time.sleep(0.01)
        second = trace.mark("two")
        assert 0 <= first <= second

    def test_notes_are_carried_into_the_record(self):
        trace = Trace(kind="test")
        trace.mark("asr")
        trace.note(asr_provider="local", asr_fallback_reason="rate limited")
        record = trace.to_dict()
        assert record["asr_provider"] == "local"
        assert record["asr_fallback_reason"] == "rate limited"
        assert record["kind"] == "test"
        assert record["trace_id"]

    def test_a_trace_with_no_marks_has_zero_total(self):
        assert Trace(kind="test").total_ms == 0.0


class TestPercentile:
    def test_returns_an_observed_value_not_an_interpolation(self):
        """With few samples an interpolated P95 reports a latency never seen."""
        values = [100.0, 200.0, 300.0, 400.0]
        assert percentile(values, 0.95) in values
        assert percentile(values, 0.5) in values

    def test_handles_a_single_sample(self):
        assert percentile([42.0], 0.95) == 42.0

    def test_handles_no_samples(self):
        assert percentile([], 0.5) == 0.0

    def test_orders_unsorted_input(self):
        assert percentile([300.0, 100.0, 200.0], 0.0) == 100.0


class TestSummary:
    def _traces(self):
        return [
            {"total_ms": 1000.0, "stages": {"asr": 400.0, "llm": 600.0}},
            {"total_ms": 1200.0, "stages": {"asr": 500.0, "llm": 700.0}},
            {"total_ms": 2000.0, "stages": {"asr": 450.0, "llm": 1550.0}},
        ]

    def test_reports_end_to_end_and_per_component(self):
        summary = summarise(self._traces())
        assert summary["count"] == 3
        assert summary["end_to_end"]["p50"] == 1200.0
        assert summary["end_to_end"]["max"] == 2000.0
        assert summary["stages"]["asr"]["samples"] == 3
        assert summary["stages"]["llm"]["p50"] == 700.0

    def test_empty_input_does_not_raise(self):
        assert summarise([])["count"] == 0

    def test_markdown_names_every_component(self):
        table = markdown_table(summarise(self._traces()), "Turn latency")
        assert "Turn latency" in table
        assert "asr" in table
        assert "llm" in table
        assert "P95" in table

    def test_markdown_states_when_there_is_nothing_to_report(self):
        assert "No traces recorded" in markdown_table(summarise([]))


class TestTraceLog:
    def test_round_trips_traces_through_the_log(self, tmp_path):
        log = TraceLog("unit", directory=tmp_path)
        trace = Trace(kind="turn")
        trace.mark("asr")
        trace.mark("llm")
        log.write(trace)
        log.write(trace)
        assert len(log.read()) == 2
        assert log.summary()["count"] == 2

    def test_a_truncated_final_line_is_skipped_not_fatal(self, tmp_path):
        log = TraceLog("unit", directory=tmp_path)
        log.write(Trace(kind="turn"))
        with log.path.open("a") as handle:
            handle.write('{"partial": ')
        assert len(log.read()) == 1

    def test_reading_a_missing_log_returns_nothing(self, tmp_path):
        assert TraceLog("absent", directory=tmp_path).read() == []
