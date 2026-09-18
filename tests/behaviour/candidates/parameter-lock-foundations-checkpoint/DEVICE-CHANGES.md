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
