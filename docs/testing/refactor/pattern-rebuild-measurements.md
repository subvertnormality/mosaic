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
