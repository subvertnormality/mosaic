"""Course clips: the before/after MIDI check that makes a routed audio take honest.

Characterisation outside README.md (tooling for the manual's course audio): the audio take sounds the
course stage on voices, so MIDI cannot witness it. The same session therefore proves the stage's tiled
course contract on MIDI BEFORE the take and again AFTER it, with only routing inputs in between. The
contract is the course's independent CONTRACTS entry (README.md course walk-through); the packets are
the ones a MIDI listener would receive. Controlled time: logical_ns, 2 ns tolerance.
"""
import copy
import os
import sys
import unittest
from pathlib import Path
import yaml

REPO = Path(os.environ.get("MOSAIC_MANUAL_ROOT", Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(1, str(REPO / "tests/behaviour"))
import manual_audio
from ui_map import control_cell

STEP_NS = 1e9 / 6


def example(ident="course-sequence-composition-both"):
    data = yaml.safe_load((REPO / "manual/audio-scenes.yaml").read_text())
    return next(v for v in data["examples"] if v["id"] == ident)


class FakeUi:
    """The public inputs a session uses, each logged as the grid/key/enc actions it would send."""
    def __init__(self, driver):
        self.driver = driver

    def tap_cell(self, x, y):
        self.driver.action(type="grid", x=x, y=y, state=1)
        self.driver.action(type="grid", x=x, y=y, state=0)
        self.driver.elapse(.06)

    def play(self):
        self.tap_cell(*control_cell("play_stop"))
        d = self.driver
        d.playing = not d.playing
        if d.playing:
            d.origin = d.logical_ns
            d.base = d.total
        else:
            d.total = d.base + len(d.window())

    stop = play

    def channel_editor(self):
        self.tap_cell(*control_cell("channel_editor"))

    def select_channel(self, channel):
        self.tap_cell(*control_cell("channel", channel))

    def channel_page(self, page, channel=1, **kw):
        self.press_key(3)

    def press_key(self, n):
        self.driver.action(type="key", n=n, state=1)
        self.driver.action(type="key", n=n, state=0)

    def expect_selected_field(self, *a, **k):
        pass

    def pick_device(self, name):
        self.driver.device = name
        self.driver.action(type="key", n=3, state=1)
        self.driver.action(type="key", n=3, state=0)

    def tap_control(self, name, index=None):
        self.tap_cell(9, 9)


class FakeDriver:
    """A norns that plays the tiled contract on MIDI while its channels are routed to MIDI."""
    clock_mode = "controlled-experimental"

    def __init__(self, ex, after_note_shift=0, tamper_stage=None):
        self.ex = ex
        self.recipe = []
        self.results = []
        self.logical_ns = 0
        self.playing = False
        self.origin = 0
        self.routed_midi = True
        self.device = None
        self.ui = FakeUi(self)
        self.total = 0
        self.after_note_shift = after_note_shift
        self.tamper_stage = tamper_stage
        self.rows = ex["midi_contract"]["notes"]
        self.stops = []

    def action(self, **value):
        self.recipe.append(value)

    def elapse(self, seconds):
        ns = round(seconds * 1e9)
        self.action(type="advance", nanoseconds=ns)
        self.logical_ns += ns

    def enc(self, n, steps):
        for _ in range(abs(steps)):
            self.action(type="enc", n=n, delta=2 if steps > 0 else -2)
        self.elapse(.15)

    def window(self):
        return self._midi() if self.routed_midi else []

    def _midi(self):
        if self.tamper_stage is not None and self.tamper_stage == self.proof_ordinal():
            rows = [dict(r, velocity=r["velocity"] - 1) if i == 0 else r for i, r in enumerate(self.rows)]
        else:
            rows = self.rows
        events = []
        for cycle in range(4):
            for r in rows:
                on = self.origin + int((r["step"] + 64 * cycle) * STEP_NS)
                events.append((on, [r["status"], r["note"], r["velocity"]], r["port"]))
                events.append((on + int(r["length"] * STEP_NS), [r["status"] - 16, r["note"], r["velocity"]], r["port"]))
        events.sort(key=lambda e: e[0])
        return [e for e in events if e[0] <= self.logical_ns]

    def proof_ordinal(self):
        return (sum(1 for a in self.recipe if a.get("x") == 1 and a.get("y") == 8 and a.get("state") == 1) + 1) // 2

    def snapshot(self):
        packets = []
        if self.playing and self.routed_midi:
            for i, (t, data, port) in enumerate(self._midi()):
                packets.append(dict(index=i + 1 + self.base, port=port, bytes=data, logical_ns=t, monotonic_ns=t))
        return dict(midi=packets, midi_count=self.base + len(packets), midi_capture=dict(outstanding=[]))

    base = 0

    def wait(self, predicate, timeout=3):
        for _ in range(100000):
            state = self.snapshot()
            if predicate(state):
                return state
            self.elapse(.01)
        raise AssertionError("never")


class Fixture(unittest.TestCase):
    def run_session(self, ex=None, **kw):
        ex = ex or example()
        driver = FakeDriver(ex, **kw)
        takes = []

        def take():
            driver.routed_midi = False
            driver.ui.play()
            driver.elapse(1)
            driver.ui.stop()
            driver.ui.tap_cell(*control_cell("panic"))
            driver.routed_midi = True
            takes.append(True)
        row = manual_audio.course_before_after(driver, ex, ex["tracks"], "controlled-experimental", take)
        return driver, row, takes


class Orchestration(Fixture):
    def test_the_session_proves_before_routes_to_voices_takes_routes_back_and_proves_after(self):
        driver, row, takes = self.run_session()
        self.assertEqual(row["kind"], "manual-audio-course-before-after")
        self.assertTrue(row["passed"])
        self.assertEqual(takes, [True])
        self.assertEqual([p for p in ("before", "route_to_voices", "take", "route_to_midi", "after") if p in row],
                         ["before", "route_to_voices", "take", "route_to_midi", "after"])
        self.assertEqual(row["before"]["onsets"], len(example()["midi_contract"]["notes"]))
        self.assertEqual(row["after"]["onsets"], row["before"]["onsets"])
        self.assertEqual(row["route_to_voices"]["channels"], [1, 2])
        self.assertEqual(row["route_to_midi"]["channels"], [1, 2])

    def test_the_channels_are_routed_to_each_declared_voice(self):
        ex = example()
        driver = FakeDriver(ex)
        picked = []
        driver.ui.pick_device = lambda name: picked.append(name)
        manual_audio.course_before_after(driver, ex, ex["tracks"], "controlled-experimental", lambda: None)
        self.assertEqual(picked, ["Polyperc 1", "Doubledecker"])

    def test_before_and_after_are_proved_on_the_full_contract_even_for_a_solo_take(self):
        ex = example()
        driver, row, _ = self.run_session(ex)
        solo = FakeDriver(ex)
        row = manual_audio.course_before_after(solo, ex, [ex["tracks"][1]], "controlled-experimental", lambda: None)
        self.assertEqual(row["before"]["onsets"], len(ex["midi_contract"]["notes"]))
        self.assertEqual(row["route_to_voices"]["channels"], [2])

    def test_a_contract_mismatch_before_the_take_refuses_the_take(self):
        ex = example()
        driver = FakeDriver(ex, tamper_stage=1)
        takes = []
        with self.assertRaises(AssertionError):
            manual_audio.course_before_after(driver, ex, ex["tracks"], "controlled-experimental", lambda: takes.append(1))
        self.assertEqual(takes, [])

    def test_a_contract_mismatch_after_the_take_refuses_the_row(self):
        ex = example()
        driver = FakeDriver(ex, tamper_stage=2)  # no take plays here: the AFTER proof is the second play window
        with self.assertRaises(AssertionError):
            manual_audio.course_before_after(driver, ex, ex["tracks"], "controlled-experimental", lambda: None)

    def test_routing_refuses_any_public_input_that_is_not_a_routing_input(self):
        ex = example()
        driver = FakeDriver(ex)
        original = manual_audio.route_track

        def sneaky(c, track, channel, midi=False, port=1):
            original(c, track, channel, midi, port)
            if midi:
                c.ui.tap_control("pattern_select", 2)
        manual_audio.route_track = sneaky
        try:
            with self.assertRaisesRegex(AssertionError, "Non-routing"):
                manual_audio.course_before_after(driver, ex, ex["tracks"], "controlled-experimental", lambda: None)
        finally:
            manual_audio.route_track = original
        self.assertIs(driver.ui.__class__, FakeUi)


class Audit(Fixture):
    def build(self, **kw):
        ex = example()
        driver, row, _ = self.run_session(ex, **kw)
        return ex, driver, row

    def source(self, ex, row):
        # One native packet log for both windows: rebuild each window's packets from the contract at its origin.
        packets = []
        for name in ("before", "after"):
            window = row[name]
            fake = FakeDriver(ex)
            fake.playing = True
            fake.origin = window["origin_ns"]
            fake.logical_ns = window["origin_ns"] + int(64 / 6 * 1e9) + 1000
            fake.base = window["midi_start_index"]
            fake.total = 0
            packets += fake.snapshot()["midi"]
        return lambda start, end, clock: [p for p in packets if start < p["index"] <= end]

    def test_a_complete_row_is_accepted(self):
        ex, driver, row = self.build()
        self.assertTrue(manual_audio.check_course_before_after(ex, row, driver.recipe, self.source(ex, row)))

    def test_a_missing_before_or_after_is_rejected(self):
        ex, driver, row = self.build()
        for name in ("before", "after"):
            bad = {k: v for k, v in row.items() if k != name}
            with self.assertRaisesRegex(ValueError, "course before/after"):
                manual_audio.check_course_before_after(ex, bad, driver.recipe, self.source(ex, row))

    def test_a_proof_that_does_not_match_its_packets_is_rejected(self):
        ex, driver, row = self.build()
        for name in ("before", "after"):
            bad = copy.deepcopy(row)
            bad[name]["boundary_index"] += 1
            with self.assertRaises((ValueError, AssertionError)):
                manual_audio.check_course_before_after(ex, bad, driver.recipe, self.source(ex, row))

    def test_a_contract_mismatch_in_the_recorded_packets_is_rejected(self):
        ex, driver, row = self.build()
        source = self.source(ex, row)

        def tampered(start, end, clock):
            rows = source(start, end, clock)
            return [dict(p, bytes=[p["bytes"][0], p["bytes"][1] + 1, p["bytes"][2]]) if p is rows[0] else p for p in rows]
        with self.assertRaises(AssertionError):
            manual_audio.check_course_before_after(ex, row, driver.recipe, tampered)

    def test_an_extra_non_routing_input_between_the_proofs_is_rejected(self):
        ex, driver, row = self.build()
        recipe = list(driver.recipe)
        a = row["route_to_midi"]["action_start"]
        recipe.insert(a + 1, dict(type="grid", x=5, y=5, state=1))  # a pattern-grid tap, not a channel-select cell
        shifted = copy.deepcopy(row)
        for part in ("route_to_midi",):
            shifted[part]["action_end"] += 1
        shifted["after"]["action_start"] += 1
        shifted["after"]["action_end"] += 1
        with self.assertRaisesRegex(ValueError, "Non-routing input"):
            manual_audio.check_course_before_after(ex, shifted, recipe, self.source(ex, row))

    def test_play_or_panic_inside_a_routing_phase_is_rejected(self):
        ex, driver, row = self.build()
        for cell in (control_cell("play_stop"), control_cell("panic")):
            recipe = list(driver.recipe)
            recipe.insert(row["route_to_voices"]["action_start"], dict(type="grid", x=cell[0], y=cell[1], state=1))
            shifted = copy.deepcopy(row)
            for part in ("route_to_voices",):
                shifted[part]["action_end"] += 1
            for part in ("take", "route_to_midi"):
                shifted[part]["action_start"] += 1
                shifted[part]["action_end"] += 1
            shifted["after"]["action_start"] += 1
            shifted["after"]["action_end"] += 1
            with self.assertRaisesRegex(ValueError, "Non-routing input"):
                manual_audio.check_course_before_after(ex, shifted, recipe, self.source(ex, row))

    def test_a_gap_between_the_phases_is_rejected(self):
        ex, driver, row = self.build()
        bad = copy.deepcopy(row)
        bad["take"]["action_start"] += 1
        with self.assertRaisesRegex(ValueError, "contiguous"):
            manual_audio.check_course_before_after(ex, bad, driver.recipe, self.source(ex, row))

    def test_routing_calls_outside_the_routing_set_are_rejected(self):
        ex, driver, row = self.build()
        bad = copy.deepcopy(row)
        bad["route_to_midi"]["calls"].append("tap_control")
        with self.assertRaisesRegex(ValueError, "Non-routing"):
            manual_audio.check_course_before_after(ex, bad, driver.recipe, self.source(ex, row))

    def test_wrong_routed_channels_are_rejected(self):
        ex, driver, row = self.build()
        bad = copy.deepcopy(row)
        bad["route_to_midi"]["channels"] = [1]
        with self.assertRaisesRegex(ValueError, "channels"):
            manual_audio.check_course_before_after(ex, bad, driver.recipe, self.source(ex, row))

    def test_a_stand_in_port_rehearsal_row_is_not_a_voice_take(self):
        ex = example()
        driver = FakeDriver(ex)

        def take():
            driver.routed_midi = False  # the stand-in port is not the one the proofs listen to
            driver.ui.play()
            driver.elapse(1)
            driver.ui.stop()
            driver.routed_midi = True
        row = manual_audio.course_before_after(driver, ex, ex["tracks"], "controlled-experimental", take, stand_in_port=2)
        self.assertEqual(row["stand_in_port"], 2)
        self.assertNotIn("pick_device", row["route_to_voices"]["calls"])
        with self.assertRaisesRegex(ValueError, "rehearsal"):
            manual_audio.check_course_before_after(ex, row, driver.recipe, self.source(ex, row))
        self.assertTrue(manual_audio.check_course_before_after(ex, row, driver.recipe, self.source(ex, row), allow_stand_in=True))

    def test_a_row_that_never_picked_a_voice_is_rejected(self):
        ex, driver, row = self.build()
        bad = copy.deepcopy(row)
        bad["route_to_voices"]["calls"].remove("pick_device")
        with self.assertRaisesRegex(ValueError, "never routed"):
            manual_audio.check_course_before_after(ex, bad, driver.recipe, self.source(ex, row))


class SessionBinding(Audit):
    """audit_lesson_capture binds a record's row to its own results.json, recipe.json and native MIDI log."""

    def session(self, root, with_row=True):
        import json
        ex, driver, row = self.build()
        out = Path(root)
        (out / "native").mkdir(parents=True)
        source = self.source(ex, row)
        packets = source(0, 10 ** 9, "controlled-experimental")
        (out / "native/native-events.jsonl").write_text("\n".join(json.dumps(dict(p, kind=11)) for p in packets))
        (out / "recipe.json").write_text(json.dumps(driver.recipe))
        (out / "results.json").write_text(json.dumps([row] if with_row else []))
        return ex, dict(course_before_after=row, evidence=dict(path=str(out)))

    def test_a_bound_row_passes_the_lesson_capture_audit(self):
        import tempfile
        with tempfile.TemporaryDirectory() as root:
            ex, record = self.session(Path(root) / "s")
            self.assertTrue(manual_audio.audit_lesson_capture(ex, ex["tracks"], record))

    def test_a_row_missing_from_the_session_results_is_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as root:
            ex, record = self.session(Path(root) / "s", with_row=False)
            with self.assertRaisesRegex(ValueError, "not bound"):manual_audio.audit_lesson_capture(ex, ex["tracks"], record)

    def test_witness_evidence_on_a_course_record_is_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as root:
            ex, record = self.session(Path(root) / "s")
            with self.assertRaisesRegex(ValueError, "not witness"):manual_audio.audit_lesson_capture(ex, ex["tracks"], dict(record, midi_witness=dict(passed=True)))


if __name__ == "__main__":
    unittest.main()
