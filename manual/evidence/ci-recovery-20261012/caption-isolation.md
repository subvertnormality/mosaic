# Caption test import isolation

Baseline: d645ba2d9c32b6adf25e9abc39c6bceed2765be0, behaviour run
38300645318, shard 0 job 114982471613. All 72 native case/lane runs
passed; the fast test layer failed importing `test_manual_caption_overlay`.
The added publication-verifier import preceded the module's tools-path setup.
Local checks with a global tools PYTHONPATH had masked this failure.

The exact isolated unittest invocation was reproduced on Linux without
PYTHONPATH: the baseline failed with `ModuleNotFoundError` for
`manual_publication_verify`. Moving the import after the existing path setup
made all 19 tests pass. Assertion bodies and native/audio inputs are unchanged.

The lightweight CI contract job now runs the same module from
`tests/behaviour` with empty PYTHONPATH and MONOME_EMULATOR. It installs
PyYAML 6.0.2 and jsonschema 4.23.0. A workflow regression executes the actual
step with its isolated environment. Both dependency pins were installed
successfully on Linux before push.

Validation: 153 focused registration, caption, recording-oracle and CI
contract tests passed; all 68 manual packaging/publication contract tests
passed. An independent read-only Luna review found no blockers. No native
application execution or audio recording was performed for this fix.

CI must qualify the corrected commit before publication. Existing final
manual artifacts cannot be relabelled for a changed source revision;
retained raw audio remains subject to unchanged strict current-source audits.
