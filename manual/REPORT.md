# Review pilot: interactive Masks manual

Built on a fresh fetch of `origin/codex/1.4.0`, commit `54d7b871358fcc68b7166847603cc9fb1461d0b6`, in `/home/andy/mosaic-manual-1.4.0` on `manual/1.4.0-interactive`. The older Windows workspace and its existing edits were preserved. Nothing was pushed, published or submitted as a PR.

## Delivered

- Research decisions, proposed site map, a 125-heading source inventory and discrepancy ledger.
- YAML authoring, Draft 7 schema and a rejecting validator.
- Native capture pipeline using the unchanged behaviour driver and independent emulator.
- Masks page with four scenes and 22 steps: inheritance/clearing, velocity/zero/length, scale-relative chords and trig overrides.
- Actual 128×64 greyscale framebuffer and 16×8 grid data, rendered with plain HTML/CSS/JS; forward/back, autoplay, clickable keys/pads, draggable encoders, keyboard focus, search, dense view and themes.
- Four-bar C-major audio: Polyperc bass plus Doubledecker chords on independent channels, captured from SuperCollider through the emulator. Opus and MP3, with a recorded playhead timeline.
- Musical recipes for motif/variation, ghost notes, harmony and polymeter. Related features link to the existing manual.
- A migration proposal. README, AGENTS, cheat sheet and historical citation authority remain intact for pilot review.

The one-command rebuild, pinned voice sources and runtime checkouts are documented in [BUILD.md](BUILD.md). The page is served from the repository root at `/manual/`, compatible with the existing Pages layout. The legacy quick reference and configuration creator were not changed.

## Verification

- Full existing Lua suite: **2,398 passed, zero failures**. Run in an unchanged staging copy named `mosaic` to satisfy the suite's existing relative include convention. Initial staging omitted fixture files; that setup failure is preserved separately.
- Affected Python model, collection, output-profile rejection and suite tests: **44 passed, no skips**.
- Four cited existing Masks cases plus all four authored scenes passed in real-time and controlled-time lanes. Evidence remains separate by lane and retains original identities/hashes.
- Additional cited boundary cases M-MASK-017 and M-MASK-021 passed in both lanes: steps 63/64 clearing/isolation and full-quantisation precedence.
- Authoring proof: changing velocity 50 to 51 in a temporary YAML produced different stable native screen pixels and the exact MIDI velocity 51. The published source was untouched.
- Binding audit: **123 native captures** checked against raw observations, framebuffer/grid hashes and semantic assertions, including the separately registered pilot audio acceptance case.
- Browser acceptance passed at 1440, 768 and 390 pixels: every screen brightness and LED value; all controls and navigation; focus; autoplay; search; density/theme; both audio formats; seek/pause/playhead synchronisation.
- Captured WAV peak **0.114**, RMS **0.0192**, with no digital clipping or silence. Short fades soften the clip boundaries; the two channels use restrained velocity.
- Cleanup receipts show stopped owned native services, no outstanding MIDI notes, released held controls and isolated project data. No emulator process remained after captures. The loopback preview server stays available for review.

Concise receipts are under `evidence/`; immutable raw sessions are under `/home/andy/mosaic-manual-runs/`. Failed development runs were retained rather than overwritten. Passing pilot evidence always leaves `complete_regression_run` false: this is not the exhaustive sharded campaign.

## Findings and limits

See [DISCREPANCIES.md](DISCREPANCIES.md) for source-line evidence: the cheat sheet's old page route, ambiguous channel “global” terminology, chord interval explanation, stale version header and incomplete campaign inventory. A continuous-hold edit/clear boundary was observed without diagnosing or changing Mosaic; the page teaches the passing release/rehold workflow.

MIDI 60 displays as C3 because Mosaic calls norns `musicutil.note_num_to_name(value, true)`; norns appends `floor(note_num / 12 - 2)`. This is octave spelling, not pitch transposition. The page and [VOICES.md](VOICES.md) explain it.

Mosaic reserves an n.b. player for its assigned channel. Reusing Polyperc 1 on another channel was unavailable; the final recording uses one player per channel. The separately researched nb_plyprc variant is outside Mosaic's admitted player names and was rejected. Emplaitress requires MiPlaits and was researched/pinned but not presented as captured. Oilcan is also researched/pinned without claiming native audio evidence for it.

The recorded playhead is observed against host recording time, not sample-accurate or physical-norns calibration. Controlled time validates scene semantics, not DSP or hardware scheduling. PCM and browser checks establish signal integrity and playback; they do not replace an artistic listening judgment or device performance evidence.

## Review decisions before expansion

The inventory is an honest cross-reference: Masks received a semantic audit; other entries are explicitly awaiting that review. The initial Polyend endpoint returned a notice; the official full reference was subsequently recovered and studied. Lines discussions could not be retrieved, so no advice is attributed to their inaccessible contents.

Review the page's interaction, tone, density, musical example and proposed site map before expanding. Then decide whether to undertake the coordinated source-of-truth migration described in [MIGRATION.md](MIGRATION.md). That migration needs all features and coverage tooling updated together. This pilot stops here.

Local commits are unsigned because the configured signing key could not be unlocked in this session. Signing configuration was not changed.
