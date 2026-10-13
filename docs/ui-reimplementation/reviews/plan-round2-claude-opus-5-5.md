## What works

Nothing notable.

## What doesn't work

Nothing notable.

## Risks

Nothing notable.

## Gaps

Nothing notable.

## Improvements

Nothing notable.

---
_paranoia-local · engine=claude · session_ref=`72819216-4795-46ca-825d-74fa1c675997` — to dispute a finding, call `rebut` with this session_ref and your counter-evidence._

=== PATCH PROPOSAL (SUPPLEMENTAL; REVIEW VERDICT UNCHANGED) ===
PATCH-PROPOSAL: UNAVAILABLE
REASON-JSON: "no successful fresh-census author session"
CALLER: inspect the candidate, confirm the bound preimage is current, apply deliberately, run appropriate tests, and submit the changed artifact in the same lineage with the next lawful round label. A stale proposal requires a new review.

CLAIM-REGISTER: 8 active external claims; 0 retired and excluded from active inventory
CLAIM-CLOSURE: 3 supported, 0 refuted, 5 unverified
ACTIONABLE SOURCE PACKETS:
- CLAIM C-3c5ac8939f — UNVERIFIED
  Plan wording: Large E1 deltas move one family boundary; owner E2/E3 scaling remains unchanged.
  Atomic proposition: The norns hardware provides three encoders and three keys.
  Replacement: none proven; remove, weaken, or research the assertion
  Assessment: Re-checked: monome's official hardware list names 3 endless rotary controls and 3 keys. The 2024 units use potentiometers instead of encoders, but that doesn't change the count of three controls for E1-E3 and three keys, which is what the plan's E1/E2/E3 wording depends on. Cold evidence attestation did not accept both publisher authority and passage entailment.
  Source 1: [primary/supports_claim] norns | monome/docs — monome
    Authority: monome designs and manufactures norns and publishes its official hardware documentation.
    Location: https://monome.org/docs/norns/ (monome.org/docs/norns, "interface" hardware list, lines 19-22)
    Exact passage: - 3 endless rotary controls. - units produced in 2024 have potentiometers with a slow turn. - units produced before 2024 and in 2025 (and beyond) have encoders with a fast turn. - 3 keys.
  Source 2: [primary/context] norns script reference — monome
    Authority: Official norns scripting reference maintained by monome.
    Location: https://monome.org/docs/norns/reference/ (norns script reference, script template, lines 85-90)
    Exact passage: function key(n,z) -- key actions: n = number, z = state end function enc(n,d) -- encoder actions: n = number, d = delta end
- CLAIM C-d972c1a6ba — UNVERIFIED
  Plan wording: Native input ownership takes precedence over all custom norns bindings.
  Atomic proposition: On norns, a quick tap of K1 swaps focus between the system menu layer and the script's playable interface, and script key/encoder actions apply while the playable interface has focus.
  Replacement: none proven; remove, weaken, or research the assertion
  Assessment: Re-checked: the official play documentation directly supports both parts, the K1 quick-tap layer swap and script-specific key/encoder actions while the playable interface has focus. Cold evidence attestation did not accept both publisher authority and passage entailment.
  Source 1: [primary/supports_claim] play | monome/docs — monome
    Authority: monome publishes the official norns user documentation describing the system menu and input layering.
    Location: https://monome.org/docs/norns/play/ (monome.org/docs/norns/play, menu/script layers section, line 72)
    Exact passage: There are two layers to the norns UI – a multi-page menu interface and a script’s playable interface. A quick tap of K1 is how you swap focus between these layers. In the diagram below, a quick K1 tap toggles between the multi-page menu layer (top row) and the current script’s playable interface (bottom image).
  Source 2: [primary/supports_claim] play | monome/docs — monome
    Authority: monome publishes the official norns user documentation describing the system menu and input layering.
    Location: https://monome.org/docs/norns/play/ (monome.org/docs/norns/play, menu/script layers section, line 73)
    Exact passage: While you are inside of the playable interface, the encoders and keys perform script-specific actions.
- CLAIM C-a257fbe094 — UNVERIFIED
  Plan wording: Native parameters retain their IDs, metadata and actions, including runtime-generated n.b./device inventories and the Rhythm Doctor analysis-server parameters.
  Atomic proposition: The nb (n.b.) norns voice library adds the parameters for the selected voices to a script at runtime via nb:add_player_params(), and MIDI devices connected when the script starts become selectable voices.
  Replacement: none proven; remove, weaken, or research the assertion
  Assessment: This sentence was edited, so it gets a new claim. The nb author's README supports runtime-generated voice parameters and selectable MIDI devices. The added Rhythm Doctor analysis-server parameters belong to this project and are out of scope. Cold evidence attestation did not accept both publisher authority and passage entailment.
  Source 1: [primary/supports_claim] sixolet/nb — sixolet, nb author
    Authority: The library author's own repository README is the governing documentation for nb behavior.
    Location: https://github.com/sixolet/nb (sixolet/nb README, usage highlights, line 11)
    Exact passage: nb:add_player_params() -- Adds the parameters for the selected voices to your script.
  Source 2: [primary/supports_claim] sixolet/nb — sixolet, nb author
    Authority: The library author's own repository README is the governing documentation for nb behavior.
    Location: https://github.com/sixolet/nb (sixolet/nb README, voices paragraph, line 20)
    Exact passage: MIDI devices that are currently connected while the script is started will be available for selection as vocies.
- CLAIM C-870f67e576 — UNVERIFIED
  Plan wording: norns handles a short K1 tap itself and the script never receives it, so K1.short and native.return are emitted when the router observes menu mode change.
  Atomic proposition: On norns, a short K1 tap is never delivered to the script's key() callback.
  Replacement: none proven; remove, weaken, or research the assertion
  Assessment: The docs describe the quick-tap layer swap but say nothing about whether the script's key() callback receives the tap. menu.lua appears to use a 0.25 s K1 hold metro that dispatches key(1,1) only after the hold time. I could not get an exact verbatim passage showing short taps are withheld from the script, so this stays unverified. The executor should confirm it on the device or in menu.lua before relying on it.
  Source 1: [primary/context] play | monome/docs — monome
    Authority: monome publishes the official norns user documentation describing the system menu and input layering.
    Location: https://monome.org/docs/norns/play/ (monome.org/docs/norns/play, menu/script layers section, line 72)
    Exact passage: A quick tap of K1 is how you swap focus between these layers.
  Source 2: [primary/context] norns/lua/core/menu.lua — monome (norns repository)
    Authority: monome's official norns system source implements K1 short/hold dispatch.
    Location: https://github.com/monome/norns/blob/main/lua/core/menu.lua (lua/core/menu.lua, _norns.key handler, source lines 111-124 (capture lines 466-479))
    Exact passage: _norns.key = function(n, z) -- key 1 detect for short press if n == 1 then if z == 1 then _menu.alt = true pending = true t:start() elseif z == 0 and pending == true then _menu.alt = false if _menu.mode == true and _menu.locked == false then _menu.set_mode(false) else _menu.set_mode(true) end t:stop() pending = false
- CLAIM C-ad82977471 — UNVERIFIED
  Plan wording: Held K1 edges are the only K1 input the script sees
  Atomic proposition: On norns, the script's key() callback receives K1 press and release events only when K1 is held past the system's short-tap threshold.
  Replacement: none proven; remove, weaken, or research the assertion
  Assessment: The source seems to deliver K1 to the script only after a hold-time metro (search excerpts mention KEY1_HOLD_TIME = 0.25 and a metro calling _menu.key(1,1)). No exact authoritative passage showing the full press/release delivery rule was available, so this stays unverified.
  Source 1: [primary/context] norns/lua/core/menu.lua — monome (norns repository)
    Authority: monome's official norns system source implements K1 short/hold dispatch.
    Location: https://github.com/monome/norns/blob/main/lua/core/menu.lua (lua/core/menu.lua, _norns.key handler, source lines 111-131 (capture lines 466-486))
    Exact passage: _norns.key = function(n, z) -- key 1 detect for short press if n == 1 then if z == 1 then _menu.alt = true pending = true t:start() elseif z == 0 and pending == true then _menu.alt = false if _menu.mode == true and _menu.locked == false then _menu.set_mode(false) else _menu.set_mode(true) end t:stop() pending = false elseif z == 0 then _menu.alt = false _menu.key(n,z) -- always 1,0 if _menu.mode == true then _menu.redraw() end else _menu.key(n,z) -- always 1,1 end
  Source 2: [primary/context] norns script reference — monome
    Authority: Official norns scripting reference maintained by monome.
    Location: https://monome.org/docs/norns/reference/ (norns script reference, script template, lines 85-87)
    Exact passage: function key(n,z) -- key actions: n = number, z = state end
LINEAGE: mosaic-ui-reimplementation-20260924 (rounds recorded: 2)
CLASS-REGISTER: staged correction parsed — NONE
CLASS-CLOSURE: 0 open, 0 closed, 0 surviving matches, 0 exempt, 0 unmechanized
STRUCTURAL-PHASE: final
STRUCTURAL-DEBT: 0 blocking open
FINAL-REGRESSION: required engine=claude
STRUCTURAL-CONVERGENCE: BLOCKED — cold final regression is required.
STAGED-ATTEMPTS: total=1 validation-retries=0 validation-invalid=0 execution-failed=0
CONVERGENCE: BLOCKED — external claim closure remains open.
REVIEW-ATTEMPTS: total=4 validation-retries=0 validation-invalid=0 execution-failed=0