# Prepared between-stage controller

This preparation does not install or run the candidate builder. Root must review and apply it only after both course captures pass. No active repository files were changed. It sends no signals, starts no native processes, drops no cache and never restarts a build.

The CLI is `python3 controller.py`. Default operation is read-only inspection. Release additionally requires `--publish` and a SHA-pinned external attestation. All successful releases use a fully flushed/fsynced exclusive temporary file followed by Linux `renameat2(RENAME_NOREPLACE)` and a directory fsync. Unsupported rename platforms refuse release. Existing releases and accepted stage archives refuse duplicate release.

## Operator plan

Create an independently reviewed JSON plan, pin its SHA-256, and pass `--plan PATH --plan-sha256 SHA`. Do not derive approval solely from an untrusted request. Exact schema:

```json
{
  "schema_version": 1,
  "builder_path": "/absolute/path/to/candidate/tools/manual_build.py",
  "builder_sha256": "a59e8f2f1e3913033f4c7f3981d364e625f4d30dabf733367d3aa70450d364c8",
  "builder_argv": ["python3", "/absolute/path/to/candidate/tools/manual_build.py", "--stage-gate-dir", "/absolute/gates"],
  "evidence_dir": "/absolute/build-evidence",
  "stages": [{"stage": {"name": "exact-name", "command": [], "emulator": null, "exclusive_lock": false, "action": null}, "command": []}]
}
```

`builder_argv` is the full actual command-line argument vector, with no omitted options. `stage` is each complete dictionary emitted by the pinned builder plan, including optional keys. `command` is the exact resolved vector `stage_command` will use, including evidence paths and dynamic audit/Ready/course-bind arguments. The controller does not import or execute the builder to reconstruct commands. Operator planning for dynamic arguments may therefore occur after preceding receipts exist, with a new independently reviewed plan pin. Existing stage rows must continue to match preceding immutable receipts. Filenames and argument vectors must remain absolute/canonical where the schema requires paths.

Inspect a request with:

```sh
python3 controller.py --request /absolute/gates/001-SHA.request.json --plan /absolute/plan.json --plan-sha256 PLAN_SHA
```

Inspection validates the canonical request bytes and filename SHA/index; exact integer types; owner file; process PID/starttime/live command line and user ownership; current builder SHA; request location against `--stage-gate-dir`; evidence directory; full stage and resolved command hashes; preceding successful stage receipts, command and log identities; pinned native reports; accepted archives and releases; and absence of matron, crone, sclang, jackd, jackdmp and jackdbus in the process table. A readable process table is required; inaccessible live entries fail closed. Inspection emits the exact resume object and cleanup scope. It does not release anything.

## External checks

Every release requires a separate fresh request-bound attestation, SHA pinned with `--checks PATH --checks-sha256 SHA`. Exact mandatory schema:

```json
{
  "schema_version": 1,
  "request_sha256": "REQUEST_SHA",
  "stage_sha256": "REQUEST_STAGE_SHA",
  "previous_receipt_sha256": null,
  "checked_utc": "2026-10-04T12:00:00+00:00",
  "memory_preflight": {"passed": true, "scope": "entire-next-stage"}
}
```

`previous_receipt_sha256` is null only at the first stage; otherwise it is the request's exact prior receipt SHA. UTC check age must be at most five minutes, and future skew at most five seconds. This is the operator's assertion of a completed memory preflight, not an automatic memory measurement. The controller does not claim adequate host memory from process absence. Budget the whole next stage, including all inner sessions in musical-audio stage 54. The gate does not provide inner-session boundaries.

For strong case-scene reports, the controller verifies every enumerated primary/child participant, the participant manifest, pinned session-context files (`finished: true`, `cleanup_verified: true`, empty held-input list), and cleanup-file hashes with complete matron/crone/sclang/jack service rows and permitted exit codes. It does not interpret scene assertions as cleanup. This schema was checked read-only against the prior actual complete-start recovery report.

Generic capture, Doctor, audio and other unrecognized report schemas do not automatically establish exhaustive cleanup, even if `passed` is true. Inspection returns `external-root-review-required`. Add this exact optional attestation field only after the operator independently reviews all preceding-stage native participants:

```json
"cleanup_review": {
  "passed": true,
  "scope": "all-prior-stage-native-participants",
  "report_sha256": "PINNED_NATIVE_REPORT_SHA_OR_NULL",
  "assertions": {"finished": true, "no_held_inputs": true, "cleanup_verified": true},
  "evidence": [{"path": "/absolute/operator-review-evidence", "sha256": "EVIDENCE_SHA"}]
}
```

All listed evidence files are rehashed. If no native report is bound by the prior receipt, use JSON null for `report_sha256`. The controller records `external-root-review`, explicitly distinguishing the operator assertion from automatic participant-file proof. These assertions depend on an honest independent operator review; a self-authored check file cannot itself prove hardware cleanup or memory capacity.

After all checks:

```sh
python3 controller.py --request /absolute/gates/001-SHA.request.json --plan /absolute/plan.json --plan-sha256 PLAN_SHA --checks /absolute/checks.json --checks-sha256 CHECKS_SHA --publish
```

All identity, receipt, cleanup and process checks run again immediately before publication. No polling/retry/restart loop is provided. Refusal exits 2. Inspect the reported reason; never replace an existing resume. Process-table absence is an instantaneous observation and does not prevent an unrelated process being started concurrently; the root orchestrator must retain its exclusive native scheduling discipline.

## Synthetic evidence

Run `python3 -m unittest -v test_controller` from this directory. Thirty-one focused tests cover valid requests, exact resume fields, typed integers and booleans, malformed/noncanonical JSON, request/plan/source/argv/command tampering, recycled PIDs, copied/symlink requests, failed or unfinished receipts, nested JSON type mismatches, native presence including jackdmp, duplicate/accepted releases, complete exclusive publication, unsupported rename platforms, stale/wrong attestations, honest unsupported-report fallback, and participant/held-input/cleanup evidence.

`review-regression-baseline/` is an explicitly reconstructed pre-review version of this preparation, reverting only the four requested hardening checks. All four corresponding regressions fail there and pass in the candidate. It is not a historical production/native baseline. Logs are `review-regressions-red.log` and `synthetic-green.log`. No live builder or native session was exercised by these tests.
