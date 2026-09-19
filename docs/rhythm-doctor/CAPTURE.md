# RD-01 native owned capture spike

This is a feasibility spike, not Rhythm Doctor application behaviour.  It does
not add an algorithm button, a grid action, analysis, persistence, or any call
to Mosaic's engine, softcut, tape, monitoring, output, or transport paths.
Those integrations remain RD-03 onwards and must retain their own behaviour
evidence.

## Baseline and red evidence

The baseline is `8c08cb9` (`codex/rhythm-doctor` worktree, captured 2026-09-19).
Its tree has no `tools/rhythm_doctor/rd_capture.c` (`git cat-file -e` exits 1),
so the new contract test has no production source to compile on that revision.
This source-absence result is the red baseline and is retained rather than
being re-labelled after implementation. The source anchors to revalidate before
wiring this spike into Mosaic are:

| Source | Baseline SHA-256 |
| --- | --- |
| `mosaic.lua` | `ec614a5072c1015d8ad51b72aadf653a1a617f0d4cccc89d4ed18de76c386978` |
| `lib/pages/trigger_edit_page/trigger_edit_page.lua` | `88dc814178142567c99e0905af99a895514e78b079ad2ddc2543fecf524b18fd` |

These identify the baseline source used for the plan and are not assertions
about the current integration checkout. RD-04 must recalculate its live hashes
before it adapts the fifth algorithm path.

## API and ownership

`tools/rhythm_doctor/rd_capture.c` exposes a C ABI intended for a future native
host bridge:

| Call | Contract |
| --- | --- |
| `rd_capture_preflight(seconds)` | Opens only the already-selected JACK server (`JackNoStartServer`), registers `input_l` and `input_r`, allocates zeroed stereo float PCM, and writes every PCM page through a volatile access before activation. Valid capacity is 1â€“45 seconds at an 8â€“192 kHz server rate. A null result is NOT READY, including an absent server, allocation failure, unsupported rate, or non-lock-free 32-bit atomics. |
| `rd_capture_start()` | Arms exactly one capture. The first JACK callback that wins the arm transition records the authoritative JACK frame origin and starts copying that callback's PCM. |
| `rd_capture_stop()` | Requests completion. The next callback uses a compare-and-swap to publish COMPLETED without copying a later block; a concurrent cancel or failure wins instead. |
| `rd_capture_cancel()` | Cancels an active capture. Canceled and failed captures cannot be restarted or published. A host destroys the capture only after JACK deactivation, so callbacks cannot retain freed PCM. |
| `rd_capture_publish_wav(path)` | Only after COMPLETED, creates a same-directory unique `path.tmp.XXXXXX` with `mkstemp`, writes interleaved float32 stereo WAVE, fsyncs the file, atomically links it into a previously absent destination, then fsyncs the parent directory. Existing destinations are refused and remain unchanged. |
| getters | Expose state/error as one atomic outcome snapshot, sample rate, accepted frame count, exact sample-frame start/end timestamps, `rd_capture_preflight_nanoseconds()`, and whether both PCM buffers were successfully `mlock`ed. |

The JACK process callback makes only state checks, bounded preallocated stereo
copies, timestamp/frame updates and lock-free 32-bit atomic publication of those
fields. State and its error code are packed in one atomic word, so FAILED cannot
be observed with a stale OK error. Preflight checks each counter with
`atomic_is_lock_free`; it takes no lock and performs no allocation, filesystem
work, model work or Mosaic work.
An xrun, JACK server shutdown, or a noncontiguous callback frame changes an
active capture to FAILED with its own visible error code. The 45-second capacity
is normal completion, not overflow: the callback retains a partial final block
and atomically completes. Overflow remains a separate defensive failure for an
impossible corrupt counter. `mlock` is attempted only after prefaulting; failure
does not reject capture, but `rd_capture_pcm_locked()` exposes that weaker memory
guarantee for a visible diagnostic. The future UI must display every failure rather than
silently treating the buffer as usable.

Stopping is callback-acknowledged rather than pretending a concurrent command
can choose a fractional JACK block. Therefore the accepted PCM is always a
contiguous prefix; callback frame timestamps must equal the prior expected frame
(with defined 32-bit JACK-frame wrap), and no rolling overwrite or origin shift
occurs. This resolves RD-01's owned capture semantics, not the
specified key-down latency target. That latency needs the later native UI bridge
and a measured grid event origin. `rd_capture_preflight_nanoseconds()` measures
resource reservation separately; it is not and must never be presented as
key-down-to-first-PCM latency.

## Evidence

`test_capture_contract.py` covers command validity, first-frame timestamps,
stereo sample identity, callback-acknowledged stop, cancel-over-stop terminal
ordering, xrun failure, callback-frame discontinuity, and automatic partial-block
capacity completion through a test-only adapter that calls the same PCM copy
function as JACK.

`test_capture_native.py` launches its own uniquely named
`jackd --name rd-capture-â€¦ -d dummy` server and sets `JACK_DEFAULT_SERVER` for
only that test process and its child tools. Cleanup handlers are registered as
each resource is acquired, including setup failures. It compiles the native
client and a tiny independent JACK source, connects the source only to that
server's private input ports, captures real callbacks, and verifies float32 WAVE
stereo polarity plus every single-sample sequence delta. It also proves an absent
server name is not autostarted or substituted, tests shutdown while armed, and
checks a failed publication leaves a prior destination unchanged. Both the
capture client and injector use `JackNoStartServer`; injector setup closes its
client on every registration or activation failure. The capture client pins
callback references through shutdown/destruction, waits before freeing PCM, and
closes its JACK client after shutdown so that the server-shutdown failure path
does not leak it.
It does not enumerate, connect, stop, or alter any pre-existing JACK session.

Controlled musical time is inapplicable to raw PCM capture: JACK callback timing
and audio-frame origins are wall-clock/native-runtime properties. The contract
test provides deterministic frame-index coverage; the dedicated-JACK test is
the real-time local native-injection lane. Desktop results do not establish ARM
norns scheduling or hardware-input performance.
