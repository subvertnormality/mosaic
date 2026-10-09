import unittest

import manual_publication_verify as audit

def midi(index, bytes_, t, port=1):
    return dict(kind=11, index=index, port=port, bytes=bytes_, logical_ns=t)

class SongRepeatAdvance(unittest.TestCase):
    def events(self, count):
        low, high = [60, 62, 64, 65], [72, 74, 76, 77]
        pitches = ([low[i % 4] for i in range(8)] + [high[i % 4] for i in range(16)] + [low[i % 4] for i in range(4)])[:count]
        return [midi(i + 1, [144, p, [127, 117, 107, 97][i % 4]], i) for i, p in enumerate(pitches)]

    def test_accepts_exact_sequence_and_rejects_changes(self):
        row = dict(stage="slot-2-pass-1", levels=[7, 15, 2], pass_text="1 / 2", latest_pitches=[72, 74, 76, 77], onsets_so_far=12)
        events = self.events(12)
        state = dict(grid=[7, 15, 2] + [0] * 109, midi_count=12)
        audit.check_song_repeat_advance(row, state, events, "controlled-experimental")
        bad = [dict(e, bytes=[144, 61, e["bytes"][2]]) if e["index"] == 12 else e for e in events]
        with self.assertRaisesRegex(ValueError, "wire sequence"):
            audit.check_song_repeat_advance(row, state, bad, "controlled-experimental")
        with self.assertRaisesRegex(ValueError, "grid levels"):
            audit.check_song_repeat_advance(row, dict(state, grid=[15, 7, 2] + [0] * 109), events, "controlled-experimental")
        with self.assertRaisesRegex(ValueError, "Changed literal"):
            audit.check_song_repeat_advance(dict(row, pass_text="2 / 2"), state, events, "controlled-experimental")

class ModulationCcPhase(unittest.TestCase):
    def events(self, cc):
        out = [midi(1, [176, 1, cc], 0), midi(2, [250], 1)]
        for i in range(9):
            pitch, velocity = [(60, 127), (62, 117), (64, 107), (65, 97)][i % 4]
            out.append(midi(3 + i, [144, pitch, velocity], round(i / 6 * 1e9)))
        return out

    def row(self, **extra):
        return dict(phase="halfway", depth=.1, source=.5, cc=38, notes=9, late_window_onsets=0, **extra)

    def test_accepts_formula_cc_and_rejects_wrong_value(self):
        audit.check_modulation_cc_phase(self.row(), self.events(38), "controlled-experimental")
        with self.assertRaisesRegex(ValueError, "No native playback"):
            audit.check_modulation_cc_phase(self.row(), self.events(32), "controlled-experimental")
        with self.assertRaisesRegex(ValueError, "Matrix formula"):
            audit.check_modulation_cc_phase(self.row(cc=32) if False else dict(self.row(), cc=32), self.events(32), "controlled-experimental")

    def test_rejects_wrong_phrase(self):
        events = self.events(38)
        events[5]["bytes"][1] = 61
        with self.assertRaisesRegex(ValueError, "No native playback"):
            audit.check_modulation_cc_phase(self.row(), events, "controlled-experimental")

if __name__ == "__main__":
    unittest.main()
