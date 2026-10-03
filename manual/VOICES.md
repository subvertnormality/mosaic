# Voicing guide and reproducibility

Exact commits are in voices.lock.json and tests/behaviour/output-profiles.json. These are independent upstream checkouts; Mosaic does not patch the voices or the emulator.

| Voice | Controls and character | Recipe | Pilot status |
|---|---|---|---|
| [Doubledecker](https://github.com/sixolet/doubledecker) | Two CS-80-inspired layers, independent amplitude/filter envelopes, high/low-pass filters, layer levels, spread, velocity and pressure routing. Source: lib/mod.lua:187–205; lib/doubledecker.sc:60 onward. | Quiet C-major chords; soften attack, avoid very long releases when attacks stack. | Existing nb-audio revision retained; used for pilot chords. |
| [Polyperc / nb_plyprc](https://github.com/sonocircuit/nb_plyprc) | Six voices, pulse width, cutoff, resonance, decay, spread, glide and modulation depth. Source lib/mod.lua:39–85. This is the explicit six-voice n.b. variant, registered as Plyprc. | Filtered bass below middle C; short upper plucks with space between attacks. Bass and lead share the six-voice pool. | Used alongside Doubledecker; not the unrelated built-in PolyPerc engine. |
| [Oilcan](https://github.com/zjb-s/oilcan) | Monophonic digital FM percussion; seven timbres, pitch sweep, attack/release, modulator ratio/level, feedback, fold, headroom, gain and clean level. Source README, lib/mod.lua:339. Notes choose timbre with (note−1) modulo 7. | Put kick/snare/hat timbres on separate attacks; kit note numbers choose sounds rather than harmonic pitches. Reduce level before pushing gain. | Pinned in manual-oilcan; not claimed as captured in the duo example. |
| [Emplaitress](https://github.com/sixolet/emplaitress) | Plaits models, harmonics, timbre, morph, percussive/ADSR style, LPG colour, aux mix and amplitude. Source lib/mod.lua:65–85; lib/emplaitress.sc:15. Requires the MiPlaits SuperCollider UGen. README describes four copies; this pinned Lua source registers six. | One restrained lead or a percussive model; choose a model before tuning morph/timbre. Avoid extremely rapid chords until device performance is checked. | Pinned in manual-emplaitress; plugin availability must be checked before using it. |

The upstream [Oilcan discussion](https://llllllll.co/t/oilcan-percussion-co/60754) is linked by its [community entry](https://norns.community/oilcan/). Lines returned an access/cache error during research, so no discussion advice is attributed to it. Searches did not retrieve primary dedicated Lines threads for the other three voices. Their pinned source and repository docs supply the guide; further community review remains open.

The short pilot uses several Mosaic channels and two of the permitted voices. It uses default upstream timbres and deliberate low note velocities, not replacement browser synthesis. Audio is captured from the live emulator into WAV then encoded to Opus/OGG and MP3. Data stores observed playhead frames against recording time. Host/JACK timing is not physical-norns calibration.

## Pitch spelling

The norns musicutil naming used here labels MIDI 60 as C3 (MIDI 0 is C−2). Many instruments call the same MIDI note C4. Captions use the names displayed on norns; scene MIDI oracles retain numeric pitches so octave-label differences cannot change the composition.
