# R08 quantisation cache

Baseline: `240f311`. This work follows the request-scoped pattern rebuild changes.

## Cached value and input contract

`quantiser.process_handler` caches transformed scale and pentatonic arrays; public
processing functions return a numeric pitch, never the arrays themselves. Misses
copy both source arrays before rotation/transposition. Preserve that ownership.

The transform reads ordered `scale` and `pentatonic_scale` contents, resolved chord
rotation when degree processing is enabled, `chord_degree_rotation` when rotation
is enabled, and transpose when transposition is enabled. Current keys additionally
include resolved root, slot number, all four flags, and version. Root, note index,
octave and pentatonic snapping are applied during final pitch selection. Retaining
redundant key components is safe; removing them requires a separate measured
comparison. A version alone is not authoritative for directly writable arrays.

Current content identity is an XOR hash of indexed scale values; pentatonic content
is omitted. Actual built-in hashes are distinct: Major197, HarmonicMajor334,
Minor3983, HarmonicMinor106, MelodicMinor481, Dorian3588, Phrygian3554, Lydian98,
Mixolydian3872, Locrian3204. Normal `program.set_scale` saves increment the slot
version. This diagnostic does not prove general collision freedom or establish
a native defect. Do not fold a speculative pitch fix into an eviction refactor.

## Existing verification and compatibility

Units already exceed100 distinct keys and count actual retained entries. Scale
hardening covers all16 save targets, song-copy separation, linked saves and direct
rotation changes. M-SCALE-CACHE-001 exercises110 live saves through the emulator.
Focused eviction/revisit and cache/source alias checks may supplement these;
do not duplicate the complete scale/pitch campaign.

Tests replace `_scale_cache` and reset `_scale_cache_size` directly, and restore
`_scale_cache_max_size` to100. A new policy must honor this existing reset contract
or migrate it explicitly. No production caller currently performs that reset.

Current eviction sorts all entries by second-resolution timestamps and removes
25percent when capacity is exceeded. Timestamp ties do not define reliable LRU.
Measure a capacity100 FIFO ring first, with insertion-only bookkeeping and explicit
reset handling. Use more elaborate LRU only if representative hotset/churn results
justify it. Key construction and scale transformation remain unchanged in this
policy comparison. Measurements and implementation decision are pending.

## Eviction experiment and decision

Corrected experiment artifacts are preserved under
`/home/andy/projects/mosaic-behaviour-runs/r08-cache-policy/`: `benchmark.lua` and
`results.tsv`. An earlier sparse-array queue prototype was rejected during review;
its measurements are not evidence. The corrected candidate uses an explicit
capacity-100 ring, resets metadata when the cache table is replaced, and removes
hit timestamp writes. Five alternating samples of 12,000 public-process calls
per workload compare every individual output note; all match.

| Workload | Current median seconds | FIFO median seconds | Decision evidence |
|---|---|---|---|
| Warm key | .032006 | .032170 | Within noise |
| Cyclic 240 keys | .139922 | .152293 | FIFO 8.8% slower, 0 hits versus about 3156 |
| Small hot set plus scans | .047365 | .042505 | FIFO 10.3% faster, 1304 misses versus 1410 |

Retain current eviction: FIFO is not a clear workload winner. True LRU cannot rescue
a cyclic sequence larger than its capacity, so more implementation/benchmarking
is not justified here. Capacity remains 100; existing reset semantics and ownership
remain unchanged. Do not replace hashes with version-only identity while direct
writes exist. Preserve source copies because transforms mutate their working arrays.

One structural cleanup makes `scale_hash` local to key construction, removing an
accidental global assignment without changing any cache key, eviction decision,
or numeric result. No speculative musical defect fix is included. Full-content
key collision resistance remains a documented limitation; the built-in diagnostic
and current workflow coverage do not prove safety for arbitrary externally mutated
scale containers. Final combined refactor acceptance remains outstanding.

## Validation receipt

All 1542 Lua tests pass (24.251 seconds), and six inventory/name/syntax guards
pass. The existing 110-save native M-SCALE-CACHE-001 passes in controlled time
`d57698edf33645069a505b69b4f84b2a` and real time
`06817a6a2e3943c8b6fea88c09e409a1`, with unchanged inputs and pitch oracles.
The production change is solely the local scope of `scale_hash`; eviction,
capacity, keys and copying remain as before. FIFO is deliberately not shipped.

Proceed to the R09 scheduler work with the existing cache policy. General key
collision resistance remains a recorded limitation, not a claimed defect fix;
final combined refactor/performance validation remains outstanding.
