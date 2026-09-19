# R07 effective-length baseline

Measured on WSL host with Lua 5.3 at Mosaic `ceb52f0`; these are helper CPU timings,
not physical-norns performance or whole-sequencer timing claims. Production is unchanged.
Reproduce from the repository root:

`lua5.3 docs/testing/refactor/benchmarks/effective-lengths.lua`

The standalone benchmark embeds the current helper and a linear backward candidate.
10,000 seeded inputs compare all 64 outputs (negative/zero/fractional/long lengths,
sparse trigs, and wraparound). Differential agreement is evidence of preservation,
not the sole oracle for accepting production changes.

30,000 calls per scenario, second measurement:

| Scenario | Current seconds | Candidate seconds | Speed ratio |
|---|---:|---:|---:|
| Dense one-step | 0.068043 | 0.074616 | 0.91x |
| One long trig | 0.103960 | 0.066220 | 1.57x |
| Dense long notes | 0.243100 | 0.103805 | 2.34x |
| Fractional lengths | 0.076333 | 0.061463 | 1.24x |
| Sparse long notes | 0.112590 | 0.062548 | 1.80x |

Decision: do not promote this candidate from microbenchmarks alone. Measure full
merge cost before accepting its dense-short overhead; use existing independent
length/merge oracles for validation. No cache or source revision is introduced.

The merge calculation currently sorts values before summing. Replacing it with a
single-pass sum changes floating-point accumulation order; preserve that ordering
unless the supported numeric domain proves equivalence. This is an evidence-based
constraint on R07's proposed sort removal, not permission to change musical results.

Next: benchmark complete merge separately, including priority-source duplicate
length resolution, then select the smallest measured improvement and run existing
length/merge behaviour and unit guards.

## Adopted linear resolver

After measuring complete merges, adopted the backward nearest-trig resolver in
`pattern.lua`. No persistent cache, source revision, merge order, sorted summation,
mask precedence or output scheduling changes. This bounds the source-length scan
linearly rather than scanning forward separately for every sustained trig.

The final `benchmarks/full-merge.lua` loads the frozen `e5a16bb` production merge
and current production merge, compares complete outputs, and measures 400 calls
per workload. Results are host microbenchmarks, not a Norns latency guarantee.
Long-note full merges improve by 2-13% in the final sample. Dense-short samples
range from 0.978x to 1.006x (up to 2.2% slower); accepted as a bounded tradeoff for
removing the long-note scan cost, not described as a universal speedup.

Final measurement:

```text
1 dense-short average original=0.039982 candidate=0.039771 speedup=1.005
1 dense-short pattern_number_1 original=0.027907 candidate=0.028236 speedup=0.988
1 dense-long average original=0.041748 candidate=0.039875 speedup=1.047
1 dense-long pattern_number_1 original=0.032648 candidate=0.029235 speedup=1.117
1 sparse-long average original=0.024803 candidate=0.023616 speedup=1.050
1 sparse-long pattern_number_1 original=0.039813 candidate=0.038817 speedup=1.026
4 dense-short average original=0.139211 candidate=0.140317 speedup=0.992
4 dense-short pattern_number_1 original=0.070905 candidate=0.071968 speedup=0.985
4 dense-long average original=0.149840 candidate=0.144205 speedup=1.039
4 dense-long pattern_number_1 original=0.084165 candidate=0.074477 speedup=1.130
4 sparse-long average original=0.056197 candidate=0.053575 speedup=1.049
4 sparse-long pattern_number_1 original=0.116303 candidate=0.113644 speedup=1.023
16 dense-short average original=0.467941 candidate=0.465062 speedup=1.006
16 dense-short pattern_number_1 original=0.243105 candidate=0.248515 speedup=0.978
16 dense-long average original=0.497664 candidate=0.470410 speedup=1.058
16 dense-long pattern_number_1 original=0.285102 candidate=0.255038 speedup=1.118
16 sparse-long average original=0.182692 candidate=0.173540 speedup=1.053
16 sparse-long pattern_number_1 original=0.422682 candidate=0.414254 speedup=1.020

```

Validation: all 1537 Lua unit/integration tests pass (29.042 seconds), six
inventory/name/syntax guards pass, and the independent new unit checks strict
fractional cutoff, exact equality, subunit lengths and isolated full-cycle notes.
Sol review independently proved the integer-distance/fractional-cutoff equivalence.
Existing native recipes/oracles are unchanged:

| Case | Controlled run | Real-time run |
|---|---|---|
| M-MERGE-025 | d1a7a4628d47424584720ea4f0145207 | b88eafcd73f741ba8d3196990a7b46b0 |
| M-MERGE-027 | 71443024c7fe44979aa7e081fb084a9b | 2ec6beaf55d240d29b563229233eb274 |
| M-MERGE-042 | cc8f8f36138f4c60aca53bac56740481 | 5fc22428b27b44a496f441b452a45350 |

Next: remove duplicate priority-source length resolution within a single merge
if measurement justifies it; keep any reuse bounded to the rebuild until the
writer/invalidation map supports longer-lived caching. R07 remains incomplete.

## Invariant merge inputs and within-call reuse

Hoisted priority parsing and the existing ambient step-mask lookup out of the
source/step loop. Numeric modes retain their sorted accumulation order. A length
priority reuses its source_lengths computed in the same synchronous call; unassigned
priority sources still participate without becoming trig assignments. No cache or
revision state survives the call. Existing selected-song getter semantics are retained.

Reproduce incremental comparison:
`lua5.3 docs/testing/refactor/benchmarks/full-merge.lua 170d6c1`

Final sample shows 1.18-3.31x full-merge speed ratios, with equal complete outputs in
all 18 workloads. This exceeds the prior small dense-short overhead and observed
noise; it remains a host merge benchmark, not a hardware timing claim.

```text
1 dense-short average original=0.039318 candidate=0.030982 speedup=1.269
1 dense-short pattern_number_1 original=0.028136 candidate=0.020120 speedup=1.398
1 dense-long average original=0.039604 candidate=0.031307 speedup=1.265
1 dense-long pattern_number_1 original=0.029335 candidate=0.020396 speedup=1.438
1 sparse-long average original=0.023509 candidate=0.017104 speedup=1.374
1 sparse-long pattern_number_1 original=0.038728 candidate=0.020178 speedup=1.919
4 dense-short average original=0.139369 candidate=0.108597 speedup=1.283
4 dense-short pattern_number_1 original=0.071736 candidate=0.042449 speedup=1.690
4 dense-long average original=0.145125 candidate=0.123407 speedup=1.176
4 dense-long pattern_number_1 original=0.074006 candidate=0.043708 speedup=1.693
4 sparse-long average original=0.053462 candidate=0.027979 speedup=1.911
4 sparse-long pattern_number_1 original=0.119801 candidate=0.042128 speedup=2.844
16 dense-short average original=0.517164 candidate=0.353268 speedup=1.464
16 dense-short pattern_number_1 original=0.245409 candidate=0.134729 speedup=1.822
16 dense-long average original=0.472050 candidate=0.356403 speedup=1.324
16 dense-long pattern_number_1 original=0.254367 candidate=0.142800 speedup=1.781
16 sparse-long average original=0.171654 candidate=0.068470 speedup=2.507
16 sparse-long pattern_number_1 original=0.416887 candidate=0.126156 speedup=3.305

```

All 1537 Lua tests (26.696 seconds) and six guards pass. Existing native cases:

| Case | Controlled run | Real-time run |
|---|---|---|
| M-MERGE-007 | fb40538a0f894783a6d293899773d958 | 0541dfcdc9224ede908a4bc386da966b |
| M-MERGE-010 | e5404b5368e744ecb2707e030897ce2f | 75dbebfeca9e44918c44e10ec167def5 |
| M-MERGE-015 | c0875db9e4fd44888751c6b3a80133ff | 6a6b2d5caaaa4ba7bdf657db2a2ab260 |
| M-MERGE-001 | 8bbdf01ce60c449f84877f71db3c5536 | ba34e9b5c69d4d88819c39364ed899a5 |

Sol review found no changed final priority behavior, in-call mutation or yield.

R07 remaining: dirty tracking and source revision checks require shared writer
seams. Adding a counter only at rebuild requests would duplicate debounce cancellation
and miss untracked writes. Next migrate the note editor step-note operation to an
explicit song/pattern target and its captured-song invalidation, then the other
writer families identified in model-mutation-map.md. Preserve per-channel publish
then yield. Do not claim source freshness after migrating only one writer family.

## Targeted rebuild candidate (baseline c7a9bde)

`lua5.3 docs/testing/refactor/benchmarks/targeted-rebuild.lua` runs the actual
production merge and cooperative scheduler, alternates old/new measurement order
for five samples per workload, and compares complete final song contents. Each
sample performs 100 source edits; source 1 feeds 1, 4 or 16 channels.

| Consumers | Baseline CPU seconds (five samples) | Targeted CPU seconds | Speedup range |
|---|---|---|---|
| 1 | .085315, .085530, .092098, .088710, .085196 | .006538, .006355, .006176, .006328, .006014 | 13.049–14.912x |
| 4 | .084807, .084489, .085076, .084309, .086507 | .022139, .022429, .026305, .022510, .022916 | 3.234–3.831x |
| 16 | .089427, .084609, .085263, .086999, .085807 | .085815, .086459, .088390, .088390, .086878 | .965–1.042x |

Sparse-consumer benefit exceeds sample variation. All-consumer requests retain
small bookkeeping overhead and show no established benefit. These are host CPU
measurements with dependency stubs, not emulator acceptance or physical-norns
performance. Validation for this candidate is recorded below.

Known unchanged limitation: merge eligibility still reads step trig masks through
the ambient selected-song getter. Explicit rebuild target validation does not
correct that pre-existing dependency. It needs isolated reproduction before a
behavior-changing fix; this candidate does not establish R07's full cross-song
correctness claim by itself.

### Targeted scheduler validation

All 1540 Lua tests pass (25.243 seconds) with no concurrent emulator workload;
six guards pass. An earlier concurrent run had 1539 successes and the known
load-sensitive 2 ms live-slide admission failure at 2.351 ms. Its limit was not
changed. Three new scheduler tests cover pending dirty union (including a source1-
only late channel), all unassigned priority dependencies and false assignments,
and stale revision/channel replacement rejection. The trigger-page integration
stub now checks the targeted song/source arguments.

Unchanged native recipes and oracles pass on the production candidate:

| Case | Controlled | Real-time |
|---|---|---|
| M-PAT-BOUNDARY-001 | 3b3b622de14a4ff2ade301410b033e78 | Not run: this recipe requires native_input_schedule in real time |
| M-EDIT-003 | cb6de6f4f29d443da9999f7d058b24ca | 291cbe22b2ef4bc79e5c346028866c76 |
| M-MERGE-TRIG-002 | 1a85754ea61944b8a20c4e50f6320726 | c288970a578a4f308121f29e9035e97f |

The final dirty-union test-only strengthening followed native validation; no
production code changed after these native runs. S71 remains an unvalidated
pre-existing suspicion, not a fix or an R07 completion claim.

### Additional targeted-rebuild acceptance (production c5f81de)

All16 priority sources, song copy/erase and autosave/fresh-process restore passed
controlled runs `4cab8f233b454f6b8904dd49bcb24b04`,
`ddabd563621140b3ab1847f1a306c7be`, `0cde13b1610c41238b49c0595c6e3dda`.
Real-time copy and save passed `d46b7668ad744712a7716e4a2dce1a74` and
`329c9ce454d14d6c94537dc761df9c75`. Real-time priorities first failed its 10ms
interval bound at 10.073ms (`22a75ba1ae424287b1b69dc133929a48`), then passed
without concurrent benchmarking (`65889a74229e44f3800818cdb76cbe58`); the bound
and musical oracle were unchanged. This records the timing variability rather
than treating the initial failure as a pass.

### Per-request effective-length reuse candidate

Independent in-memory candidate experiment and raw samples are preserved under
`/home/andy/projects/mosaic-behaviour-runs/r07-effective-reuse/` (`benchmark.lua`,
`results.tsv`). Five alternating samples of 40 full16channel sweeps each compare
complete outputs with current production and bound the cache to16 source arrays.
Median speedups for 1/4/16 shared sources: dense-short 1.060/1.061/1.095x;
sparse-sustained 1.035/1.143/1.293x. The single sparse source was within noise;
consistent multi-source gains justify implementing conservative request-scoped
reuse. These are host CPU experiments, not physical-device acceptance.

Candidate implementation resets the per-song cache on every async rebuild request
(including an empty target set), invalidates it on direct synchronous rebuilds,
and releases it when the dirty sweep completes. Direct builds remain uncached.
No source-version claim or persistent cache is introduced. Validation follows.

### Actual request-cache implementation validation

`benchmarks/rebuild-length-reuse.lua` compares the actual implementation with
pinned `9b17d3f`; raw results are preserved in
`/home/andy/projects/mosaic-behaviour-runs/r07-effective-reuse/actual-candidate-results.tsv`.
Median speedups for1/4/16sources: dense-short1.050/1.030/1.078x and
sparse-sustained1.034/1.117/1.277x. Dense4source samples were noisy (.797–1.126x);
sustained16source samples consistently ranged1.273–1.287x. All compared outputs
matched and the source cache stayed within16entries. The earlier exploratory
script dynamically reads the checkout; its original `results.tsv` is historical
and must not be regenerated as though it still represented the old baseline.

All1542 Lua tests pass (25.516 seconds), and six guards pass. Focused tests verify
source-array reuse, direct-build invalidation before late async publication,
targeted and empty-request invalidation, and separation between songs. Read-only
review found no introduced cache ownership defect. The optional internal cache
argument belongs to one song/request; arbitrary external table reuse across songs
is not a supported API. An idle empty request may retain an empty table, never
source arrays; weak song ownership remains unchanged.

| Case | Controlled | Real-time |
|---|---|---|
| M-PAT-BOUNDARY-001 | cc7a3b9b78d44a21a55df394693bfa1c | Existing runtime limitation, not run |
| M-PAT-004 | c6b56182e95c4e32b3d08f23d2d3f886 | de4354f3b0954563950e0a48bdd3a6ab |
| M-MERGE-007 | 364e48c169a044e6b4245a2fc4c4671d | 5c25eaf48bcf4c0da52a22071792399f |

R07 implementation now includes measured effective-length resolution, within-merge
invariant reuse, request-scoped cross-consumer reuse, and targeted dirty tracking
with per-channel publication checks. Sorted accumulation remains deliberately
unchanged where unsorted floating arithmetic would change results. S71 is an
unvalidated pre-existing suspicion and not fixed by these optimizations. Final
combined dense/input-pressure acceptance remains part of the continuing refactor;
no full refactor or physical-device performance completion is claimed here.
