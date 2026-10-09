# Final manual book browser test delta audit

Read-only comparison of the source16-pinned test and the final candidate. No tests, browser, native, or audio runs were performed.

Source16 file SHA-256: 82cd8bc637a7351ff07140170fed860d2bf8396e122e524f18c18b5b7dab36b9  
Final candidate SHA-256: 39b79cb1def0637a4255020daa18ae1d2bec7a0cfb627db77bfbf385a096ab4f  
Unified diff SHA-256: eaa62303bfa9ff7b103813e9177c9f195ee4212ec82112e5dbc095835d59d5ab

The milestone change adds a narrow flag to nativeFrame. Scene-mode calls keep exact authored milestone group, counter, and accessible heading checks. Lesson-context playback must remain on the lesson route with the lesson workspace visible; that call opts out of the scene-mode milestone assertion, then records the lesson context. The ordinary scene traversal still applies the exact scene milestone checks and full step-set coverage.

The audio-seek helper waits up to 5 seconds for exact expected screen intensity samples and all expected grid levels, checks equal lengths and every value, then calls the unchanged strict frame assertion. It adds no tolerance and is only used for timeline checks after play/seek.

The original native scene step/input/output SHA checks, qualified chunk hashes, MIDI oracles, and exact frame/grid assertions are unchanged. The frame assertion checks the decoded intensity plane and grid values, not separate RGBA channels. The parent-provided immediate RED and approximately 100 ms exact-render observation were not independently rerun here. This audit is not a test-pass claim; the live full run remains separate.

The complete bounded diff and exact manifest/source pins are in REVIEW.json and manual_book_browser-final.diff.
