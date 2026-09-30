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

Placement correction: host timestamps around the action round trip do not say
when the native stall ran. CI run 36036355266 sent the stall 17.9 ms before the
due onset, but the Lua thread ran that onset first and only then stalled, so the
stall blocked nothing. Placement is now decided from native evidence. The
acknowledgement's native monotonic_ns is emitted by the Lua thread immediately
after the stall; the stall cannot have started before the request was submitted
or before any Lua-emitted MIDI message stamped before that completion. A
placement is decided when that native start precedes the target due time by the
margin while completion follows it, or when the target onset was provably held
until completion. Otherwise it is recorded as undecided and retried on a later
onset with the lead corrected by the measured native transit. Every attempt is
recorded; the oracle itself is unchanged.
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
_PLACEMENT_MARGIN_NS = 5_000_000
_PLACEMENT_ATTEMPTS = 3
_RETRY_STEPS = 2


def _port_one_onset(event):
    return event["port"] == 1 and event["bytes"][0] == 144 and event["bytes"][2] > 0


def _stall_start_ns(events, submitted_ns, completed_ns):
    # Channel-voice MIDI output is emitted by the serialised Lua event thread, so
    # the stall began no earlier than the last such message stamped before completion.
    emitted = [event["monotonic_ns"] for event in events
               if 0x80 <= event["bytes"][0] <= 0xEF and event["monotonic_ns"] < completed_ns]
    return max([submitted_ns] + emitted)


def _blocked(due_ns, emitted_ns, submitted_ns, completed_ns):
    # Due while the stall was requested or running, and held until it completed.
    # An onset due in that window but emitted before completion was emitted
    # before the stall started (the Lua thread is serialised), so it was not blocked.
    return submitted_ns <= due_ns < completed_ns <= emitted_ns


def _placement(start_ns, submitted_ns, completed_ns, due_ns, emitted_ns):
    covered = start_ns <= due_ns - _PLACEMENT_MARGIN_NS and completed_ns > due_ns
    blocked = emitted_ns is not None and _blocked(due_ns, emitted_ns, submitted_ns, completed_ns)
    return dict(decided=covered or blocked, covered=covered, target_blocked=blocked,
                start_margin_ns=due_ns - start_ns, completion_overlap_ns=completed_ns - due_ns)


def internal_clock_stall_phase(c):
    assert c.clock_mode == "real-time", "Lua-thread stalls use wall-clock time"
    build_composition(c)
    ui = c.ui
    # The expected 120 BPM value is a user-visible song-page parameter.
    ui.song_editor()
    ui.turn(1, 1)
    ui.set_value(_BPM - 90)
    ui.press_key(3)
    ui.turn(1, -1)
    ui.menu("channel_editor")

    marker = c.snapshot()["midi_count"]
    capture = MidiWindow(marker)
    ui.play()
    def port_one_onsets():
        return [event for event in capture.events if _port_one_onset(event)]
    c.wait(lambda state: capture.extend(state) and len(port_one_onsets()) >= _WARM_ONSETS, timeout=3)
    warm_onsets = port_one_onsets()
    warm_intervals = [later["monotonic_ns"] - earlier["monotonic_ns"]
                      for earlier, later in zip(warm_onsets, warm_onsets[1:])]
    assert len(warm_intervals) >= _WARM_ONSETS - 1, warm_intervals
    assert all(abs(interval - _STEP_NS) <= _PHASE_BOUND_NS for interval in warm_intervals), warm_intervals
    # Target dues are on the same phase lattice the oracle uses below.
    origin = warm_onsets[0]["monotonic_ns"]
    target_index = len(warm_onsets)
    lead = _STALL_LEAD_NS
    attempts = []
    while True:
        target_due = origin + target_index * _STEP_NS
        c.wait(lambda state: capture.extend(state) or True, timeout=1)
        time.sleep(max(0, (target_due - lead - time.monotonic_ns()) / 1e9))
        before = time.monotonic_ns()
        acknowledgement = c.action(type="runtime_stall", milliseconds=_STALL_MS)
        after = time.monotonic_ns()
        completed = acknowledgement["native"]["monotonic_ns"]
        # Every Lua emission before completion precedes the acknowledgement on the
        # native socket. Wait for the target onset and the first onset emitted after
        # completion (the only one the stall can have held) before judging placement.
        c.wait(lambda state: capture.extend(state) and len(port_one_onsets()) > target_index and
               port_one_onsets()[-1]["monotonic_ns"] >= completed, timeout=3)
        start = _stall_start_ns(capture.events, before, completed)
        emitted = port_one_onsets()[target_index]["monotonic_ns"]
        placement = _placement(start, before, completed, target_due, emitted)
        placement["blocked_onset_indices"] = [
            index for index, event in enumerate(port_one_onsets())
            if _blocked(origin + index * _STEP_NS, event["monotonic_ns"], before, completed)]
        placement["decided"] = placement["decided"] or bool(placement["blocked_onset_indices"])
        attempt = dict(attempt=len(attempts) + 1, target_onset_index=target_index,
                       target_due_ns=target_due, lead_ns=lead, before_ns=before, after_ns=after,
                       stall_elapsed_ns=after - before, native_ack=acknowledgement["native"],
                       native_completed_ns=completed, target_emitted_ns=emitted,
                       in_run_start_ns=start, measured_transit_ns=start - before, in_run=placement)
        attempts.append(attempt)
        if attempt["in_run"]["decided"] or len(attempts) == _PLACEMENT_ATTEMPTS:
            break
        # Undecided: let the stall settle for at least two steps, then correct the
        # lead by the measured native transit so the stall starts before the due onset.
        lead = max(0, start - before) + _STALL_LEAD_NS
        target_index += _RETRY_STEPS
        while origin + target_index * _STEP_NS - lead < time.monotonic_ns() + _PHASE_BOUND_NS:
            target_index += 1
    c.elapse(6)
    ui.stop()
    c.wait(lambda state: not state["midi_capture"]["outstanding"], timeout=5)
    c.finish()

    events = [json.loads(line) for line in (c.out / "native/native-events.jsonl").read_text().splitlines()]
    outputs = [event for event in events
               if event.get("kind") == 3 and event.get("index", 0) > marker]
    onsets = [event for event in outputs if _port_one_onset(event)]
    assert len(onsets) >= 48, len(onsets)
    origin = onsets[0]["monotonic_ns"]
    dues = [origin + index * _STEP_NS for index in range(len(onsets))]
    phase_errors = [event["monotonic_ns"] - due for event, due in zip(onsets, dues)]
    # Authoritative placement from the native log: the backend's own submission
    # time replaces the host's pre-request timestamp as the start lower bound.
    timings = {event["sequence"]: event for event in events if event.get("kind") == "input_timing"}
    blocked = {}  # onset index -> response after the completion of the stall that held it
    for attempt in attempts:
        timing = timings[attempt["native_ack"]["sequence"]]
        assert timing["native_ack_ns"] == attempt["native_completed_ns"], (timing, attempt["native_ack"])
        submitted, completed = timing["submitted_ns"], attempt["native_completed_ns"]
        start = _stall_start_ns(outputs, submitted, completed)
        index = attempt["target_onset_index"]
        emitted = onsets[index]["monotonic_ns"] if index < len(onsets) else None
        attempt.update(native_submitted_ns=submitted, native_start_ns=start,
                       blocked_onset_indices=[i for i, (event, due) in enumerate(zip(onsets, dues))
                                              if _blocked(due, event["monotonic_ns"], submitted, completed)],
                       **_placement(start, submitted, completed, dues[index], emitted))
        # An attempt that held any onset past its due time is decided, whatever its margin.
        attempt["decided"] = attempt["decided"] or bool(attempt["blocked_onset_indices"])
        for i in attempt["blocked_onset_indices"]:
            blocked[i] = onsets[i]["monotonic_ns"] - completed
    decided = [attempt for attempt in attempts if attempt["decided"]]
    chosen = decided[0] if decided else attempts[-1]
    placement_ok = len(decided) == 1 and decided[0] is attempts[-1] and decided[0]["in_run"]["decided"]
    # Blocked onsets get the completion-response oracle; every other onset,
    # including those around undecided attempts, keeps the original phase oracle.
    blocked_responses = [blocked[i] for i in chosen["blocked_onset_indices"]]
    blocked_ok = bool(blocked_responses) and set(blocked) == set(chosen["blocked_onset_indices"]) and \
        all(0 <= response <= _PHASE_BOUND_NS for response in blocked_responses)
    blocked_index = chosen["blocked_onset_indices"][0] if chosen["blocked_onset_indices"] else chosen["target_onset_index"]
    blocked_response_ns = blocked_responses[0] if blocked_responses else None
    maximum = max(abs(error) for index, error in enumerate(phase_errors) if index not in blocked)
    elapsed = chosen["stall_elapsed_ns"]
    target_due = chosen["target_due_ns"]
    before, after = chosen["before_ns"], chosen["after_ns"]
    c.results.append(dict(kind="internal-clock-runtime-stall-phase",
                          characterization="emulator-only bounded Lua event-thread fault",
                          stall_ms=_STALL_MS, stall_elapsed_ns=elapsed,
                          expected_due_ns=target_due,
                          preceding_onset_ns=onsets[chosen["target_onset_index"] - 1]["monotonic_ns"],
                          warm_intervals_ns=warm_intervals, stall_lead_ns=target_due - before,
                          stall_overlap_ns=after - target_due, stall_before_ns=before, stall_after_ns=after,
                          blocked_onset_index=blocked_index,
                          blocked_onset_phase_error_ns=phase_errors[blocked_index],
                          blocked_response_ns=blocked_response_ns,
                          blocked_responses_ns=[dict(onset_index=i, response_ns=blocked[i]) for i in sorted(blocked)],
                          maximum_phase_error_ns=maximum,
                          phase_bound_ns=_PHASE_BOUND_NS,
                          native_ack=chosen["native_ack"],
                          placement_margin_ns=_PLACEMENT_MARGIN_NS,
                          placement_decided=placement_ok,
                          placement_attempts=attempts,
                          passed=placement_ok and blocked_ok and maximum <= _PHASE_BOUND_NS and
                          _STALL_MS * 1_000_000 <= elapsed <= 100_000_000))
    (c.out / "results.json").write_text(json.dumps(c.results, indent=2) + "\n")
    assert placement_ok, ("stall placement undecided or inconsistent", attempts)
    assert blocked_ok, ("blocked onset response", blocked, chosen["blocked_onset_indices"])
    assert maximum <= _PHASE_BOUND_NS, ("Lua-stall internal phase", maximum, phase_errors)
    assert _STALL_MS * 1_000_000 <= elapsed <= 100_000_000, elapsed
