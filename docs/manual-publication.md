# Manual site publication

The publisher normally uses the main-edition policy. After PR 98 is merged, release the 1.4 manual with the pr98-merged-main-promotion policy from the main branch. Supply the successful Build manual site run ID and attempt from PR 98, PR number 98, and the exact merge, PR-head, and producer-recorded main-base SHAs. Set the artifact kind to merged-pr.

This route promotes the existing PR 98 artifact; it does not rebuild the manual after merge. The publisher verifies the producer workflow, run attempt, PR association, exact source and merge identities, required source-bound CI, GitHub artifact digest, extracted file map, and that the merged tree is still the current trusted main tree. It rejects post-merge dispatch artifacts and a main tree that has changed since the merge.

The publisher checks out trusted main with credentials disabled and transfers only the verified site and receipt between jobs. Keep the repository Pages build and deployment source set to GitHub Actions.
