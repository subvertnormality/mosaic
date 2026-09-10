"""Song commands queued during playback, then Stop (README "Song Mode Operations",
line 910: a slot change during playback is queued and executed after the current
sequence completes). Stop before that boundary discards the queued slot and a queued
global length (arbitrated 2026-09-11: discard-on-stop, docs/testing/decisions.md
SEM-015); the next Play follows song mode from the playing slot.

Global length 2; slots 1, 2 and 4 carry channel-1 octaves 0, +1 and +2; slot 3 is
empty, so song mode loops slots 1 and 2.
"""


def song_queue_stop(c):
    c.configure()
    c.tap(6, 8); c.tap(2, 7); c.tap(8, 7)                         # global length 2
    for target, x in ((2, 11), (4, 12)):
        c.tap(6, 8); c.tap(1, 1); c.hold_tap((1, 1), (target, 1)); c.tap(target, 1); c.tap(3, 8); c.tap(1, 1); c.tap(x, 8)
    c.tap(6, 8); c.tap(1, 1)
    def onsets(s, marker): return [m['bytes'][1] for m in s['midi'] if m['index'] > marker and m['bytes'][0] == 144 and m['bytes'][2] > 0]
    def play(count):
        marker = c.snapshot()['midi_count']; c.tap(1, 8)
        state = c.wait(lambda s: len(onsets(s, marker)) >= count, timeout=6)
        c.tap(1, 8); c.wait(lambda s: not s['midi_capture']['outstanding'])
        return onsets(state, marker)[:count]
    def interrupted(gesture):
        """Play, make a queued change after the first onset, Stop before the boundary."""
        marker = c.snapshot()['midi_count']; c.tap(1, 8)
        c.wait(lambda s: len(onsets(s, marker)) >= 1, timeout=2); gesture()
        c.tap(1, 8); c.wait(lambda s: not s['midi_capture']['outstanding'])
        assert onsets(c.snapshot(), marker)[:1] == [60]
    def check(stage, actual, expected):
        assert actual == expected, (stage, actual, expected)
        c.results.append(dict(kind='song-queue-stop', stage=stage, notes=expected, passed=True))
    check('baseline', play(6), [60, 62, 72, 74, 60, 62])
    interrupted(lambda: c.tap(4, 1))                              # queue slot 4, then Stop
    check('queued-slot-discarded', play(6), [60, 62, 72, 74, 60, 62])
    interrupted(lambda: c.tap(8, 7))                              # queue global length 3, then Stop
    check('queued-length-discarded', play(6), [60, 62, 72, 74, 60, 62])
    c.tap(8, 7)                                                   # stopped: slot 1's length 3 applies now
    check('stopped-length-applies', play(9), [60, 62, 64, 72, 74, 60, 62, 64, 72])  # each slot has its own length
