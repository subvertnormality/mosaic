# R10 playback ownership

## Existing pending-action inventory

| Action | Owner and identity | Time domain | Cancellation and terminal cleanup |
|---|---|---|---|
| Delayed strum onset | step closure captures note container, chord data and channel; scalar delayed-action ID belongs to channel clock | Channel-relative delayed action | Lattice reset discards future onsets; callback resolves live scale using the existing captured channel |
| Ordinary voice release | Note container retains player, MIDI channel/device; callback retains note and velocity | Channel-relative gate; nonpositive gates release immediately | must_execute IDs flushed on Stop; Note Off remains owed after Note On |
| Arp voice release | Same captured container, release ID additionally belongs to arp release_ids | Parent-channel phase plus off-phase offset; before-onset priority | execute_at_note_end plus arp finish flush; cancelling future arp onsets leaves owed releases intact |
| Arp next onset | Per-channel arp_sprockets and closure-local arp reference, interval and stop state | Lattice sprocket, channel division and shuffle projection | cancel_arp_onsets destroys future sprockets; finish also flushes owned release IDs |
| Slide sample/endpoint | Bounded ring slot, channel/parameter owner index, end occurrence | Absolute lattice transport plus projected channel onset occurrence | Replace silently; explicit finish may emit endpoint; retire ownership before callbacks; division/shuffle changes rebase without immediate output |
| MIDI transport pulse | midi_output_transport subscription, active flag, generation and epoch | Native outgoing F8 boundary plus intermediate scheduler deadlines | Cancel subscription and intermediate clock on Stop/reset; no generation guard is used to suppress owed voice releases |

This is the current ownership contract, not a claim every R10 extraction is done.
The MIDI adapter retains its existing note-count handling for overlapping pitches.
No universal generation system, new queue, heap or lattice rewrite is introduced.

## Voice emission/release boundary

`lib/clock/voice_lifetime.lua` now owns the existing On-then-schedule-Off helper
and ordinary/arp gate wrappers. It is constructed once with m_clock; step keeps
musical resolution, live-scale timing, dashboards and future onset decisions.
The callback still reads the captured note container, retaining existing behavior.
No new per-voice allocation, return convention or route remapping is introduced.
The unused selected-song/channel lookup was removed from that helper.

The existing arp release contract uses the explicit module instead of recursively
searching private step functions. All 54 combinations of parent period and arp
division pass. Reentrant Stop drains owned releases once; the boundary contract
still places release before onset. Full Lua suite: 1545 passed (27.608 seconds).
Six inventory/name/syntax guards passed. Existing step tests cover parent-route
retention during delayed live-scale edits and immediate nonpositive gate release.

Next: extract slide storage/interpolation/retiming behind the existing m_clock API,
then arp lifetimes and transport transitions one at a time. Preserve ring traversal
and reentrant callback behavior. Full R10 timing/profile acceptance remains owed.

## Native extraction regressions

| Case | Mode | Passing run |
|---|---|---|
| M-ARP-002 | controlled-experimental | 98a5a2f666f344f18a601200eaeca810 |
| M-LEN-004 | controlled-experimental | dfe7e87a914e4177bfa4748aa098fe04 |
| M-MIDI-001 | controlled-experimental | 2c31d93153c841c2bafa689d34a97f10 |
| M-ARP-002 | real-time | dcebda568973451aa0e4c6d5d468cbe3 |
| M-LEN-004 | real-time | c332bce9dbc842a087a9ecf6617f6c66 |
| M-MIDI-001 | real-time | 6df424ca88644e9aa449dd9508f0a5df |

Sol reviewed emission order, capture, scheduling flags, return behavior and allocation shape; no concrete correctness issue found. These results cover the extraction, not full R10 acceptance.
