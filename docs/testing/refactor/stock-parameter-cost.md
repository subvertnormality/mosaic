# Stock parameter resolution cost

Candidate against f3e788d: reuse callbacks in the runtime bridge and pass channel
and step explicitly into the existing resolver. Remove the second formatting of
an already-formatted control ID. No parameter values or device handles are cached.

Precedence remains first matching assignment, step lock/off handling, assigned
live value, then fallback. Fallback still reads the current value before looking
up its control, and consults the default only for a truthy value. The channel
number comes from the model's channel object, whose number matches its index.

## Measured local benefit

Evidence root: `/home/andy/projects/mosaic-behaviour-runs`.
`stock_bridge_benchmark.lua` extracts the actual bridge and resolver with
representative parameter/program dependencies. Five alternating500000-call
rounds rotate equally through fallback, assigned and step-lock paths. Median
CPU cost592.7ns becomes373.0ns (37.1% lower). A separate100000-call GC-stopped
sample measures280.013B/call before and0.012B/call after (measurement floor).
All checksums match. This is a bridge microbenchmark, not native or hardware speedup.
Raw output: `stock_bridge_benchmark_results.txt`; summary:
`stock_bridge_benchmark_summary.txt`; source hashes and artifacts:
`stock_bridge_benchmark_artifacts.sha256` (verified).

## Correctness validation

All1546 Lua tests passed, including stock-parameter precedence and sentinel
contracts. Six inventory/name/syntax checks passed. Existing M-PARAM-036
(stock/None assignment, zero/tie/127 values and channel isolation) passed:

- Controlled: `f3e2fb5bff224f1c92c85709d324c3c8/manifest.json`.
- Real time: `53aa7face62a41738ad8a0d755f6f74e/manifest.json`.

A read-only semantic review found no new state lifetime or lazy-default issue.

## Native comparison pending

Uninstrumented baseline worktree `/home/andy/projects/mosaic-perf-baseline-r13`
at f3e788d uses the original image
`sha256:38b516ef4a8e7f85355da8d94d8f6f21c007b6a8d47fa829a8fc9039c01eea91`.
PERF-003 workload:16channels,8seconds,0.5CPU quota,768MiB,cpuset0. Baseline output:
`r13-stock-resolver-native-before-01`. Candidate will use the same workload and
image after baseline completes. Native improvement and timing acceptance remain
unproven; existing runtime timing findings are separate.
