# Rhythm Doctor remote analysis server

Runs on a PC on the same network as the norns. Mosaic posts a capture and gets
back ten lanes instead of the three the on-device backend can produce.

The on-device DSP path remains the default and the fallback. This server is an
advanced option: when it is unreachable, or slower than the configured timeout,
or returns anything Mosaic does not accept, analysis falls back to the local
backend and the capture still works.

## Why it is better than the local path

The local backend separates drums from a full mix with a partially-fixed NMF
dictionary. It has to decide what a kick is while a bass note is sharing the
same transient, and it cannot name a tom at all. This server runs a separation
model first, so every later stage sees an isolated instrument:

1. **Beat This!** tracks beats and downbeats on the **mix**, before separation.
   It was trained on mixes, and separation is lossy — running it on a drums
   stem discards the harmonic motion that marks a bar line.
2. **htdemucs_6s** splits the mix into drums, bass, other, vocals, guitar and
   piano.
3. **LarsNet** splits the drums stem into kick, snare, toms, hihat and cymbals.
4. Every stem becomes onsets and velocity.

## Lanes

`KICK SNARE TOMS HIHAT CYMBALS BASS GUITAR PIANO VOCALS OTHER`

`OTHER` is demucs' own residual: whatever the five named stems did not claim,
which in practice is synths and pads.

**No pitch, anywhere.** The melodic stems contribute rhythm, not notes. Mosaic's
bank stores a gate and a velocity per cell and has nowhere to put a note
number, so transcribing one would be work whose result is discarded — and it
keeps a transcription model and its licence out of the dependency list.

Velocity is normalised **per stem**, against that stem's own loudest attack in
the capture. A guitar stem's absolute level says nothing about how hard the
guitar was played relative to the kick, and a shared scale would make every
quiet stem produce uniformly weak gates.

## Running it

```
pip install -r requirements.txt
python3 server.py --host 0.0.0.0 --port 8420
```

`--allow-missing-models` starts anyway and reports the fault on `/v1/health`,
which is useful for checking connectivity from the norns before the models are
in place.

## API

`GET /v1/health` — protocol version, readiness, the lane list and its default
gates, and the model identity. Mosaic calls this to lay out the grid before any
capture exists.

`POST /v1/analyse` — body is the capture as a WAV (16-bit, 24-bit or float;
mono or stereo — the device records 24-bit through softcut). An optional
`X-Rhythm-Doctor-Alignment` header carries a player correction as
`{"bpm": 96.0, "origin_sample": 4410}`, which outranks the tracker.

The response is the analysis shape Mosaic's worker already validates, plus
`phrase_start_sample`, `phrase_confidence`, `beat_positions` and
`capture_sha256` so the client can confirm the server analysed the capture it
sent.

Requests are serialised: separation is memory hungry and the norns sends one
capture at a time, so a thread pool would only risk running the machine out of
memory.

## Licences

| model | licence |
| --- | --- |
| htdemucs_6s (Demucs) | MIT |
| Beat This! | MIT — code and published weights |
| LarsNet | check before redistributing |

Beat This! is used rather than madmom deliberately. madmom's code is BSD but
its model files are CC BY-NC-SA, so commercial use is conditional on permission
from the authors; Beat This! is MIT throughout and is the stronger tracker.
