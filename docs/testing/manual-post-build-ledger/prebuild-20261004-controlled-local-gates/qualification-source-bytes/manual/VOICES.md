# Voicing guide and reproducibility

Exact commits are in voices.lock.json and tests/behaviour/output-profiles.json. These are independent upstream checkouts; Mosaic does not patch the voices or the emulator.

| Voice | Controls and character | Recipe | Pilot status |
|---|---|---|---|
| [Doubledecker](https://github.com/sixolet/doubledecker) | Two CS-80-inspired layers, independent amplitude/filter envelopes, high/low-pass filters, layer levels, spread, velocity and pressure routing. Source: lib/mod.lua:187–205; lib/doubledecker.sc:60 onward. | Assign Doubledecker to a chord channel. Add 3rd and 5th chord masks, then set a lower velocity than the bass channel. Reduce release if consecutive chords overlap too much. | Existing nb-audio revision retained; used for pilot chords. |
| [Polyperc / nb_polyperc](https://github.com/dstroud/nb_polyperc) | The n.b. form of the norns PolyPerc engine: decay, cutoff, tracking, pulse width, amplitude, gain, pan and effect sends (lib/mod.lua:37–45). One player is enabled by default, registered as Polyperc 1. | Assign Polyperc 1 to the bass channel. Set MIDI 48 and 55 with note masks and use short note lengths. Mosaic removes an assigned player from the other channel pickers; a second channel requires another available player. | Supported by Mosaic; pinned at 714bd0c5. |
| [Oilcan](https://github.com/zjb-s/oilcan) | Monophonic digital FM percussion; seven timbres, pitch sweep, attack/release, modulator ratio/level, feedback, fold, headroom, gain and clean level. Source README, lib/mod.lua:339. Notes choose timbre with (note−1) modulo 7. | Assign Oilcan 1 to the percussion channel. Use MIDI 36, 37 and 38 to select timbres 1, 2 and 3 in the default kit. Change LEVEL to adjust output volume; GAIN changes the signal level into the soft-clipping stage. | Captured in the Oilcan pocket and three-player examples; not used in the Masks duo. |
| [Emplaitress](https://github.com/sixolet/emplaitress) | Plaits models, harmonics, timbre, morph, percussive/ADSR style, LPG colour, aux mix and amplitude. Source lib/mod.lua:65–85; lib/emplaitress.sc:15. Requires the MiPlaits SuperCollider UGen. The pinned Lua mod registers four players. | Select a Plaits model first. Adjust harmonics, timbre and morph to change its sound, then choose percussive or ADSR envelopes. Native capture requires a runtime with the MiPlaits UGen installed. | Pinned in manual-emplaitress; MiPlaits is absent from the installed capture runtime, so no captured sound is claimed. |

The upstream [Oilcan discussion](https://llllllll.co/t/oilcan-percussion-co/60754) is linked by its [community entry](https://norns.community/oilcan/). Lines returned an access/cache error during research, so no discussion advice is attributed to it. Searches did not retrieve primary dedicated Lines threads for the other three voices. Their pinned source and repository docs supply the guide; further community review remains open.

The Masks example assigns Polyperc 1 and Doubledecker to two separate Mosaic channels. It uses the upstream default timbres and the velocities listed in its authoring data. Audio is captured from the live emulator into WAV then encoded to Opus/OGG and MP3. Data stores observed playhead frames against recording time. Host/JACK timing is not physical-norns calibration.

## Pitch spelling

Mosaic calls `musicutil.note_num_to_name(value, true)` in `lib/pages/channel_edit_page/channel_edit_page_ui.lua:189`. The [official norns implementation](https://github.com/monome/norns/blob/14bbeae8646c6717f6bb44c8cd60250bf94b6042/lua/lib/musicutil.lua#L617-L620) in `lua/lib/musicutil.lua:617–620` appends `floor(note_num / 12 - 2)`, so MIDI 60 is C3 and MIDI 0 is C−2. This is a display convention, not a transposition. Many instruments call the same MIDI note C4. Masks captions use the names displayed by that control; scene MIDI oracles retain numeric pitches so octave-label differences cannot change the composition. This convention is specific to the Masks formatter: the separate Fixed Note device control builds labels from MIDI 0 as C0 (`lib/devices/device_map.lua:26–38`), making MIDI 60 C5 there. Read the number and the control together rather than assuming a universal octave label across Mosaic.

## Rejected alternative

The separately researched [sonocircuit/nb_plyprc](https://github.com/sonocircuit/nb_plyprc) is a six-voice variant registered as plyprc. Mosaic deliberately admits only its tested note-player names (lib/devices/device_descriptors.lua:8,53), so this variant does not appear in its picker. It is not used or patched for the pilot. The failed picker run is preserved at `/home/andy/mosaic-manual-runs/0eb2e3088cac4ef68b648fdc47d0bb88/report.json`.

The attempted third channel reused Polyperc 1, which Mosaic removes from other channels’ device pickers after assignment. The preserved failed run is `462dde12a53d47078e189c5ad21f9424`. The final duo uses one player per channel instead.

## Listening examples

`audio-scenes.yaml` defines five four-bar examples at 90 BPM. Oilcan pocket, Bass and intervals, and Three-player sequence are independent compositions for trying the voices. Their lower velocities and fixed note masks are not demonstrations of the ghost-note or scale-slot lessons.

Adding a Ghost Note uses Oilcan 1. The main attacks on steps 1, 5, 9 and 13 have velocity 90. The first two bars contain only those attacks. The last two bars also contain step 12 at velocity 35, selecting MIDI 38. Listen for the additional quieter attack before step 13. All lengths are half a beat.

Changing Harmony with Scale Slots assigns Doubledecker to the upper pattern and Polyperc 1 to the bass pattern. Note masks remain X. Bars 1–2 use C Major in slot 1; the public scale-slot control and K3 apply D Major in slot 2 before bar 3. The upper notes change from MIDI 60/62 to 62/64; the bass changes from 48/55 to 50/57. The upper velocity is 80 except the final attack at 50; the bass velocity is 60. This listening comparison has its own levels and half-beat lengths, separately from the continuous course project.

The two lesson comparisons require literal MIDI pitches, velocities, lengths and musical onset times in both real-time and controlled-time sessions. Their audio sessions add silent public MIDI witness channels, so the same-session note receipts and the native WAV start timestamp locate the declared PCM windows. The ghost-note check measures added activity in the last two bars. The separate Polyperc recording checks the C and D bass pitches in fixed note interiors. These checks do not calibrate physical hardware latency or arbitrary mixed-instrument pitch.

Every assigned player is recorded on its own in a fresh isolated session before the mix can publish. Five mixes and nine solos require fourteen native DSP sessions, plus four MIDI qualification sessions for the lessons. Digital integrity checks reject near clipping, incorrect duration and an unsettled final tail. Timeline frames are actual framebuffer/grid observations sampled against the native recording epoch.

Emplaitress remains unavailable in the installed capture runtime because MiPlaits is absent. Its documented controls and immutable source pin remain available for a runtime that provides the UGen. No substitute sound is rendered.

`tools/manual_audio.audit_publication()` rechecks the immutable authoring/tool/schema baseline, original native WAV hashes, literal lesson output, fixed PCM interiors, headroom and tails, session cleanup, solo contribution and every timeline/frame binding. The original three-example publication and its metadata overlays remain preserved independently; a fresh five-example publication must pass its own complete inventory.
