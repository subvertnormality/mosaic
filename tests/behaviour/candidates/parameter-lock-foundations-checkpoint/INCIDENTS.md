# Diagnostic incidents

2026-09-18, probe smoke `e7edad3`: device tar extraction reports source file
timestamps roughly 9,000 seconds in the future relative to the device wall clock.
Full warnings remain in the diagnostic's `off.log`. No clock was changed. Source
content verification uses SHA-256; this smoke cannot qualify capture-clock timing.

The earlier emulator attempt failed at startup because the isolated copy lacked
the pinned n.b. submodule. Its original manifest is preserved separately. Seeding
the exact gitlink resolved that setup failure without modifying the emulator.

Full `pulse-v1` smoke captured complete spans without overflow, and all four
windows passed the existing dispatch gates. However, probe-on p95 jitter was
2.48–2.52 ms versus 0.87–1.21 ms off; CPU was 36.17–39.18% versus 33.64–34.32%.
This does not qualify the probe's overhead. The off/off/on/on smoke is not the
predeclared interleaved ten-window campaign, so differences do not prove causality.
Retain all traces, including startup/stop tails; do not treat their correlations
as unperturbed measurements. A reduced scope was subsequently added for further
testing, without changing production scheduling or relaxing thresholds.
