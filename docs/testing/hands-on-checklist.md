# Hands-on checklist: the eight held-back fixes (2026-09-11)

These fixes rest on a decision rather than on a line of the manual, so they are held on the
branch `ux/pending-hands-on` and are **not** on `codex/behaviour-validation`. Each one has an
emulator regression that fails on the old code and passes on the new, but only you can say
whether the new behaviour is the one you want when playing.

For each: do the steps on the current build, then on the pending build, and compare with the
"now" and "with the fix" columns (both taken from the recorded runs, controlled and real-time
lanes). Mark **keep** or **drop**.

To try the pending build: `git checkout ux/pending-hands-on` in the Mosaic checkout you install
from. To drop one fix later, revert its commit; each is a single commit with its own patch and
`bugs.json` record.

---

## 1. S26 — an unset chord mask starts from X (`c26d0b0`)

**Steps.** Channel editor, Masks page, no step held. Turn Chd1 one detent up. Then turn it one
detent down twice.

| Now | With the fix |
|---|---|
| One turn up still shows **X**; one turn down shows **-6th** (-7th is unreachable downwards) | One turn up shows **2nd**; one turn down shows **-7th** |

**Why it matters to playing:** every chord-mask gesture is one detent different from before.
Case M-MASK-CHORD-X-001. It also rewrites the turn counts in 13 test helpers, which is the
largest ripple of the eight.

---

## 2. S14 — transport Stop clears keyboard chord state (`7615434`)

**Steps.** Hold a step and hold a key on a MIDI keyboard. Disconnect that keyboard while both
are held (so its Note Off never arrives). Press Play, then Stop. Now hold the same step and
press a single key.

| Now | With the fix |
|---|---|
| The new key is added as a **chord voice** over the lost key, and stays that way after Stop or Panic | The new key becomes the step's **note**, as a fresh entry |

**Also changed:** autosave and project save/load call the same stop function, so they now clear
keyboard chord state too. Worth a try: start a chord entry, let an autosave happen, then add the
next voice. Case M-KEYBOARD-STOP-001 (README 193, 601).

---

## 3. S34 — undoing a lock clears that lock's slide (`787b976`)

**Steps.** On the Trig Locks page give step 1 a lock on slot 1, and a second lock on slot 2.
Hold step 1 and press K3 to slide slot 1. On the Memory page, step back once (E3 left) to undo
the slot 1 lock. Hold step 1 again and look at the slide outline, then set a new slot 1 lock
there without pressing K3.

| Now | With the fix |
|---|---|
| The slide outline stays although no lock is behind it, and the new lock **slides** (40 → 90) | The outline is gone and the new lock **jumps** to its value |

**Side effect to check:** a slide you set with hold + K3 on a step before any lock existed is
also removed when a lock on that step is cleared. Case M-MEMORY-012 (README 964-969, 698-703).

---

## 4. S10 — a mapped CC returns the page on every MIDI channel (`85f0d19`)

**Steps.** Map a selected-channel mask parameter to a CC on **MIDI channel 2** (norns MIDI map,
input 1..2, output -1..1, accumulation on). Open the channel editor's Device Config page and
turn that CC.

| Now | With the fix |
|---|---|
| The editor jumps to Note Masks and **stays** there | It jumps to Note Masks and returns to Device Config after two seconds, as a channel-1 CC already does |

**Why it matters:** if you have controllers on channels 2-16, pages will now spring back where
they previously stayed put. The README documents neither the switch nor the return.
Case M-MAP-PAGE-RETURN-001.

---

## 5. S32 — live recording while a page key is held (`aeca4c1`)

**Steps.** Arm record. Hold the channel editor's own page button (row 8, button 3) and play a
key on the keyboard for about half a second, then release.

| Now | With the fix |
|---|---|
| Nothing is recorded, and the release commits a length-only mask that **silences** that step | The note is recorded on the current step with its length, as if no key were held |

Case M-REC-PAGE-KEY-001 (README 239, 316).

---

## 6. S4 — switching to an n.b. device without params clears slots 16-39 (`374406e`)

**Steps.** On a channel using the CC device with device params set up, switch the device to an
n.b. player that has no parameters of its own (Jf Kit). Open the channel's group in the norns
params menu and turn the first entry.

| Now | With the fix |
|---|---|
| The old device's entries (e.g. "CC 1") are still listed and still **send MIDI** | The slots are hidden and send nothing |

Case M-XA-007-NB-SWITCH-SLOTS (README 542, 546). Note this profile runs real-time only, so
there is no controlled-lane evidence.

---

## 7. S24 — a mask turned back to X clears the lock (`08400f9`)

**Steps.** Hold step 2 on the Masks page and turn Trig one detent down, so the step is muted.
Turn it back up to X and listen to step 2. Then hold step 3, set a velocity lock, turn it back
to X, and listen to step 3.

| Now | With the fix |
|---|---|
| The step **stays silent** although the screen shows X, and the velocity lock **keeps its value**; both survive a restart | Both play exactly as if the mask had never been set |

Chord masks are unchanged: -1 still means "-7th". Case M-MASK-OFF-001 (README 570, 597).

---

## 8. S18 — the chosen pattern's top-row LED flickers on all four step pages (`293a66c`)

**Steps.** In the note editor (and the velocity editor), put a column's value at its top row,
then switch through the four step pages (row 8, buttons 9-12) and watch the chosen pattern's
column on the top row.

| Now | With the fix |
|---|---|
| It flickers on page 1 only; on pages 2-4 it sits steady at level 12 | It flickers on every page, as README 471 describes |

Cosmetic, and the smallest risk of the eight. One existing case (M-PAT-006) expected the old
steady LED and was updated. Case M-EDIT-FLICKER-001.

---

## After your verdict

- **Keep:** I merge that commit into `codex/behaviour-validation` with its regression case.
- **Drop:** I revert the commit and turn its regression into a characterisation test that pins
  today's behaviour, so a later refactor cannot change it by accident.
