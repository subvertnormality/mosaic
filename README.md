# Mosaic

![Mosaic](images/logo.svg)

Mosaic is a grid-first rhythm and harmony sequencer for norns and a 128 grid.
Compose and perform with rhythmic patterns and harmony. Combine patterns on
channels, then shape their output with masks, scales and parameter locks.

**[Open the interactive manual](https://subvertnormality.github.io/mosaic/manual/)** · [Quick reference](https://subvertnormality.github.io/mosaic/cheat_sheet.html) · [Configuration creator](https://subvertnormality.github.io/mosaic/config_creator.html)

## Developer instructions

`manual/book.yaml` and its listed YAML sources are the manual authority. The
HTML manual and quick reference are generated from them. See
[build instructions](https://github.com/subvertnormality/mosaic/blob/codex/1.4.0/manual/BUILD.md), [validation evidence](https://github.com/subvertnormality/mosaic/blob/codex/1.4.0/manual/REPORT.md)
and the [developer instructions](https://github.com/subvertnormality/mosaic/blob/codex/1.4.0/AGENTS.md).

Every feature change must update its affected behaviour tests and manual sections
in the same change. New features need comprehensive behaviour coverage, including
boundaries, failures and interactions, plus full manual sections with practical
workflows and interactive examples. Update the quick reference when controls change.

The published manual lives on [GitHub Pages](https://subvertnormality.github.io/mosaic/manual/).
During development, [Build manual site](https://github.com/subvertnormality/mosaic/actions/workflows/manual-build.yml)
creates a downloadable preview artifact for the exact pull-request run. A preview
does not update the published manual.

The 1.4.0 release combines the sequencer, manual and Pages publisher in
[one release PR](https://github.com/subvertnormality/mosaic/pull/98).
After it merges to `main`, the publisher promotes the exact validated CI
artifact using the [publication procedure](docs/manual-publication.md).
It checks the merged PR, source identity and current `main` tree before publishing.

Local generation and behaviour checks use controlled time. Real-time execution is
reserved for recording assets when necessary; the exhaustive real-time behaviour
campaign runs separately in CI.

The [original 1.4.0 manual](https://github.com/subvertnormality/mosaic/blob/codex/1.4.0/manual/legacy/README-1.4.0.md) is preserved unchanged
so historical behaviour evidence retains its original source identity.
