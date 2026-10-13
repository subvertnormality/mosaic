"""Song commands queued during playback, then Stop (README "Song Mode Operations",
line 910: a slot change during playback is queued and executed after the current
sequence completes). Stop before that boundary discards the queued slot and a queued
global length (arbitrated 2026-09-11: discard-on-stop, docs/testing/decisions.md
SEM-015); the next Play follows song mode from the playing slot.

Global length 2; slots 1, 2 and 4 carry channel-1 octaves 0, +1 and +2; slot 3 is
empty, so song mode loops slots 1 and 2.
"""


def song_queue_stop(c):
    ui = c.ui
    ui.configure()
    ui.song_editor(); ui.tap_control('global_pattern_length', 2); ui.tap_control('global_pattern_length', 8)
    for target, x in ((2, 11), (4, 12)):
        ui.song_editor(); ui.tap_control('song_pattern_slot', 1)
        ui.copy_slot(1, target, control='song_pattern_slot')
        ui.tap_control('song_pattern_slot', target); ui.menu('channel_editor')
        ui.select_channel(1); ui.tap_control('channel_octave', x - 10)
    ui.song_editor(); ui.tap_control('song_pattern_slot', 1)
    def onsets(s, marker): return [m['bytes'][1] for m in s['midi'] if m['index'] > marker and m['bytes'][0] == 144 and m['bytes'][2] > 0]
    def play(count):
        marker = c.snapshot()['midi_count']; ui.play()
        state = c.wait(lambda s: len(onsets(s, marker)) >= count, timeout=6)
        ui.stop(); c.wait(lambda s: not s['midi_capture']['outstanding'])
        return onsets(state, marker)[:count]
    def interrupted(gesture):
        """Play, make a queued change after the first onset, Stop before the boundary."""
        marker = c.snapshot()['midi_count']; ui.play()
        c.wait(lambda s: len(onsets(s, marker)) >= 1, timeout=2); gesture()
        ui.stop(); c.wait(lambda s: not s['midi_capture']['outstanding'])
        assert onsets(c.snapshot(), marker)[:1] == [60]
    def check(stage, actual, expected):
        assert actual == expected, (stage, actual, expected)
        c.results.append(dict(kind='song-queue-stop', stage=stage, notes=expected, passed=True))
    check('baseline', play(6), [60, 62, 72, 74, 60, 62])
    interrupted(lambda: ui.tap_control('song_pattern_slot', 4))  # queue slot 4, then Stop
    check('queued-slot-discarded', play(6), [60, 62, 72, 74, 60, 62])
    interrupted(lambda: ui.tap_control('global_pattern_length', 8))  # queue global length 3, then Stop
    check('queued-length-discarded', play(6), [60, 62, 72, 74, 60, 62])
    ui.tap_control('global_pattern_length', 8)                   # stopped: slot 1's length 3 applies now
    check('stopped-length-applies', play(9), [60, 62, 64, 72, 74, 60, 62, 64, 72])  # each slot has its own length
