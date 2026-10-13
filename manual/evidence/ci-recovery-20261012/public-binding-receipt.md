# Public binding-receipt export regression

The manual build on `d0cf9cea76d2b5ac908678b2b2f77791c01f429e`
(Actions run `38312744028`, attempt 1) completed all 49 timed generation,
audit and browser stages. Packaging then rejected an absolute host path under
`features[].review.binding_receipt` in the reader index.

The receipt is developer evidence used by the private reconciliation checks.
The public reader does not consume feature review metadata. An actual-data check
also exposed an absolute `log` path in its historical review evidence. The export
now omits `features[].review`, alongside the existing omission of feature sources,
while preserving the original private input. Unknown absolute host paths still
fail export. Runtime chunk hashes and feature scene references remain.

The regression exercises the complete public-site collection with the receipt
and historical review log present and checks private source bytes remain unchanged. A separate test
keeps the unknown nested host-path rejection explicit.

Before the production change, the Linux packaging suite ran 70 tests and failed
with exactly one error: `Absolute host path found in public JSON under
binding_receipt`. After the change, all 70 tests passed. Diagnostic red and green
logs are retained separately under `.ci-diagnostics/run-d0cf9cea/`.

The publisher's reviewed tooling digest is updated to the new canonical LF
packager bytes. This change does not modify musical scenes, audio assets,
application behaviour or the identities of previous evidence.

An independent replay verified Actions evidence archive SHA-256
`0068112b41d5b56ed24627ba5b9aa58e5e898587296326d596116e3ab86bf256`.
Its reader index is byte-identical to the source checkout (SHA-256
`254d19c38871b71973a6252fe859a02c4a9d6c8c464840d367de58baa8c4ff24`).
The frozen HEAD exporter reproduces the receipt error; the scoped exporter passes
on that same index and the pilot. All 167 referenced chunks match their recorded
hashes, the source checkout and the collected site. Full collection produces
225 files, including 169 JSON files, with feature reviews omitted.

Hash-bound runtime chunks remain byte-identical, including their nested native
receipt metadata; this fix does not rewrite or relabel those proofs. The separate
developer diagnostic records their path fields. These are not exposed as reader
controls or feature specifications.

The packaged-site smoke also required a follow-up: it requested unpublished raw
book, audio-report and inventory JSON rather than the public reader projection.
That browser check must use the packaged reader index and referenced chunks.
The frozen HEAD smoke was executed against the collected site with the same
Playwright 1.51.1 used in CI. It failed in `page.evaluate` with `Unexpected token
'<'` when `/manual/generated/book.json` returned HTTP 404. The reader itself had
loaded its public reader index and pilot with HTTP 200 before this failure.

The corrected smoke passed on the same collected site with Playwright 1.51.1:
133 features, 146 scene chunks, 21 audio chunks, every chunk SHA-256 and ID
verified, six navigation links, rendered Masks title, audio HEAD HTTP 200, and
no page errors. The public-package fixture regression fails against the former
raw-data references and passes against the revised smoke. All 71 Linux
packaging/publisher contract tests pass after both fixes. No native sessions or
audio recording were run locally for these changes.
