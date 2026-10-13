# Enlarged-grid alignment evidence

This package preserves the exact CSS, JavaScript and registered-browser-test inputs used for the CG-2 RED/GREEN check, the corrected final focus-scroll baseline, and the actual-served post-install report and screenshots.

The focused harness is operator-specific. It loads Playwright from /home/andy/mosaic-manual-tools/node_modules/playwright and intercepts only the CSS and JS from the fixed candidate/baseline trees under /home/andy/mosaic-manual-build-operators/compact-grid-enlargement-alignment-fix-20261008-03. The archived proof outputs are proof/red.json and proof/green.json. They test four viewport/layout combinations: 1121px and 1440px, in Original and Shield layouts.

The installed-preview harness, proof/served-final.json, uses the already-running preview at http://127.0.0.1:8785/manual/ without CSS/JS interception or restart. Its recorded asset hashes must match the installed pins in MANIFEST.json. The four screenshots show the initially aligned headers and ArrowRight focus on column 16 for both layouts.

The document scroll baseline is taken after focusing pad 1. This isolates scrolling caused by ArrowRight from any initial focus scroll. The candidate must keep the focused last pad at least 8px inside the grid scroller and preserve every LED value and accessible pad label.

The exact operator workspace dependencies and output paths are recorded in the scripts and manifest. These are archived operator harnesses, not portable commands for a fresh clone.
