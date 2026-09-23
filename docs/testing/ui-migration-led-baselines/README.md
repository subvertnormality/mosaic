# LED oracle migration evidence

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

## Length and duration LED assertions

The later semantic LED reexpression for `M-LEN-001` through `M-LEN-004`
is also stored here because their earlier canonical migration records already
exist in `ui-migration-cases-baselines/`; those records were not overwritten.
GitHub Actions run `35928530231` passed the strict gate in real-time and
controlled-time lanes for the raw physical-LED source
`6a93b8861996f1ef65e29a644545a7262b7b0b73` and semantic candidate
`612d1802ce461f7557a16380bfa1cc7b6bb11232`. Both sides used the same
UI map, runner, gate, and application source. Its targeted report retains
`complete_regression_run: false`.

The same raw and semantic source pair passed for `M-PAT-003` through
`M-PAT-005` and `M-MIDI-001` in GitHub Actions run `35928532283`. These
duration/MIDI LED records are stored here as a second immutable migration
stage, alongside the length LED records. The targeted gate passed in both
real-time and controlled-time lanes, with `complete_regression_run: false`;
it is not a substitute for the aggregate behaviour campaign.

The editor LED reexpression for `M-EDIT-005` also lives here because an
earlier immutable record exists in `ui-migration-cases-baselines/`. Its
strict raw/candidate pair is `8767bd1eab3c9958bd9756b91e53edd5cd18ea5e`
and `bf1e4c1abd8731134213100f40e3119f9a37583a`. GitHub Actions run
`35932086040` passed in both timing lanes after a failed grouped run had
reported a native `matron` shutdown crash on the raw side. That failure
artifact remains separately preserved; this successful retry has its own
source manifests, results, recipes and provenance.

The same raw/candidate editor LED pair passed for `M-EDIT-001` through
`M-EDIT-004` in GitHub Actions run `35933484155`, in both real-time and
controlled-time lanes. These records live here together because
`M-EDIT-004` already has an earlier immutable record in
`ui-migration-cases-baselines/`. The targeted report remains partial
(`complete_regression_run: false`).
