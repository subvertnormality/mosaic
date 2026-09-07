# Campaign progress

2026-09-07: requested Paranoia plan critique plus focused follow-up returned and
were triaged. User confirms browser manual derives from repository docs; README
and cheat sheet hashes bind the inventory. No independent browser-source gate.

The Mosaic-owned runner boots this actual worktree through the generic emulator
Session API, drives real grid/keys/encoders, and records native screen/grid/MIDI
and cleanup evidence. Two initial cases are implemented. Pattern editing passed
on the baseline. The length collision case failed at approximately0.665 seconds
against an independent2-step expectation of0.333 seconds at90BPM, despite the grid
showing the shorter duration. The isolated pattern merge correction makes the
unchanged case pass; the unchanged editing case still passes. All474 upstream
units pass on baseline and corrected isolated copies with pinned runtime Lua and
a failing curl guard. Exact artifact paths and digests are in bugs.json.

The correction computes effective source-pattern lengths at the next source trig
without destroying the stored editing length; merge modes consume those lengths.
Tests for wrap/restoration/merge/mask interactions still need implementation.

Coverage remains incomplete:113 README headings plus the cheat sheet are indexed,
but only two requirements have partial-domain executable coverage. --require-all
fails explicitly. Controlled time has an inspected adapter design, no admitted
runtime implementation yet. T00/T01/T02 remain unfinished; no refactor starts.
