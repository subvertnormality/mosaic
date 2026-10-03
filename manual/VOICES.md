# Voicing guide and reproducibility

Exact commits are in voices.lock.json and tests/behaviour/output-profiles.json. These are independent upstream checkouts; Mosaic does not patch the voices or the emulator.

| Voice | Controls and character | Recipe | Pilot status |
|---|---|---|---|
| [Doubledecker](https://github.com/sixolet/doubledecker) | Two CS-80-inspired layers, independent amplitude/filter envelopes, high/low-pass filters, layer levels, spread, velocity and pressure routing. Source: lib/mod.lua:187–205; lib/doubledecker.sc:60 onward. | Quiet C-major chords; soften attack, avoid very long releases when attacks stack. | Existing nb-audio revision retained; used for pilot chords. |
| [Polyperc / nb_polyperc](https://github.com/dstroud/nb_polyperc) | The n.b. form of the norns PolyPerc engine: decay, cutoff, tracking, pulse width, amplitude, gain, pan and effect sends (lib/mod.lua:37–45). One player is enabled by default, registered as Polyperc 1. | A short filtered bass and upper plucks with space between attacks. Mosaic assigns this player to one channel; enable another upstream player before trying to assign it elsewhere. | Supported by Mosaic; pinned at 714bd0c5. |
| [Oilcan](https://github.com/zjb-s/oilcan) | Monophonic digital FM percussion; seven timbres, pitch sweep, attack/release, modulator ratio/level, feedback, fold, headroom, gain and clean level. Source README, lib/mod.lua:339. Notes choose timbre with (note−1) modulo 7. | Put kick/snare/hat timbres on separate attacks; kit note numbers choose sounds rather than harmonic pitches. Reduce level before pushing gain. | Pinned in manual-oilcan; not claimed as captured in the duo example. |
| [Emplaitress](https://github.com/sixolet/emplaitress) | Plaits models, harmonics, timbre, morph, percussive/ADSR style, LPG colour, aux mix and amplitude. Source lib/mod.lua:65–85; lib/emplaitress.sc:15. Requires the MiPlaits SuperCollider UGen. README describes four copies; this pinned Lua source registers six. | One restrained lead or a percussive model; choose a model before tuning morph/timbre. Avoid extremely rapid chords until device performance is checked. | Pinned in manual-emplaitress; plugin availability must be checked before using it. |

The upstream [Oilcan discussion](https://llllllll.co/t/oilcan-percussion-co/60754) is linked by its [community entry](https://norns.community/oilcan/). Lines returned an access/cache error during research, so no discussion advice is attributed to it. Searches did not retrieve primary dedicated Lines threads for the other three voices. Their pinned source and repository docs supply the guide; further community review remains open.

The short pilot uses two independent Mosaic channels and two of the permitted voices. It uses default upstream timbres and deliberate low note velocities, not replacement browser synthesis. Audio is captured from the live emulator into WAV then encoded to Opus/OGG and MP3. Data stores observed playhead frames against recording time. Host/JACK timing is not physical-norns calibration.

## Pitch spelling

Mosaic calls `musicutil.note_num_to_name(value, true)` in `lib/pages/channel_edit_page/channel_edit_page_ui.lua:189`. The [official norns implementation](https://github.com/monome/norns/blob/14bbeae8646c6717f6bb44c8cd60250bf94b6042/lua/lib/musicutil.lua#L617-L620) in `lua/lib/musicutil.lua:617–620` appends `floor(note_num / 12 - 2)`, so MIDI 60 is C3 and MIDI 0 is C−2. This is a display convention, not a transposition. Many instruments call the same MIDI note C4. Captions use the names displayed on norns; scene MIDI oracles retain numeric pitches so octave-label differences cannot change the composition.

## Rejected alternative

The separately researched [sonocircuit/nb_plyprc](https://github.com/sonocircuit/nb_plyprc) is a six-voice variant registered as plyprc. Mosaic deliberately admits only its tested note-player names (lib/devices/device_descriptors.lua:8,53), so this variant does not appear in its picker. It is not used or patched for the pilot. The failed picker run is preserved at `/home/andy/mosaic-manual-runs/0eb2e3088cac4ef68b648fdc47d0bb88/report.json`.

The attempted third channel reused Polyperc 1, which Mosaic removes from other channels’ device pickers after assignment. The preserved failed run is `462dde12a53d47078e189c5ad21f9424`. The final duo uses one player per channel instead.
