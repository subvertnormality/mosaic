# Fresh rendered review: six affected units

This is a fresh visual review of the candidate `projection-v02` in the running reader at `http://127.0.0.1:8785/manual/`. The browser intercepted the candidate generated reader index and four scene chunks; the index SHA-256 is `785d690e479df305ff4eb6a5082b592382570e388360ddf7e8a53a89ac72a701`. All six routes reached their expected canonical fragment. The reader displayed the unit titles and captured states, and the browser recorded no page or console errors.

Five course units still show the Sound Sources cross-reference as literal Markdown (`[Norns Sound Sources with n.b.](#norns-sound-sources-with-n-b)`) in their starting-point prose. The underlying visible navigation does not turn that sentence into a link. This directly weakens understandability and usefulness for the installation prerequisite. I scored those five at 7 for understandability and kept the remaining criteria at or above 8. The Polyperc apply-confirm page is readable and retains the expected pending selection and K3 confirmation prompt.

| Unit | Scores in criterion order | Result |
|---|---|---|
| getting-started-objects | 9, 8, 8, 8, 8, 9, 9, 7, 8, 8 | Below threshold |
| getting-started-notation | 9, 9, 9, 8, 8, 9, 9, 7, 9, 8 | Below threshold |
| setup-route | 9, 9, 9, 8, 8, 9, 8, 7, 9, 8 | Below threshold |
| setup-apply | 9, 9, 9, 8, 8, 9, 9, 7, 9, 8 | Below threshold |
| setup-tempo | 9, 9, 9, 8, 8, 9, 9, 7, 8, 8 | Below threshold |
| play-polyperc-apply-confirm | 9, 9, 8, 9, 8, 8, 8, 8, 8, 8 | Meets threshold |

Criterion order: canonical home, coherence, flow, granularity, integration, naming, representation, understandability, usefulness, vocabulary. See `fresh-review.json` for route observations and evidence references. The route screenshots are in `evidence-v04/`; the earlier v02/v03 failed harness reports remain preserved.
