# Per-page miniature animation plan

Status: reviewable design proposal. No sprite or production UI implementation is included. Tone: **cute, playful and gentle**, without exaggerated comedy. Every Mosaic-owned registered page has its own meaningful silhouette, prop and movement; family characters remain recognizable without merely copying the same animation everywhere.

## Placement and space

All artwork is confined to the **top right**, within the actual free title space. Ordinary pages may use up to x96–127, y0–8 (32 × 9). Preferred widths below range from 20 to 30 pixels because several meaningful objects need horizontal room. Actual width is measured after drawing the full title and scope; preferred width is a request, never permission to crop text. Keep a blank pixel between artwork and text. Footers, actions, list rows, exact values and scope do not move or lose space.

Masks C01, Trig Params C02 and dashboards already have right-aligned scope information: their reservation is only x121–127, y0–7 (7 × 8). Those pages therefore use a single compact silhouette, not a downscaled scene of several characters. A 7-pixel bud, note, ring or bead chain has its own designed poses. It must remain legible and distinct at native resolution.

A narrow title slot uses an authored compact variant of the same concept. Do not stretch or blindly downsample a 30 × 44 Doctor into a 7-pixel blob. If the full title leaves no valid room, drawing yields to text; acceptance should find and resolve that collision through an appropriate compact pose, without truncating the title. Retain the original Doctor's head mirror, glasses and coat silhouette in the larger slot, and the garden's flowers/visitor and choir's note-shaped creatures.

## Timing and movement

The production owner confirmed the actual Mosaic transport:

`quarter_beats = (m_clock.get_clock_lattice().transport - 1) / lattice.ppqn`

The lattice initializes/resets/prepares at transport 1; normal PPQN is 96. Read the instance's actual PPQN. When Mosaic is playing, use this actual lattice phase. When Mosaic is stopped, use the **selected norns musical clock** through `clock.get_beats()`; verify its tempo with `clock.get_tempo()`. This is an intentional idle beat preview, independent of sequencer playback, so the Doctor remains gently animated during recording and analysis, which require the Mosaic transport to be stopped. Reading this clock does not start the sequencer or emit notes. Motion Off always displays the meaningful rest pose immediately. Missing, invalid or unavailable clock data also displays rest.

The production owner verified the locally installed norns `core/clock.lua` API at lines 114–120: `get_beats()` delegates to native clock beat time and `get_tempo()` reads native clock tempo. The internal clock reference continues advancing when Mosaic transport stops. A selected external MIDI/Crow clock may legitimately remain still until incoming pulses/acquisition; do not fabricate movement with a wall-clock fallback. The proposal relies on that verified local API, not a new clock implementation.

Do not reuse the old Doctor's wall-clock × analysed-tempo phase, elapsed page time, redraw count or musical RNG. Source choice is deterministic: playing = actual Mosaic lattice; stopped = selected norns clock; Motion Off or invalid source = rest. Quantize whichever valid source is selected into eighth-note poses. Do not maintain an accumulating per-page phase, and do not start/reset the clock or set its tempo when a page opens.

Each animation repeats over the two- or four-quarter-note loop listed below. Poses change on eighth-note subdivisions of the selected musical beat source. A four-beat sequence has eight held poses: rest, prepare, first gesture, return, rest, second gesture, settle, rest. A two-beat sequence has four: rest, gentle gesture, return, rest. The description defines each page's gestures; any values, labels and selection remain fixed. The same selected musical source and phase give the same pose after a page revisit; switching between playing and stopped deterministically selects the corresponding source rather than carrying a page-local phase.

Horizontal motion is small and bounded: up to two pixels in an ordinary slot, one pixel in a 7-pixel slot. Usually the prop or limb moves horizontally while the character's base stays planted; a travelling note or seed may use a bounded back-and-forth path. Avoid a one-direction marquee, jumping across the title, flashing whole areas or an independently running scroll. Quarter-note/eighth-note actions should feel synchronized, not frenetic. Reuse the current 12 FPS art ceiling and draw only when the quantized pose actually changes; no added audio or scheduler work is justified by these decorations.

Original asset sources: `lib/ui_characters.lua` Doctor/window, garden, choir/register and metronome geometry; `lib/rhythm_doctor/dancing_doctor.lua` original four-pose Doctor sprite. Miniatures need faithful authored simplification. `docs/ui-reimplementation/code/visuals.lua` contains keyboard, dial, trig bars, scale ring, arp, voice movement, song slots and swing motifs; reuse their visual vocabulary, not their hardcoded fixture data.

## Registry and route scope

The current registry contains **102 screen IDs**, including **9 native-owned PARAMS entries** and **19 declared visual variants**. There are **93 distinct Mosaic miniature concepts** below. This is an inventory of registered screens, not a claim that 93 public destinations currently exist.

- **Route:** registered candidate for normal/state-dependent presentation. Existing task, grid, action and owner route wiring must be verified when implemented; the plan creates no new menu destination.
- **Variant:** declared visual/specimen state. Implement its motif only if the existing renderer actually presents it; retain its dormant status rather than inventing public navigation to demonstrate the icon.
- **Retired:** M10 is explicitly a compatibility specimen and not reachable from Merge Pitch.
- **Native:** X01–X09 are owned by norns PARAMS. No custom Mosaic animation is proposed on those menus. The relevant Mosaic task page can have its own icon, but that does not make norns' screens Mosaic-owned.

Some original garden/choir artwork was assigned in the registry but never drawn by the live detail branch. Recovering those identities in the header is useful; it must be described as restoration from existing art studies, not proof that those characters were previously visible on every page.

## Page-by-page choreography

All titles below come from the actual current registry. Width × height is the preferred authored size; measured available space remains authoritative. Rest pose is also the Motion Off and unavailable-clock frame.

| ID / title | Route status | Unique miniature | Gentle motion / rest pose | Loop | Preferred space |
|---|---|---|---|---|---|
| C01 NOTE MASKS | Route | Note seed | A single note bud gently opens and closes its leaf. Rest: closed bud. | 2 beats | 7 × 8 |
| C02 TRIG PARAMS | Route | Parameter dial | A tiny knob pointer leans left and returns upright. Rest: upright pointer. | 2 beats | 7 × 8 |
| C03 MEMORY | Route | Memory spool | Two ribbon spools exchange one small loop. Rest: loop resting between spools. | 4 beats | 24 × 8 |
| C04 CLOCK | Route | Clock pendulum | Original metronome gently swings its pendulum. Rest: pendulum centered. | 2 beats | 20 × 8 |
| C05 DEVICE | Route | Device socket | A plug settles into a small socket then rests. Rest: plug seated. | 4 beats | 22 × 8 |
| C06 OUTPUT | Route | Output note | One note breathes with a brightening stem. Rest: note standing upright. | 2 beats | 7 × 8 |
| C07 ASSIGN PARAM | Route | Assignment tag | A blank tag tilts toward its matching pin. Rest: tag hung on pin. | 4 beats | 22 × 8 |
| C08 NOTE SOURCE | Route | Note-source spring | A note rises from a short spring and settles. Rest: note above spring. | 2 beats | 24 × 8 |
| C09 MERGE MODES | Route | Merge braid | Two narrow strands pass into one braided stem. Rest: strands joined. | 4 beats | 28 × 8 |
| S01 SCALE | Route | Scale stair | A small note steps across three ascending rungs. Rest: note on middle rung. | 4 beats | 26 × 8 |
| S02 SCALE CLOCK | Route | Scale-clock dial | Metronome beside a stepped scale turns toward each rung. Rest: pendulum centered beside rungs. | 4 beats | 28 × 8 |
| S03 SCALE OVERVIEW | Route | Scale rosette | A compact seven-petal rosette softly opens. Rest: rosette open. | 4 beats | 7 × 8 |
| S04 SCALE SOURCE | Route | Scale root | A rooted leaf stretches upward and settles. Rest: leaf over visible root. | 4 beats | 7 × 8 |
| S05 APPLY SCALE | Route | Scale stamp | A scale-shaped seal lowers toward a small page then returns. Rest: seal hovering above page. | 4 beats | 26 × 8 |
| P01 PATTERN TRIG | Route | Trig stepping stones | A rounded seed steps between four short pulse stones. Rest: seed on first stone. | 4 beats | 28 × 8 |
| P02 TRIG OPTIONS | Route | Pattern toggle | A pair of tiny switches nods alternately. Rest: switches level. | 2 beats | 22 × 8 |
| P03 PATTERN NOTE | Route | Note caterpillar | A note-shaped creature follows a gentle three-step pitch path. Rest: creature on middle step. | 4 beats | 28 × 8 |
| P04 PATTERN VELOCITY | Route | Velocity reeds | Three reeds breathe with different heights. Rest: reeds resting. | 4 beats | 24 × 8 |
| P05 CHANNEL VIEW | Route | Channel windows | A small light travels across three framed windows. Rest: light in center window. | 4 beats | 28 × 8 |
| A01 SLOT SETUP | Route | Song-slot envelope | A folded slot card gently opens its flap. Rest: card closed. | 4 beats | 24 × 8 |
| A02 GLOBAL FEEL | Route | Global-feel ribbon | Metronome ticks beside a ribbon that subtly bends. Rest: pendulum centered ribbon straight. | 4 beats | 30 × 8 |
| A03 SONG PLAYBACK | Route | Song beads | Three linked beads brighten in sequence. Rest: middle bead resting bright. | 4 beats | 7 × 8 |
| X01 PROJECT | Native | norns owns this screen | No custom animation | — | — |
| X02 LOAD PROJECT | Native | norns owns this screen | No custom animation | — | — |
| X03 SAVE PROJECT | Native | norns owns this screen | No custom animation | — | — |
| X04 SEQUENCER OPTIONS | Native | norns owns this screen | No custom animation | — | — |
| X05 QUANTISER OPTIONS | Native | norns owns this screen | No custom animation | — | — |
| X06 MIDI MAPPING | Native | norns owns this screen | No custom animation | — | — |
| X07 DEVICE PARAMS | Native | norns owns this screen | No custom animation | — | — |
| X08 CLOCK AND MODS | Native | norns owns this screen | No custom animation | — | — |
| F01 CLOCK * | Variant | Pending clock | Metronome hand approaches a small waiting dot. Rest: hand centered dot steady. | 4 beats | 24 × 8 |
| F02 CLOCK | Variant | Clock lantern | A tiny lantern brightens on the beat. Rest: lantern softly lit. | 2 beats | 7 × 8 |
| F03 GRID OFFLINE | Variant | Resting grid cable | A loose cable makes a slight settling curve. Rest: cable resting disconnected. | 4 beats | 26 × 8 |
| F04 LOAD REJECTED | Variant | Closed project gate | A small closed gate breathes around a stationary latch. Rest: gate closed. | 4 beats | 24 × 8 |
| F05 MASKS | Variant | Mask veil | A light veil lifts above a tiny note and settles. Rest: veil hanging beside note. | 4 beats | 24 × 8 |
| F06 MASKS | Variant | Held mask pin | A note leaf sways while its pin stays fixed. Rest: leaf pinned. | 2 beats | 24 × 8 |
| F07 RECORDING | Variant | Recording seed | A compact recording ring expands one pixel and returns. Rest: ring at rest. | 2 beats | 7 × 8 |
| F08 PARAMETER SLIDE | Variant | Slide bridge | A bead glides up a short diagonal bridge then rests. Rest: bead at bridge base. | 4 beats | 28 × 8 |
| H01 VOICE LEADING | Route | Leading choir | Original note creatures take one small shared step. Rest: three creatures resting. | 4 beats | 28 × 8 |
| H02 REGISTER | Route | Register ladder | Original register creature climbs one rung and returns. Rest: creature on middle rung. | 4 beats | 24 × 8 |
| H03 BASS | Route | Bass anchor | A bass note creature nods above a fixed anchor. Rest: anchor grounded creature upright. | 2 beats | 24 × 8 |
| H04 ENSEMBLE | Route | Ensemble circle | Four small note heads breathe together around a center. Rest: heads evenly spaced. | 4 beats | 28 × 8 |
| H05 VOICE MOVEMENT | Route | Voice-movement trail | Two creatures exchange neighboring perches along a short trail. Rest: creatures on their own perches. | 4 beats | 28 × 8 |
| H06 NO VOICING | Route | Waiting choir | Two original note creatures wait with a soft alternating nod. Rest: creatures at rest gap between them. | 4 beats | 24 × 8 |
| N01 CHANNEL TASKS | Route | Channel lanterns | Three lanterns gently tilt toward their shared stem. Rest: lanterns hanging straight. | 4 beats | 28 × 8 |
| N02 SCALE TASKS | Route | Scale book leaf | A leaf-shaped bookmark sways above an open book. Rest: bookmark upright. | 4 beats | 26 × 8 |
| N03 PATTERN TASKS | Route | Pattern seed tray | A seed rolls gently between three tray compartments. Rest: seed in center compartment. | 4 beats | 28 × 8 |
| H07 MEMBERS | Route | Member garland | Connected note creatures nod one after another. Rest: garland hanging level. | 4 beats | 28 × 8 |
| H08 VOICING RULES | Route | Voicing compass | A small compass needle follows two choir perches. Rest: needle centered. | 4 beats | 24 × 8 |
| H09 ENTRY / FAILURE | Route | Entry doorway | A note creature leans toward a doorway then returns. Rest: creature beside doorway. | 4 beats | 26 × 8 |
| H10 HARMONIC SOURCE | Route | Harmonic well | A note creature lifts a small note from a well. Rest: creature and note at rim. | 4 beats | 28 × 8 |
| H11 TONE MAP | Route | Tone-map tiles | Original choir creature taps three tiny tone tiles in order. Rest: creature beside center tile. | 4 beats | 28 × 8 |
| H12 PATTERN MOVEMENT | Variant | Pattern-movement wing | A note with a small wing breathes upward. Rest: wing resting. | 2 beats | 7 × 8 |
| H13 PATTERN BASS | Variant | Pattern-bass root | Register creature settles beside a rooted note. Rest: creature grounded beside root. | 4 beats | 26 × 8 |
| C10 CHORD TIMING | Route | Chord-time chimes | Three hanging note chimes sway one after another. Rest: chimes vertical. | 4 beats | 28 × 8 |
| P06 TRIG ALGORITHM | Route | Algorithm loom | A little loom alternates two threads over a fixed bar. Rest: threads level. | 4 beats | 28 × 8 |
| P07 PAINT PREVIEW | Route | Paint brush seed | A tiny brush nods over a seed mark. Rest: brush upright. | 2 beats | 7 × 8 |
| P08 TRIG STEP EDIT | Route | Step pebble | A marked pebble rises one pixel then settles. Rest: pebble grounded. | 2 beats | 7 × 8 |
| N05 SONG TASKS | Route | Song chapter tabs | A small bookmark passes between three chapter tabs. Rest: bookmark on middle tab. | 4 beats | 28 × 8 |
| C11 DEVICE CHANGE | Route | Device-change parcel | A plug peeks from a small open parcel then settles. Rest: plug seated in parcel. | 4 beats | 24 × 8 |
| C12 MASK DETAIL | Route | Mask magnifier | A small lens tilts over a note leaf. Rest: lens resting over leaf. | 4 beats | 24 × 8 |
| C13 TRIG DETAIL | Route | Parameter-detail lens | A pointer moves beneath a lens-shaped dial rim. Rest: pointer upright under lens. | 2 beats | 24 × 8 |
| R01 RHYTHM DR | Route | Doctor greeting | Original Doctor dude gives a small nod beside his mirror. Rest: doctor upright mirror visible. | 2 beats | 20 × 8 |
| R02 CAPTURE | Route | Doctor listening | Doctor leans toward a small recording shell. Rest: doctor beside shell. | 4 beats | 26 × 8 |
| R03 CANCEL TAKE? | Route | Doctor take card | Doctor holds a take card that gently tilts. Rest: card level in hands. | 4 beats | 26 × 8 |
| R04 ANALYSIS | Route | Doctor notes | Doctor follows three small analysis dots with a subtle head nod. Rest: doctor facing dots. | 4 beats | 28 × 8 |
| R05 WINDOW | Route | Doctor window | Doctor leans into a little window frame and returns. Rest: doctor centered in frame. | 4 beats | 28 × 8 |
| R06 ALIGNMENT | Route | Doctor alignment | Doctor moves a small ruler beside two staggered marks. Rest: ruler aligned with marks. | 4 beats | 28 × 8 |
| R07 ALIGNMENT | Route | Doctor aligned markers | Doctor nods beside two matched marker flags. Rest: flags lined up doctor upright. | 4 beats | 28 × 8 |
| R08 PAINT | Route | Doctor brush | Doctor gently raises a small paint brush. Rest: brush held at rest. | 2 beats | 24 × 8 |
| R09 PAINT | Route | Doctor painted bed | Doctor tends a small dotted paint bed with a hand nod. Rest: doctor beside planted dots. | 4 beats | 28 × 8 |
| R10 CLEAR BANK? | Route | Doctor bank box | Doctor holds a closed bank box whose handle tilts. Rest: box closed in hands. | 4 beats | 26 × 8 |
| R11 STOP SEQUENCER | Route | Doctor rest stool | Doctor sits beside a stationary stop pebble and breathes. Rest: doctor seated pebble stationary. | 4 beats | 28 × 8 |
| R12 NO BANK | Route | Doctor empty tray | Doctor looks into a small empty tray and returns upright. Rest: doctor beside empty tray. | 4 beats | 26 × 8 |
| R13 BANK LANES | Route | Doctor lane ribbons | Doctor follows three parallel ribbons with a gentle nod. Rest: ribbons parallel doctor upright. | 4 beats | 30 × 8 |
| R14 SETUP LIMITS | Route | Doctor limit fence | Doctor adjusts a short measuring fence by one pixel. Rest: fence steady doctor upright. | 4 beats | 28 × 8 |
| R15 BROWSE | Route | Doctor browsing leaf | Doctor turns one small leaf-shaped page. Rest: page half open. | 4 beats | 26 × 8 |
| M01 CHANNEL | Route | Garden gate | Original garden visitor peeks above a little garden gate. Rest: visitor at gate. | 4 beats | 26 × 8 |
| M02 MERGE SHAPE | Route | Garden shape | Original two-flower garden gently sways as a whole. Rest: flowers upright. | 4 beats | 30 × 8 |
| M03 RHYTHM | Route | Rhythm sprouts | Three sprouts nod successively over a fixed soil line. Rest: sprouts upright. | 4 beats | 28 × 8 |
| M04 MERGE SHAPE | Variant | Growing shape bed | Two original flowers settle around a newly raised middle sprout. Rest: middle sprout standing. | 4 beats | 30 × 8 |
| M05 MERGE RESULT | Route | Merge-result basket | A flower seed settles into a small woven basket. Rest: seed in basket. | 4 beats | 24 × 8 |
| M06 PHRASE | Route | Phrase vine | A short vine unfurls one curved leaf then rests. Rest: leaf open. | 4 beats | 28 × 8 |
| M07 PITCH | Route | Pitch vine ladder | A flower head climbs three vine rungs gently. Rest: flower on middle rung. | 4 beats | 26 × 8 |
| M08 RHYTHM | Variant | Rhythm marker leaf | A leaf nods beside a stationary anchor stone. Rest: leaf upright anchor fixed. | 2 beats | 26 × 8 |
| M09 MERGE SHAPE | Variant | Saved garden pot | A small potted flower breathes while its rim stays fixed. Rest: flower upright in pot. | 4 beats | 24 × 8 |
| M10 HARMONY | Retired | Harmony graft | Two leaves on a retired garden graft sway together. Rest: leaves joined on stem. | 4 beats | 28 × 8 |
| M11 MERGE SHAPE | Variant | Garden tool rest | A tiny rake rests beside two established flowers and tilts. Rest: rake grounded flowers upright. | 4 beats | 30 × 8 |
| H14 HARMONY | Variant | Settled choir arch | Two choir creatures nod beneath a joined arch. Rest: arch complete creatures upright. | 4 beats | 28 × 8 |
| H18 EVENT RESULT | Variant | Event-result note | A choir creature releases a small note that settles beside it. Rest: note resting beside creature. | 4 beats | 24 × 8 |
| H15 EVENT RESULT | Variant | Quiet choir pause | A choir creature breathes beside a small rest mark. Rest: creature upright rest mark fixed. | 4 beats | 24 × 8 |
| H16 EVENT RESULT | Variant | Local-scale path | A choir creature steps beside a split leafy path. Rest: creature at junction. | 4 beats | 28 × 8 |
| H17 DELETE GROUP? | Route | Group garland clasp | A closed clasp tilts between two choir creatures. Rest: clasp closed. | 4 beats | 28 × 8 |
| X09 LOCK LEAD TIME | Native | norns owns this screen | No custom animation | — | — |
| M12 AMOUNT DETAIL | Route | Amount watering can | A small watering can nods toward three sprouts. Rest: can upright sprouts stationary. | 4 beats | 28 × 8 |
| M13 PITCH TARGET | Route | Pitch-target flower | A flower head leans toward one of three fixed leaves. Rest: flower centered. | 4 beats | 26 × 8 |
| M14 MERGE REASON | Route | Merge-reason seed | A small split seed opens and closes gently. Rest: seed showing its seam. | 2 beats | 7 × 8 |
| H19 RESET TONE MAP? | Route | Tone-map slate | A choir creature holds a blank small slate and nods. Rest: slate level. | 4 beats | 24 × 8 |
| R16 CANCEL CORRECTION? | Route | Doctor correction leaf | Doctor holds a softly bent correction leaf that straightens. Rest: leaf level in hands. | 4 beats | 28 × 8 |
| M15 FRAGMENTS | Route | Fragment leaves | Three small detached leaves settle into a short vine pattern. Rest: leaves aligned. | 4 beats | 28 × 8 |
| M16 INTERLOCK | Route | Interlock stems | Two curved stems lean into a gentle alternating link. Rest: stems linked. | 4 beats | 28 × 8 |
| M18 STRUCTURE | Route | Structure trellis | A tiny vine climbs a fixed three-post trellis. Rest: vine at middle post. | 4 beats | 28 × 8 |

## Review and implementation gates

First approve native-resolution drawings and four/eight pose strips for a varied pilot: C01 (7-pixel bud), C04 (metronome), C07 (tag), S01 (stair), R01/R02/R05 (distinct Doctor props), M02/M03/M15 (distinct plants) and H01/H02/H03 (choir/register/bass). Compare side by side so differences are visible without title text, then extend the registry mapping. Avoid rolling out an identical family glyph with only its name changed.

The machine-readable companion `page-animation-map.json` preserves the exact inventory, spec hash, unique concepts, movements, rest poses, musical loop lengths, preferred widths, original art family and route-status caveats. It is proposal data, not a runtime spec, and must not be silently imported as active navigation.

Acceptance must establish: correct unique motif for each rendered screen; no pixel outside its reservation; no title/scope/list/footer change; exact pose at controlled musical phases; immediate rest when Motion Off or clock data is unavailable, plus gentle selected-clock idle animation while stopped; restart/reset reproducibility; tempo changes following transport; internal/external clock compatibility; page re-entry at the same phase; no MIDI/grid/random-state changes; and no busy redraw when Motion Off or the selected source has not advanced; stopped internal-clock preview redraws only on a changed pose. Add actual-app public-input screen checks with meaningful musical output unchanged, plus relevant real-time coverage and existing full Lua validation under repository instructions. Rebuild affected manual framebuffer/grid scenes and procedures from the new candidate, retaining old source identity and failure evidence.

No new public route, beat counter, sequencer callback, random source or fictitious instrument feedback is required. These are decorations informed by page purpose; a breathing recording ring is not an input meter and a three-bead song icon does not report the real number of song slots.
