# Device diagnostic journal

2026-09-18: started probe smoke from immutable source `e7edad3`, isolated at
`/tmp/mosaic-foundations-e7edad3/mosaic`, with n.b. pinned to
`503be3ae9a7f4368a8bc35d6081795e0a130cadf`.

The smoke temporarily deploys Mosaic and a copied locks-16 fixture, requests lead
25 ms, and measures two 80-step windows with the probe off, then on. It is not the
qualification campaign. Raw artifacts are retained under
`/home/andy/projects/mosaic-behaviour-runs/foundations-probe-smoke-e7edad3-20260918`.
The wrapper invokes the supplied restoration helper and verifies the active marker,
services, original source fingerprint and five stock bindings after every run.

Restoration status: verified after both runs. The active marker is absent, all four
norns services are active, the original directory mtime and mosaic.lua SHA-256
match the read-only preflight, and all five stock bindings match. No power-cycle,
firmware change, credential change or permanent user parameter change was made.

The runner retained diagnostic recovery/test copies under
`/home/we/.cache/mosaic-real-norns/kept-foundations-e7edad3c-off` and
`/home/we/.cache/mosaic-real-norns/kept-foundations-e7edad3c-pulse-v1`.
These are the only intentional retained device-side artifacts. They were not
deleted or reused. Full host artifacts were also copied into this workspace at
`tests/behaviour/artifacts/lock-lead/e7edad3/legacy-delay-v1/smoke-20260918`.

2026-09-18: started the first interleaved reduced-probe cell from immutable
`cc051cc`, isolated at `/tmp/mosaic-foundations-cc051cc/mosaic` with the same
pinned n.b. gitlink. This cell is locks-16 at 130 BPM and lead 25 ms, ten pairs
of 80-step windows, randomized off/core order and pair seeds frozen before
deployment in `campaign.json`. Raw host output is under
`/home/andy/projects/mosaic-behaviour-runs/probe-overhead-cc051cc-locks25-20260918`.
The wrapper restores and verifies original device state before reporting a result.
The first attempt lost SSH during source transfer before any measurement window.
The first restoration attempt also failed to connect. After reconnecting, the
restoration helper succeeded; the active marker is absent, all four services are
active, original directory mtime/source hash match and all five stock bindings
were verified. No performance result was produced.

At the user's request, restarted the complete cell in a new `-attempt2` artifact
directory with unchanged source, pair seeds, order and thresholds. A compressed
SSH master reduces source-transfer time. Status: attempt 2 in progress;
Attempt 2 also lost SSH during bulk transfer, before any measurement windows.
Restoration through the separate connection succeeded; all services, the original
source fingerprint and absent active marker were verified. A paced 1 MiB upload
also failed on channel 1. No timing failure or passing performance result is
inferred from these transfer failures.

The user explicitly requested changing the hotspot channel and its default.
NetworkManager's Hotspot profile previously had no band and channel 0 (automatic),
with the active radio on channel 1. With playback restored, a detached helper
briefly stopped the hotspot and scanned. Neighbours were observed on channels
1, 2 and 9. A signal-weighted overlap score for candidates 6/11 was 337/57,
respectively. The helper saved band `bg`, channel `11`, and successfully
reactivated the hotspot; the radio reports channel 11, 2462 MHz, width 20 MHz.
This is the user's requested persistent network change, not a temporary test
setting. It does not establish zero interference. The device-side report is
`/home/we/.cache/mosaic-hotspot-channel-20260918.json`.
The subsequent paced 1 MiB hash-only transfer also stalled. Its upload and
report-fetch processes were terminated; it wrote no device files. Channel 11
remains the verified persistent setting, but stable bulk transfer is unresolved.
No performance measurement was started after the channel change.

Further diagnosis on both machines: Windows and WSL large-packet pings lost
5/8 and 6/8 respectively, while Windows 32-byte pings passed 8/8. A 1 MiB
norns-to-host download passed in about 1.2 s, whereas host-to-norns uploads
stalled, including connection-only QoS and smaller-segment checks. The norns
reported strong -35 dBm signal and 1 Mbps received PHY rate; its power-throttle
flags were zero. USB errors mapped to the ESI MIDI interface, not the Wi-Fi
adapter. The PC uses a Ralink RT5370 USB adapter; no driver or power setting was
changed. These observations locate an asymmetric link impairment without proving
a driver fault.

After the user separated the touching antennas, signal was about -55 dBm and
the received PHY rate rose to 13 Mbps. Windows 1400-byte pings then passed 8/8
at 1-2 ms. A deliberately paced 1 MiB upload passed SHA-256 verification in
20.662 s (duration includes intentional pacing, not a throughput benchmark).
This supports antenna placement as a significant factor, not a proven RF
mechanism. Hardware attempt 3 restarted with the same immutable source, seed,
order and gates in a new `-attempt3` host directory. Full source transfer and
manifest verification completed. All 20 windows completed; restoration verified
the absent active marker, four active services, original source fingerprint and
five stock bindings. The cell failed: windows 5, 9, 11, 12 and 13 failed step
jitter; window 13 also failed event timing. Windows 5, 11 and 13 had the probe
off. Every pair failed the combined overhead qualification. All core captures
were complete with zero drops, using 5,840-6,268 of 65,536 rows. These are valid
timing failures, not invalid network captures; none are excluded or rerun away.
Raw artifacts are preserved under
`tests/behaviour/artifacts/lock-lead/cc051cc/legacy-delay-v1/locks25-attempt3`;
compact results and SHA-256 inventory use the `hardware-core-campaign-cc051cc`
prefix in this evidence directory.
