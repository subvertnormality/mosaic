"""Characterise internal-clock phase through a bounded Lua-thread stall.

This is intentionally distinct from M-SYNC-023: that test covers external
MIDI Stop pre-emption after a one-second backlog. Here the normal internal
transport drives the README typical-workflow song. The emulator-only fault
blocks the Lua event thread for 42 ms while native workers continue. The
port-one onset stream must recover its pre-stall phase after the blocked onset; a failure is a
reproducible internal-clock phase-loss witness, not a hardware-equivalence
claim.

Oracle correction: the forced-overlap variant introduced in 80bca88 retained
an impossible deadline for the blocked note. That note now has a 10 ms response
budget from native stall completion; every other note keeps the original phase.
Evidence: mosaic-behaviour-runs/c23aba34875d4c318c6ae77117d52659 (old failure),
25497ea108aa47deb4b9a1a1439f09f4 (corrected oracle: 3.436 ms blocked response,
1.828 ms maximum unaffected phase). This does not qualify PERF-008 recovery.
"""
import json
import time

from composition_workflow import build_composition
from midi_window import MidiWindow

_BPM = 120
_STEP_NS = 125_000_000
_STALL_MS = 42
_PHASE_BOUND_NS = 10_000_000
_STALL_LEAD_NS = 18_000_000
_WARM_ONSETS = 4


def internal_clock_stall_phase(c):
    assert c.clock_mode == "real-time", "Lua-thread stalls use wall-clock time"
    build_composition(c)
    # The expected 120 BPM value is a user-visible song-page parameter.
    c.tap(6, 8)
    c.enc(1, 1)
    c.enc(3, _BPM - 90)
    c.key(3)
    c.enc(1, -1)
    c.tap(3, 8)

    marker = c.snapshot()["midi_count"]
    capture = MidiWindow(marker)
    c.tap(1, 8)
    def port_one_onsets():
        return [event for event in capture.events
                if event["port"] == 1 and event["bytes"][0] == 144 and event["bytes"][2] > 0]
    c.wait(lambda state: capture.extend(state) and len(port_one_onsets()) >= _WARM_ONSETS, timeout=3)
    warm_onsets = port_one_onsets()
    warm_intervals = [later["monotonic_ns"] - earlier["monotonic_ns"]
                      for earlier, later in zip(warm_onsets, warm_onsets[1:])]
    assert len(warm_intervals) >= _WARM_ONSETS - 1, warm_intervals
    assert all(abs(interval - _STEP_NS) <= _PHASE_BOUND_NS for interval in warm_intervals), warm_intervals
    target_due = warm_onsets[-1]["monotonic_ns"] + _STEP_NS
    time.sleep(max(0, (target_due - _STALL_LEAD_NS - time.monotonic_ns()) / 1e9))
    before = time.monotonic_ns()
    acknowledgement = c.action(type="runtime_stall", milliseconds=_STALL_MS)
    after = time.monotonic_ns()
    assert before < target_due < after, (before, target_due, after)
    c.elapse(6)
    c.tap(1, 8)
    c.wait(lambda state: not state["midi_capture"]["outstanding"], timeout=5)
    c.finish()

    events = [json.loads(line) for line in (c.out / "native/native-events.jsonl").read_text().splitlines()]
    onsets = [event for event in events
              if event.get("kind") == 3 and event.get("index", 0) > marker and
              event.get("port") == 1 and event["bytes"][0] == 144 and event["bytes"][2] > 0]
    assert len(onsets) >= 48, len(onsets)
    origin = onsets[0]["monotonic_ns"]
    phase_errors = [event["monotonic_ns"] - (origin + index * _STEP_NS)
                    for index, event in enumerate(onsets)]
    # Exactly the next expected onset is intentionally blocked past its deadline.
    # Keep the original phase oracle for every other onset; do not rebase recovery.
    blocked_index = len(warm_onsets)
    blocked_onset_ns = onsets[blocked_index]["monotonic_ns"]
    stall_completed_ns = acknowledgement["native"]["monotonic_ns"]
    blocked_response_ns = blocked_onset_ns - stall_completed_ns
    maximum = max(abs(error) for index, error in enumerate(phase_errors)
                  if index != blocked_index)
    elapsed = after - before
    c.results.append(dict(kind="internal-clock-runtime-stall-phase",
                          characterization="emulator-only bounded Lua event-thread fault",
                          stall_ms=_STALL_MS, stall_elapsed_ns=elapsed,
                          expected_due_ns=target_due, preceding_onset_ns=warm_onsets[-1]["monotonic_ns"],
                          warm_intervals_ns=warm_intervals, stall_lead_ns=target_due - before,
                          stall_overlap_ns=after - target_due, stall_before_ns=before, stall_after_ns=after,
                          blocked_onset_index=blocked_index,
                          blocked_onset_phase_error_ns=phase_errors[blocked_index],
                          blocked_response_ns=blocked_response_ns,
                          maximum_phase_error_ns=maximum,
                          phase_bound_ns=_PHASE_BOUND_NS,
                          native_ack=acknowledgement["native"],
                          passed=maximum <= _PHASE_BOUND_NS and 0 <= blocked_response_ns <= _PHASE_BOUND_NS and _STALL_MS * 1_000_000 <= elapsed <= 100_000_000))
    (c.out / "results.json").write_text(json.dumps(c.results, indent=2) + "\n")
    assert 0 <= blocked_response_ns <= _PHASE_BOUND_NS, ("blocked onset response", blocked_response_ns)
    assert maximum <= _PHASE_BOUND_NS, ("Lua-stall internal phase", maximum, phase_errors)
    assert _STALL_MS * 1_000_000 <= elapsed <= 100_000_000, elapsed
