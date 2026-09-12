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
