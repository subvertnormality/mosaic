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

## Versioned prefix plans for dynamic stage arguments

Pin and preserve the ORIGINAL complete 72-stage JSON array from the reviewed builder plan separately. Its dictionaries define immutable stage identities for the entire run. Do not invent future resolved command vectors: Doctor Ready and option-audit commands depend on receipts and fixture paths that do not yet exist at startup.

The controller accepts a plan PREFIX through the current stage (`stage_index <= len(stages)`). Use one version per gate: stage 1 has one row, stage 2 appends its row, and so on. Every previous full-stage dictionary and actual resolved command must remain byte-equivalent under canonical JSON. Earlier plan versions and their pins remain immutable. The original complete plan pin independently anchors all stage dictionaries; prefix versions pin actual commands only after their dependencies exist.

Bootstrap after the builder writes its owner/request. The actual build evidence UUID is created by the builder and is not known in advance. Independently inspect the owner's live process command line and canonical evidence path, compare them with the requested owner and your intended invocation, then write a pinned context JSON containing the operator-plan fields except `stages`. Do not substitute a guessed evidence UUID or silently trust a request to authorize a different invocation. The controller independently verifies this context against the live process when inspecting/releasing the resulting plan.

The separate `prefix_plan.py` utility creates an exclusive immutable prefix and its version receipt. It does not execute/import the builder, resolve commands, release a gate or claim cleanup. Root may safely import the SHA-pinned reviewed candidate builder and call `stage_command` only after the current stage's actual dependencies exist. Independently compare its selected full-stage dictionary with the separately pinned ORIGINAL complete plan. Write the resulting exact argv list to a SHA-pinned command JSON file, then append the version:

```sh
python3 prefix_plan.py --original-plan /absolute/original-72-plan.json --original-plan-sha256 ORIGINAL_SHA --context /absolute/bootstrap-context.json --context-sha256 CONTEXT_SHA --command /absolute/current-resolved-command.json --command-sha256 COMMAND_SHA --stage-index 1 --output-directory /absolute/operator-plan-versions
```

For later gates, add `--previous-prefix PATH --previous-prefix-sha256 SHA` naming the immediately previous immutable plan. The utility defaults to an original count of 72, rejects skipped/repeated versions, compares every earlier full-stage dictionary against the original complete plan using canonical JSON types, copies all previous commands literally, and verifies that bootstrap/source identity is unchanged. Each receipt binds the original plan, bootstrap context, current command and preceding prefix SHA to the new prefix SHA. Pass the returned prefix path/SHA to the controller. No placeholder future rows are needed.

A plan and receipt are published separately with exclusive atomic writes; a crash between them can leave an orphan plan. This never releases the builder. The utility refuses to overwrite either file; root must inspect and preserve any incomplete preparation rather than automatically deleting/replacing it. Original complete-plan and prefix receipts are operator evidence, not automatic native-cleanup evidence. All host-memory attestations and external cleanup reviews remain required, including after nonnative audit stages whose report cannot enumerate native cleanup.

Run `python3 -m unittest -v test_prefix_plan` for 11 additional synthetic checks of exact append-only versions, future dependency commands, full-plan count/source pins, no skipped/repeated stages, bootstrap and nested-type mismatch refusal, preserved prior commands, and immutable CLI version receipts/duplicate refusal.

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
