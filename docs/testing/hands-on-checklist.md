# Emulator-arbitrated UX decisions (2026-09-12)

All eight formerly held-back fixes are **kept** and active on
`codex/behaviour-validation`. The decisions use complete user-like grid, key,
encoder and MIDI input through the emulator and assert user-perceived grid,
screen, MIDI, parameter-menu, persistence and lifecycle results. Each fix had
already failed for its stated reason on the unfixed code before passing with the
isolated candidate. Fresh fixed-tree runs below bind the decisions to revision
`300e93a85e6a7de41c1f3e9f4c2badb9fa57a13d`.

These are automated product decisions rather than claims about physical norns
hardware. Seven cases pass both the controlled and real-time lanes. The n.b. JF
Kit case uses its applicable real-time `crow-jf` profile because that profile is
not supported by the controlled runtime.

| Decision | Behavior retained | Automated oracle | Controlled | Real-time |
|---|---|---|---|---|
| S26 keep | An unset chord mask starts at X; one detent up selects 2nd and one down selects -7th. | `M-MASK-CHORD-X-001`: screen labels after physical encoder turns. | `cab9745fa7024ccca944087d120701b2` | `a5c987a34a3d4b6cbab92584b650aa34` |
| S14 keep | Stop clears stale keyboard chord-entry state after a missing Note Off. | `M-KEYBOARD-STOP-001`: MIDI disconnect, transport controls, subsequent grid/keyboard entry and grid result. | `6f85e3232e2a47d78bf8bc243e4a55cf` | `b2514683a3bd4a839bfd73f014afd600` |
| S34 keep | Clearing or undoing a parameter lock clears the slide belonging to that lock. | `M-MEMORY-012`: two-lock history flow, slide LED state and jump-versus-slide MIDI output. | `4405750b0f9a48668be36de023ab96e4` | `839cb88d201e49038fa3e68befbaf1c7` |
| S10 keep | A mapped CC returns from its temporary page on MIDI channels 1, 2 and 16. | `M-MAP-PAGE-RETURN-001`: MIDI mapping input and timed screen-page return. | `3df481cf59cc4de0855d981ffb2293ac` | `4850a64c69d748ebbf3e05d836413178` |
| S32 keep | Live recording continues while a non-step page key is held. | `M-REC-PAGE-KEY-001`: first press through final release, recorded note/length, grid and MIDI playback. | `88fac56aa50b4e6a9fc4945b038af587` | `cc37989c9d044d7c894f53a86f20918c` |
| S4 keep | Switching from CC to an n.b. device with no parameters clears slots 16-39. | `M-XA-007-NB-SWITCH-SLOTS`: physical device switch, parameter-menu state and absence of stale MIDI. | N/A for profile | `58161ce7e0a54275808d2ea4be555229` (`crow-jf`) |
| S24 keep | Turning a trig or velocity mask back to X removes its lock and survives restart. | `M-MASK-OFF-001`: grid/screen state, MIDI playback and autosave/restart behavior. | `62365d112891416f9aed491f6387e222` | `65943ec2758c4b8d9288b5981e032323` |
| S18 keep | The selected pattern's top-row LED flickers on every step editor page. | `M-EDIT-FLICKER-001`: physical page navigation and time-sampled grid levels. | `4b13fd78c0cb49da8d4ed3e815644f7c` | `f5b5657f48494006a3fa56089c00a54b` |

No hands-on verdict remains. These regressions now pin the intended behavior for
the later refactor. The broader campaign and emulator release gates remain
separate prerequisites before that refactor starts.
