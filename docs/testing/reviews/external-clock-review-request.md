Focused Codex-only paranoia review of the new external MIDI-clock fault checkpoint.
This is a trusted single-user local musical development utility. The user has
approved sending these repository sources and evidence to Codex. Review only;
Use read-only shell commands as needed to inspect the listed local files, Git
history and retained evidence. Do not edit files, run tests or emulator/runtime
processes, use extra agents, browse the web, or certify the full campaign.

The new generic norns probe and Mosaic cases cover alternating +/-5ms jitter,
one missing clock, one extra clock at a half interval, abrupt and gradual
100-to150BPM changes, per-port receive selection, and a500ms clock gap followed
by explicit Start. Controlled and real-time results all pass. The intended
musical rule is received-pulse ordinal at24PPQN: missing input delays later
boundaries and extra input advances them. Pinned norns may extrapolate between
pulses. Without Stop it freewheels from the last estimate; explicit Start must
cancel old playback ownership, release the sounding note, and reanchor Mosaic
step1. Recovery without a transport command remains unclaimed and pending.

Assess these specific risks:

1. Is the expected-timing oracle independent enough, or does it mirror the
   norns estimator/Mosaic scheduler and permit a timing regression?
2. Can note filtering/accounting miss wrong ports/channels, extra/missing notes,
   duplicate/incorrect releases, reordered events, stale post-Start output, or
   output after Stop?
3. Does the physical CLOCK menu recipe actually prove input1 selection and
   port2 rejection, given norns defaults to all inputs?
4. Are the controlled bounds (2ns,2ms,3ms,5ms by scenario) and the existing
   additional10ms wall dispatch allowance capable of hiding a whole-pulse or
   musically material phase error?
5. Is the manual statement about all-input default, received-pulse behavior,
   freewheel and explicit-Start recovery no broader than source and evidence?
6. Are the generic and Mosaic recovery traces checking one owner after restart,
   or merely accepting the observed output as a golden trace?

Give concrete material findings with file/line and a bounded correction/test.
Distinguish missing future scope from a blocker in this slice. Do not request
hardware/manual testing, a broad refactor, security governance, stochastic
certification, or dual-vendor review.

Mosaic files:
- tests/behaviour/external_clock_faults.py
- tests/behaviour/test_external_clock_fault_oracle.py
- tests/behaviour/cases.py
- README.md
- tests/behaviour/manual-inventory.json
- docs/testing/external-clock-fault-validation.json

Generic emulator files:
- /home/andy/projects/monome-emulator-midi-clock/fixtures/probes/midi-clock-faults/midi-clock-faults.lua
- /home/andy/projects/monome-emulator-midi-clock/tests/external_midi_faults_native.py
- /home/andy/projects/monome-emulator-midi-clock/docs/delivery/external-midi-fault-checkpoint.json

Final generic evidence:
- /home/andy/projects/monome-emulator-midi-clock/artifacts/external-midi-faults/e61945eb3ef64811a7134f7dc50ab64b/manifest.json
- /home/andy/projects/monome-emulator-midi-clock/artifacts/external-midi-faults/8394c266e5a44c52977ff8a7f9c78c66/manifest.json

Final Mosaic manifests are enumerated and hashed in
docs/testing/external-clock-fault-validation.json. The full526-test unit log and
18 mutation-test log are under
/home/andy/projects/mosaic-behaviour-runs/external-clock-units-20260910-0218/.
