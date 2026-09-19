# Incident: SSH control master lost during the slides-16 pulse-advance cell

Date 2026-09-18. Deployed source ed969ec, case PERF-003-HW-16, lead 25, seed
20260919, contract pulse-advance.

The run reached its measurement phase and then the shared SSH control master at
/tmp/mosaic-network-diagnosis.sock disappeared. The on-device resource sampler's
SSH call returned 255, which propagated out of run_hardware_performance, and the
runner's own restore step could not reach the device either. The runner raised
"Restoration failed; stop all further measurement" rather than reporting a
result, which is the correct behaviour.

The device was left with the test build active: the
/home/we/.cache/mosaic-real-norns/active marker was present and the deployed
directory mtime was 1789751712.

The link itself was healthy throughout: three of three pings at about 1.6 ms
immediately afterwards. This was the control master expiring, not a network
failure, and it is the same failure mode recorded earlier in this project.

Recovery: a new control master was established on /tmp/mosaic-slides-restore.sock
through a temporary askpass file that was deleted in the same command, then
restore_with_stock_errors.py ran to completion. Verified afterwards: marker
absent, norns-jack/matron/crone/maiden all active, directory mtime back to
1789654247, mosaic.lua sha256 back to ec614a5072c1015d..., four stock C output
bindings and stock Lua midi.event at core/midi.lua:461.

No measurement was produced, so slides-16 under pulse-advance remains unmeasured
on this source. Exit status zero from any part of this run would not have been
evidence of a passing gate, and none is claimed.
