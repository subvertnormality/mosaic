# Vertical-list UI documentation migration

Status: first source update complete after both frozen baseline lanes demonstrated the missing simultaneous row visibility. Candidate images and audited interactive bindings remain pending.

## Authorized scope

Convert live focused pages to stable vertical lists. Preserve Masks (C01), ten-slot Trig params overview, musical diagrams, read-only dashboards and native PARAMS. E2 selects a visible row; E3 edits the existing value. Retain contextual K2/K3, staged Apply/Cancel, held-step scope, and startup animation. Implementation contract: four stable field rows below title and scope. A long selected value uses a separate full-width value row, leaving three field labels visible. Lists longer than the viewport show the selected position beside scope. Essential labels and values remain still with motion on or off. The contextual footer replaces previous/next labels; startup/title motion and nonconverted art remain.

## Source changes after baseline

1. Rewrite README Norns Menu Navigation display explanation: list rows replace single large value and previous/next-field footer. Explain viewport/selection without implying musical diagrams became menus. Preserve every legacy heading and anchor.
2. Update Clock, Scale, Slot setup, Tempo/feel, Trig Options and Rhythm Doctor setup instructions with explicit E2 row selection and E3 edit. Preserve draft/live semantics and existing bounds.
3. Update UI Motion to describe only animations retained by the candidate. Do not invent a Trig params conversion; both overview grids remain.
4. Update cheat sheet essential controls and append concise editable-list visibility guidance. Retain exact Masks/held-step clearing exceptions and ten-slot assignment controls.
5. Update relevant reference-learn, reference-channel, reference-scale, reference-song, reference-pattern, reference-options and reference-musical prose/controls. Leave masks.yaml unchanged.
6. Add practical before/action/result examples (for instance select Clock Division for a slower bass or prepare a second Scale slot), not boundary-test transcripts.

## Evidence and publication migration

Old generated frames, raw native captures, source identities and failure artifacts remain immutable. Any existing scene whose native screen oracle asserts focused layout must be recaptured from the changed actual app. A changed caption or source timestamp cannot make an old framebuffer depict the new list. Source guards prohibit indexed writes during native baselines/candidate runs. Native captures must include grid and screen output under images/ and be bound by the corresponding new behaviour assertions.

Candidate documentary freeze must follow implementation control/layout confirmation and precede real/controlled recapture. Affected old scene references require an explicit historical or pending status until new audited bindings are available. Existing book completeness and authority activation remain pending; this change does not authorize moving authority wholesale from README to YAML.

## Literal terminology inventory

The following matches need human triage: musical horizontal lines, mask clear-neighbour wording, ten-slot overview wording and supplemental marquee are not carousel instructions.

- `README.md:33`: Welcome to _Mosaic_, a powerful rhythm- and harmony-focused sequencer designed to unify control over your entire studio. It combines the advanced features of Elektron sequencers with generative and modular techniques, enabling you to craft complex rhythms and harmonies effortlessly. Whether you're sketching ideas or composing full tracks, Mosaic offers a deep and unique musical experience. This manual will help you quickly navigate _Mosaic_ and start creating tunes in no time.
- `README.md:352`: Every screen has the same parts. The title row names the screen and its scope: the channel (`CH03`), the song slot when it is not the first (`S02`), and any held steps (`ST05` for one step, `3ST` for several). A Channel screen also shows `MUTE` when the channel is muted, its octave when it is not 0 (`OCT+1`), and a held step's octave lock (`O-1`); the pattern editor names the pattern it edits before the channel it shows (`PAT02 CH01`). The selected field is outlined or marked with `>`, and its whole value is always shown: in its cell on a grid of fields (on the last line instead, beside its full name, when the cell is too narrow and shows `...`), or in large type on a single-field screen. The last line lists the controls for the screen, or shows a tooltip after a grid action. A grid action brings up the screen that shows what it changed, with that value chosen: a merge button or a pattern assignment shows Merge modes (where E2 and E3 also change the trig, note, velocity and length merge modes, including the pattern-priority ones), a channel scale lock shows Scale source, global transposition and scale-track locks show Scale overview, and the song length fader shows Song playback. K2 or E1 then carries on from there. Screens that only show information, such as Scale overview, Song playback and Paint preview, list every value at once with no cursor. The four small tiles at the right of the title row are _Mosaic_'s mark; they light up in turn when something changes.
- `README.md:682`: This space displays 16 steps at a glance. Active trigs appear as soft-glowing vertical bars while the root note lies in a subtle horizontal line. The notes you've actively chosen glow brightly. To pick a note for any of the 16 steps, just press. Whilst holding shift (K1), any entered note is automatically duplicated across all 4 step screens.
- `README.md:979`: The Trig params screen of the channel editor shows all ten slots at once. Each slot shows its parameter's two short names from the device definition, the first above the value and the second below, so together they name the parameter (for example `Quan` over `Note` for Quantised Fixed Note). The names stay still; one too long for its slot is cut short. A value too wide for its slot shows `...`, and while that slot is selected its full name and whole value take the last line. Here's how to navigate and manipulate these settings:
- `README.md:1284`: The sequencer features an autosave function when it is not actively playing. If left idle, it will automatically save your work under the name "autosave" after 60 seconds. When you start Mosaic again, it automatically loads this most recent autosave. Before replacing the current project, Mosaic checks saved song slots, global lengths, and channel and scale-track ranges. If a check fails, the screen identifies the problem and the current project and playback are retained. Autosaving is then suspended to protect the rejected file; editing, playing or cancelling a dialog does not resume it. Successfully loading a valid project, saving a named project, or choosing New resumes the normal idle autosave interval. A failed save leaves autosaving suspended. Valid saved one-step ranges remain supported, without adding a one-step range gesture. These checks cover the saved range structure, not every possible corrupted project field.
- `README.md:1376`: Turns decorative screen motion on or off (**PARAMS > MOSAIC > UI motion**, default On): the start-up animation, the light running round _Mosaic_'s mark, the selection's shadow gliding across the Masks and Trig params grids (diagonally when it changes row), names and values too long for their space scrolling right to left so you can read them in full (the names in the Masks and Trig params grids stay still), values rolling into place, and the characters. The Rhythm Doctor dances to the tempo of the captured bank, the Merge Shape garden sways and the Harmony choir bobs while the sequencer plays, and a metronome swings on the clock and tempo screens. A single numeric value, such as a mask or trig param, also shows a small dial of where it sits in its range, beside the value itself. Motion never delays input, hides a value for more than a moment or changes timing; with it off, every screen is still.
- `manual/features/reference-channel.yaml:1620`: scope: Clearing one and all selected-channel step overrides retains defaults and neighboring overrides.
- `manual/features/reference-channel.yaml:1623`: rationale: Clearing one and all selected-channel step overrides retains defaults and neighboring overrides.
- `manual/features/reference-channel.yaml:2865`: \ screen of the channel editor shows all ten slots at once. Each slot shows its parameter's two short\
- `manual/features/reference-channel.yaml:2932`: - M-PARAM-DIAL-OFF-001
- `manual/features/reference-locks.yaml:788`: scope: All ten parameter slots are reachable; selecting beyond either endpoint clamps. Individual
- `manual/features/reference-locks.yaml:1162`: scope: Public note clear neighbors, plus actual scale/transpose/octave lock editing/clear precedence
- `manual/features/reference-locks.yaml:1174`: scope: Public note clear neighbors, plus actual scale/transpose/octave lock editing/clear precedence
- `manual/features/reference-locks.yaml:1187`: scope: Public note clear neighbors, plus actual scale/transpose/octave lock editing/clear precedence
- `manual/features/reference-locks.yaml:1191`: rationale: Public note clear neighbors, plus actual scale/transpose/octave lock editing/clear precedence
- `manual/features/reference-locks.yaml:1513`: dialog do not resume autosave. A successful valid load, a successful named save or New resumes the
- `manual/features/reference-options.yaml:1971`: - Right-to-left scrolling for names and values that exceed their available space. Names on the Masks
- `manual/features/reference-options.yaml:1974`: - Values rolling into place and animated characters.
- `manual/features/reference-options.yaml:1980`: - A swinging metronome on the clock and tempo screens.
- `manual/features/reference-options.yaml:1983`: A single numeric value, such as a mask or trig parameter, also displays a small dial beside the value
- `manual/features/reference-pattern.yaml:680`: The grid displays 16 steps at a time. Active trigs show dim vertical bars; a dim horizontal line marks

## Confirmed converted screen IDs

C04 Clock; S01 Scale; P02 Trig Options; A01 Slot Setup; A02 Global Feel; F01 Clock draft; F08 Parameter Slide; C10 Chord Timing; C12 Mask Detail; C13 Trig Detail; R01 Record; R02 Capture; R04 Analysis; R05 Window; R06 Alignment; R08 Paint preview; R09 Paint result.

C01 Masks and C02 Trig Params remain simultaneous overview grids. Masks' visible controls and held-step behaviour remain unchanged. The single-field C12/C13 detail routes become labelled rows without changing the overview they are reached from.

## Ownership

README, cheat sheet and reference-channel/scale/song/pattern/options/locks are owned by the vertical-list documentation task. The course author owns reference-learn/workflow/musical, tutorials and cookbook and receives the same control contract. Masks authoring is unchanged. Root owns publication/generation tooling. Native baseline and candidate freeze coordinator owns release of source-write windows.
