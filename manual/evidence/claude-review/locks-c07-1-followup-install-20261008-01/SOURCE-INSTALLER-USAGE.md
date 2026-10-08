# C07-1 staged qualifier

The package includes `qualify_locks_c07_1.py`. It imports the existing guarded staged compiler and projection helpers, verifies this exact three-leaf manifest with no caption allowance, stages compilation, and checks that all 146 scenes and 167 chunks remain exact. The book and index guards allow only the three recipe text values, the two changed authoring-file hashes, the resulting authoring identity/source hashes, and `canonical_inputs.book_json_sha256`; every other book/index leaf must match. The authored `manual/audio-scenes.yaml` preimage is pinned identically in both roots, and each root’s existing generated `audio-scenes.json` is pinned separately because those generated files differ between the checkouts.

Read-only staged qualification command (the work directory must be new):

```powershell
wsl.exe -d Ubuntu-20.04 --cd /home/andy/mosaic-manual-1.4.0 -- python3 /mnt/c/Users/andy/.codex/visualizations/2026/10/03/01a100e0-e188-7c11-b2f0-748214517bb6/locks-c07-1-followup-20261008-01/qualify_locks_c07_1.py --manifest /mnt/c/Users/andy/.codex/visualizations/2026/10/03/01a100e0-e188-7c11-b2f0-748214517bb6/locks-c07-1-followup-20261008-01/manifest.json --candidate-root /mnt/c/Users/andy/.codex/visualizations/2026/10/03/01a100e0-e188-7c11-b2f0-748214517bb6/locks-c07-1-followup-20261008-01/candidate --work /home/andy/mosaic-manual-build-operators/c07-1-followup-20261008-01/work05
```

The optional `--install --reviewed-manifest-sha256 <sha256>` mode is gated on the exact manifest bytes and uses the helperâ€™s two-root backup/rollback transaction. It was not run for this proposal.
