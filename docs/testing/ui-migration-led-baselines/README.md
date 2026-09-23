# Recording LED oracle migration evidence

The strict targeted CI before/after records for the later recording LED-oracle
reexpression live here because `ui-migration-cases-baselines/` already contains
earlier immutable evidence for some of the same cases. No earlier record was
overwritten.

The source pair is `be74fb4115d338d751b7964f4d65cd539e492923` (raw
64-cell LED observations) and `60e5d1fa3446ba2f718340381aa013436384a21d`
(semantic `Ui.expect_steps`). Both sides use the same UI map, runner, gate, and
production source. The strict gate passed in real-time and controlled-time
lanes for these batches:

- GitHub Actions run `35918869167`: M-REC-008 through M-REC-011.
- GitHub Actions run `35918871437`: M-REC-012 through M-REC-014,
  M-REC-032, and M-REC-033.

The same source pair also passed for M-REC-001 through M-REC-004 in run
`35918866295`; those records live in `ui-migration-cases-baselines/`.
All three targeted reports set `complete_regression_run` to `false`, as required
for selected-case evidence rather than a full regression campaign.
