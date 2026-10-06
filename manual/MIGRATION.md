# Coordinated manual authority transition

The HTML field guide and its quick reference use one YAML model. The user has
authorized that model as documentation authority. Acceptance activation remains
inactive during preparation; completing the content migration is separate from
the exhaustive behavior campaign.

## Preserve the recorded source revision

The exact original README remains `manual/legacy/README-1.4.0.md`, SHA-256
`532f08b5fff1d2b90022f02ba418dcbef3b77017e8a1a5c6e057d04a9e41b51c`.
The original cheat sheet is `manual/legacy/cheat-sheet-1.4.0.html`, SHA-256
`edf0df405c75727a8ff29a16d3640b71af2c6bfe4b5ddb5db603474e02bed561`.

Later full UI documentation is a different source revision. Freeze it in a
content-addressed `README-before-authority-<sha>.md` and
`cheat-sheet-before-authority-<sha>.html`. Source aliases identify those exact
bytes; the original archive hash never derives from the changed current README.

The transition retains all 125 MAN IDs, 178 requirements, the original 876 case
IDs and their additive extensions. Every statement keeps its original source
record. All 77 original quick-reference rows remain in a separate history receipt.
Current reviewed controls keep their own source revision. Historical result files,
baselines and failure evidence remain untouched.

## Prepare before freezing native inputs

1. Finish transition code and its tests, production changes, exact prose and all
   scene/audio/fixture authoring. Do not shorten the root README while its final
   full UI documentation is still being edited.
2. Preview the source transaction without writing:

   ```
   python3 tests/behaviour/reconcile_manual.py --freeze-manual-sources --prepare-authority --plan
   ```

3. When the final full documentation is ready, apply that same transaction:

   ```
   python3 tests/behaviour/reconcile_manual.py --freeze-manual-sources --prepare-authority
   ```

   This creates exact immutable snapshots, routes every existing statement to a
   matching archived line and hash, and prepares stable feature mappings.
   `manual_authority.status` stays `inactive`; no mutable final authoring identity
   is bound yet. The behavior gate uses the frozen full UI manual, so the later
   short root overview cannot erase intended behavior or section coverage.
4. Apply the reviewed root overview, AGENTS authority wording and generated root
   quick reference together. Refresh the UI source ledger against explicitly
   frozen original/current sources while preserving its previous identities.
   Root documents and generated artifacts are part of whole-repository identity.
5. Freeze runtime files, all `docs/ui-reimplementation` files, non-test behavior
   helpers, native adapters, plans and fixtures. Run the required native capture
   build against that candidate. Those inputs must not change after capture.

`--help` and `--plan` never write the gate or archive files. Missing, incomplete
or stale activation inputs fail before any inventory, matrix or snapshot write.
Prepared mappings grant no native acceptance.

## Activate only after final evidence

1. Independently audit raw captures, both applicable timing lanes, Doctor's
   explicit real-audio exception, chapter contracts and audio.
2. Bind only proven feature/chapter scopes, refresh the scene index, compile the
   book and generate the final user references. Keep `complete_manual=false`
   until actual feature and course gates pass.
3. After the compiled book is complete and current, activate:

   ```
   python3 tests/behaviour/reconcile_manual.py --activate-authority
   python3 tests/behaviour/reconcile_manual.py --check
   ```

   Activation is an inventory/matrix transaction. It retains the original
   historical README identity, keeps the later full-manual aliases and binds every
   configured YAML/schema source to its current hash. The gate also checks the
   complete compiler output and assertion-backed scene contracts. Preparing an
   already active authority cannot downgrade it.
4. Run the final resolver, inventory, publication and browser checks without
   modifying any pinned helper or UI-ledger file.

Case/generic capture snapshots omit the root overview and generated publication
data, so final data binding can preserve those native identities. Whole-repository
canonical snapshots include those files: qualify after final artifacts settle,
or retain earlier qualification explicitly as historical with a reviewed runtime
projection. Never rewrite or silently narrow the original identity.

Shard and aggregate acceptance rules remain unchanged.
`complete_regression_run` stays false for a manual build. No commit, push or pull
request is implied by this local transition.
