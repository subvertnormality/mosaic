# Live keyboard recording placement campaign

Priority user report: notes entered live often appeared on the wrong steps.
This brings the relevant C10 recording work forward while C08 remains unfinished.
Every scenario uses scheduled native MIDI input and public grid/key/encoder
actions. Model inspection is diagnostic only. Require both recorded grid/mask
feedback and disarmed replay MIDI with independently calculated step positions.

| Area | Required cases | Status |
|---|---|---|
| Stable placement | Empty pattern, distinct notes inside steps2/4 at100BPM, external MIDI clock, disarmed internal replay | M-REC-001 passes controlled and real-time |
| Boundary phase | Just before/on/after step boundaries, native pulse boundaries and fractional phases; explicit equal-deadline ordering contract | M-REC-002/003 pass at minus/plus2ms; M-REC-004 exact pulse hypothesis fails; SEM-008 open |
| Clock and tempo | Internal and MIDI sources, slow/fast tempo, tempo change while held, source handoff | Planned |
| Channel position | Channel divisions, non-first range start, unequal/coprime lengths, selected-channel switches during held notes | M-REC-005 origin ownership; M-REC-008/009/010 non-first ranges pass; divisions and unequal lengths remain |
| Wrap | Last-to-first step, grid row transitions, global/channel wrap, song transitions | M-REC-009 crosses a grid row; M-REC-011/012 record across channel wrap; song transitions remain |
| Note lifecycle | Short/long notes, same-pitch retrigger/overlap, chords and all release orders, note-on velocity0 | Planned |
| Recording lifecycle | Arm/disarm before/on/after boundary; stop/start while held; empty and existing target steps | Planned |
| Feedback | Live updates and stopped/revisited grid/mask screen; distinguish stale display from wrong stored/replayed position | Planned |

Controlled tests use exact logical deadlines and three fresh-process repeats.
Real-time tests retain actual native input-delivery timestamps and compare them
with the independently scheduled musical grid; host dispatch errors must be
reported rather than reclassified as recording success. A single middle-of-step
pass does not establish boundary correctness. Keep failing recipes and isolate
emulator scheduling defects from Mosaic recorder or display defects before fixes.


Initial finding: exact scheduled pulse-deadline notes appear on preceding steps
1/3 rather than the hypothesis2/4 in both lanes. The controlled trace places note
input/preview at4810000000ns and the sequencer's global-step emissions at
4810000001ns (same separation at5110000000ns). Pinned native clock.sync uses strict
beat>target, already covered by C16. A pulse deadline is therefore not automatically
the application step-transition deadline. This is not yet classified as a Mosaic
defect or a hardware reproduction. Do not change the oracle or production timing
just to make the case green. SEM-008 asks whether current-step quantisation should
remain or change to nearest-step behavior. The before/after tests and midpoint
test have passing grid and disarmed MIDI replay evidence; exact-boundary acceptance,
fresh three-process repeats and every other matrix row remain open.
