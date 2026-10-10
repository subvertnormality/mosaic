# v05 two-scalar review

**Decision: HOLD.** This supplement reviews only the two v05 fields and preserves the earlier v03/v04 reports. Scores are fresh judgments against the current rubric ledger `fe378689a917dd0eedc2f77e13588bd9b6faba11b66dfc3d6e948dc78c1255f2`; no prior scores were transferred from the stale Windows ledger.

| Unit | Coherence | Usefulness | Understandability | Representation | Granularity | Flow | Integration | Vocabulary | Naming | Canonical home |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Locks recipe 4 | 9 | 7 | 8 | 9 | 8 | 7 | 8 | 8 | 9 | 9 |
| Performance Management detail 0 | 6 | 7 | 9 | 8 | 8 | 6 | 6 | 7 | 5 | 8 |

Locks v05 fixes the v04 navigation findings: it tells the reader to open Channel, select channel 1, assign Pattern 1, tap slot 2 after each copy, and select slot 1 before each comparison. The note values are correctly step-local absolute Note masks, not Pattern Note scale degrees. One setup issue remains: the relative-turn exercise calls slot 1 32 steps without instructing the reader to set it; new Song Patterns default to 64 (`lib/models/model_defaults.lua:98`). The endpoint exercise does explicitly set slot 1 to 32. Add that same setup to the relative exercise.

The Performance Management replacement sentence is understandable but remains under the unchanged title “Earlier timing test,” and the containing feature prose still includes the version 1.1.1 test-history paragraph. Update the heading and address the stale history in the parent prose; tie the practical advice to the workload controls already described.

Candidate manifest: `928d0ce471fce9ac259978a4956c48f08816fb7ebb54e0a004808da44cf160b0`. Candidate Locks YAML: `6e55bc5426ebdab56607baf3e60e034a271269262fa53b74f5b0c322b0c6f9c2`. Candidate musical YAML: `a0e236ebaa20c95d1032a60431fcc3b8ba427b52694a496cb50b040a16cd2d8e`.
