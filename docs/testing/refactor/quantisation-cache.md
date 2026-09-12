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
