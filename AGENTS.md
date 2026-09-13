# Mosaic development instructions

Mosaic is a grid-first norns sequencer. `README.md` is its user manual and the
primary source of truth for intended behaviour. `cheat_sheet.html` is a second
user-facing reference and must remain consistent with the manual.

## Development method

Use red-green-refactor for behaviour changes:

1. Add the smallest regression that demonstrates the missing or incorrect behaviour.
   For a defect, prove that the test fails on the unfixed revision for the expected
   reason. For a new feature, write its externally observable acceptance first.
2. Make the smallest production change that makes the regression pass.
3. Refactor only with the new regression and relevant existing coverage green.
4. Run the affected unit and integration tests, the relevant emulator-backed behaviour
   tests, and the existing full Lua suite before considering the change complete.

Do not change the monome emulator to imitate a Mosaic bug or make a Mosaic test pass.
The emulator is an independent, general-purpose norns/grid utility. Keep Mosaic-specific
oracles, fixtures, navigation and compatibility rules in this repository.

## Required evidence

Unit tests are fast evidence for algorithms, data transformations, bounds and failure
paths. Integration tests cover collaborations between Mosaic modules. Use them
exhaustively where user-input behaviour tests would add cost without increasing
confidence.

Unit and integration tests alone are insufficient for a user-visible feature. Add
behaviour coverage under `tests/behaviour/` that starts the actual Mosaic application,
uses grid, norns key/encoder or MIDI input through the emulator's public input path,
and observes the result a player can perceive: emitted MIDI, grid LEDs, the screen,
persistence or a visible failure. Internal Lua state may aid diagnosis but is not the
sole acceptance oracle.

Behaviour coverage must include meaningful boundaries, failure modes and interactions
with existing features. Timing-sensitive behaviour needs exact controlled-time musical
expectations and an applicable real-time check. Controlled time supplements real time;
it does not establish host or hardware scheduling accuracy. Keep random behaviour
deterministic with explicit seeds and invariant-based expectations.

A behaviour defect fix normally needs a regression that fails on the unfixed code in
both real-time and controlled-time lanes before the production change. A lane may be
inapplicable when it depends on audio, Crow, physical hardware or real wall time; record
that reason explicitly. Do not weaken an oracle or tolerance merely to obtain a pass.

Every assertion must cite the relevant `README.md` behaviour or be labelled as a
characterisation outside the manual. Preserve failure evidence and source identity so
a passing candidate cannot overwrite or relabel its baseline.

Manual clicking or listening is never required acceptance. Tests must leave no running
emulator sessions, held grid keys, active notes or modified user projects.

## Manual and images

Every new user-facing feature must be explained in `README.md`, with the cheat sheet
updated when it affects controls or quick-reference behaviour. Include appropriate grid
and norns screen images that show how the feature is reached and what feedback the user
receives. Prefer deterministic captures of the actual emulator framebuffer and grid
state. Store durable documentation images under `images/`, and keep the corresponding
behaviour assertions so the image cannot replace semantic verification.

Fixing documented behaviour does not require a new image unless the visible interface
or workflow changes. Documentation-only claims do not replace executable evidence.

## Validation scope

Use focused tests while developing. Run broader coverage once after the implementation
settles, and avoid duplicating expensive full-suite runs when focused evidence closes a
small final change. Performance tests must distinguish Mosaic work from emulator or host
scheduling, and may not claim physical-norns equivalence without device evidence.

GitHub Actions behaviour smoke tests are a fast cross-platform gate, not the complete
campaign. Their reports must state the selected cases and leave
`complete_regression_run` false. Full-suite and real-norns evidence remain separately
identified. The repository configuration-creator web page is outside the behaviour-test
campaign unless explicitly requested.
