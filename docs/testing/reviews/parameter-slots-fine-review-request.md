# Trig-parameter slot limits and fine-control semantic review

Use Codex only. Read-only local commands are allowed; do not edit or launch tests/runtime processes.

Decide the documented fine-control contract and review M-PARAM-045/046 using `docs/testing/parameter-slots-fine-validation.json`.

The repository conflicts: README line756 says hold K1 while E3 fine-tunes; cheat_sheet line947 says K3. Git blame shows the cheat wording entered in 064cc38b on 2024-11-03, then README was explicitly changed to K1 in 4f4084b5 on 2024-12-05. Current source scales wide-range values coarsely unless `is_key1_down`; K3 on the Trig Locks page toggles step/global parameter slides. M-PARAM-045 uses native key/encoder input on NRPN14: the same E3 detent changes Off(-1) to0 with K1, 0 to129 with neither, and129 to258 with K3. Exact standard NRPN bytes are asserted, then Play emits258 both as patch recall and step1 default before the note. It passes controlled and real time. Recommend preserving established K1 behavior and changing the cheat sheet from K3 to K1; changing K3 behavior would collide with documented/tested slides.

M-PARAM-046 assigns CC1..10 through K2, turns E2 twenty positions beyond the upper and lower ends, sets held locks, and proves selection clamps to slot10/CC10 and slot1/CC1 through exact repeated MIDI, timing, CC-before-note, gates and releases in both clocks. Existing M-PARAM-033 covers per-song copy isolation and M-PARAM-036 covers reassignment with existing locks; M-PARAM-043/044 cover all64 steps, all10 slots and live overwrite.

Challenge whether the K1/K3 evidence and history justify a manual correction rather than product change; whether K3 could plausibly be fine control without breaking slide behavior; NRPN oracle arithmetic and recall attribution; slot-limit proof; source bindings; and conservative inventory scope. Return a clear semantic decision plus ACCEPTED or CHANGES REQUIRED for these cases. Do not generalize the historical Digitakt NRPN compatibility exception.
