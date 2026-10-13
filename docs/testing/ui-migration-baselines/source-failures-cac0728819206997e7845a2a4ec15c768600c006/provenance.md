# Preserved forwarded-clock baseline failures

These source-identified captures were made from Mosaic revision `cac0728819206997e7845a2a4ec15c768600c006` before any contract extraction. Both M-SYNC-012 attempts failed the existing 10 ms real-time onset-phase assertion (26.622324 ms and 26.540223 ms). M-SYNC-013 timed out in the emulator client's encoder action while navigating to the second MIDI output. The per-attempt manifests, recipes, and results are preserved under their case and attempt directories.

`forwarded_clock.py`, its registry entries, and its allowlist entry are left unchanged. These captures are failure evidence, not accepted migration baselines.
