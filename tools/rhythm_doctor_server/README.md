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

Demucs and Beat This! fetch their own weights on first use, from their
libraries' own versioned homes — Hugging Face and the authors' server — and
cache them. Nothing to do.

LarsNet does not. Its checkpoints are a 562 MB zip on Google Drive and nowhere
else, which is neither durable nor verifiable: the link can change, the file
can be replaced, and a quota-limited error page downloads with a 200 status
and looks like a file. So:

```
git clone https://github.com/polimi-ispl/larsnet
python3 fetch_models.py --larsnet-root ./larsnet
export LARSNET_ROOT=$PWD/larsnet
```

`fetch_models.py` prints the archive's SHA-256; pass it back as `--sha256` to
pin the download, and `--url` to fetch from your own mirror instead. The
archive published in December 2023 is:

```
dd785d77f66413c5acbd3a4cedac02951578c838496d059930c43f159647c907
```

**Running without LarsNet is supported.** `--no-drum-split`, or simply not
setting `LARSNET_ROOT`, keeps the drums stem whole: six lanes instead of ten,
still twice what the device produces. The server logs the reason and says so
on `/v1/health`. Refusing to start over the optional half would let a licence
decide whether the feature exists at all.

`--allow-missing-models` starts anyway and reports the fault on `/v1/health`,
which is useful for checking connectivity from the norns before the models are
in place.

## Windows, start to finish

Verified on Windows 10/11 with Python 3.10 and a norns in access-point mode.
No administrator rights are needed.

### 1. Install

```powershell
mkdir $HOME\rd-server; cd $HOME\rd-server
copy \\wsl.localhost\Ubuntu-20.04\home\<you>\path\to\mosaic\tools\rhythm_doctor_server\*.py .
python -m venv .venv
.\.venv\Scripts\pip install numpy torch demucs beat-this pyyaml
```

Copy the files from wherever the repository lives; the UNC path above is only
what a WSL checkout looks like from Windows.

### 2. Optional: the drum splitter

Without this the server runs in six-lane mode, which is supported and twice
what the device produces on its own. With it you get ten. The checkpoints are
CC BY-NC 4.0: read the licence before building anything commercial on them.

```powershell
git clone https://github.com/polimi-ispl/larsnet $HOME\rd-server\larsnet
.\.venv\Scripts\pip install gdown
.\.venv\Scripts\python fetch_models.py --larsnet-root .\larsnet
$env:LARSNET_ROOT = "$HOME\rd-server\larsnet"
```

`fetch_models.py` prints the archive's SHA-256; pass it back as `--sha256`
next time to pin the download, or point `--url` at your own mirror. Cloning
the repository is not enough on its own -- the weights are a separate
download, and the server says exactly which file is missing if you skip it:

```
WARNING drum splitting unavailable, drums stay one lane:
        larsnet checkpoint missing for kick: ...\pretrained_kick_unet.pth
        -- run fetch_models.py
```

### 3. Run

```powershell
cd $HOME\rd-server
.\.venv\Scripts\python server.py --host 0.0.0.0 --port 8420
```

`--host 0.0.0.0` matters: bound to loopback the norns cannot reach it. Expect

```
INFO listening on http://0.0.0.0:8420/ (ready=True)
```

Windows Firewall prompts on the first run. Allow it on **private** networks,
or the norns connects to nothing and analysis quietly falls back on-device.

### 4. Point the norns at it

PARAMS > MOSAIC > Rhythm Doctor: set **Analysis server** to the PC's address on
the network the norns is on, for example `http://10.42.0.144:8420`, and switch
**Use analysis server** on.

Find that address with `ipconfig`, or in PowerShell:

```powershell
Get-NetIPAddress -AddressFamily IPv4 | Select-Object IPAddress,InterfaceAlias
```

When the norns is acting as the access point, the PC's address is the one on
the norns' subnet (10.42.0.x), not its usual LAN address.

### 5. Check it before recording

```powershell
curl.exe http://10.42.0.144:8420/v1/health
```

You want `"ready": true` and the lane list. If that answers from PowerShell
but captures still come back with three lanes, the firewall is blocking the
norns: three lanes is the on-device fallback, which is what you get whenever
the server cannot be reached.

### Running the server inside WSL instead

The norns cannot reach a WSL2 server directly: WSL2 sits behind its own NAT on
a different subnet, and a norns in access-point mode has no route off its own
hotspot. Forward the port from Windows, in an **elevated** PowerShell:

```powershell
$wsl = (wsl -d Ubuntu-20.04 -- hostname -I).Trim().Split(" ")[0]
netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=8420 connectaddress=$wsl connectport=8420
New-NetFirewallRule -DisplayName "Rhythm Doctor server" -Direction Inbound -Protocol TCP -LocalPort 8420 -Action Allow
```

WSL2's address changes when it restarts, so that rule goes stale; re-run it, or
remove it with:

```powershell
netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=8420
Remove-NetFirewallRule -DisplayName "Rhythm Doctor server"
```

Running natively on Windows avoids all of this.

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
| LarsNet checkpoints | **CC BY-NC 4.0 — non-commercial** |
| LarsNet code | no licence file in the repository |

The LarsNet weights are the drum-splitting half of this server and are
licensed for non-commercial use only; its repository carries no licence file
for the code at all. Read both before building anything commercial on this.
Everything else here is MIT, and the server runs without LarsNet.

Beat This! is used rather than madmom deliberately. madmom's code is BSD but
its model files are CC BY-NC-SA, so commercial use is conditional on permission
from the authors; Beat This! is MIT throughout and is the stronger tracker.
