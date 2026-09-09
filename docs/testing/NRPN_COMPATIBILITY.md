# NRPN compatibility investigation

Status: unresolved compatibility decision; production encoder unchanged.
User steering: the existing value adjustment was introduced after real-device experience. Do not remove it solely to satisfy the generic 14-bit oracle.

## Evidence established on 2026-09-08

Mosaic commit 4f1173ddaf7a2d310ee55f26ee5c16cf5c80e997 (2024-08-18, “Digitakt 2 tweaks”) introduced low-byte division by two in lib/midi_controller.lua. The same commit fixed NRPN calls to the five-argument CC helper by inserting the missing nil CC-LSB argument. Therefore its working result cannot isolate the effect of division alone. The present lib/m_midi.lua still uses that division for every device.

The generic byte oracle expects standard numeric reconstruction. It fails for value1 because the helper passes a fractional low byte. Native M-PATCH-007 displays126 but sends Data Entry LSB63, in both controlled and real time. These prove a mismatch against that declared generic oracle, not Digitakt incompatibility. Baseline manifests: 458e038d82b14151801f7ed3fc4834e9 and 889c74c8a665417a9625d20a6159bda8 under /home/andy/projects/mosaic-behaviour-runs. The later candidate0050 concerns startup parameter ordering, not NRPN encoding.

## External evidence and limits

- MIDI Association controller table identifies CC6/38 as Data Entry MSB/LSB: https://midi.org/midi-1-0-control-change-messages . This defines transport roles, not every receiver's parameter scaling.
- Elektron Digitakt OS1.51 Appendix B lists parameter addresses: https://www.elektron.se/wp-content/uploads/2024/09/Digitakt_User_Manual_ENG_OS1.51_231108.pdf . It is insufficient by itself to establish precise receiver value scaling or current firmware behavior.
- Firsthand Digitakt controller-development discussion provides actual reported send/receive values for LFO Speed and describes ordinary coarse/fine mapping: https://www.elektronauts.com/t/control-src-slot-on-digitakt/105468/10 . This is historical user evidence, not our physical validation or a universal Digitakt II contract.
- Firsthand Digitakt delay report includes the reporter's reproduction and a quoted Elektron support confirmation in March2022: https://www.elektronauts.com/t/nrpn-to-delay-time-data-entry-lsb-not-functioning/168499 . Fine input was ignored for delay while source tune worked. Current-firmware fix status is unverified.
- Firsthand Analog Heat reports describe receive values halved despite correct transmit values: https://www.elektronauts.com/t/nrpn-messages-are-divided-by-2/183469 . Different product and different transformation: this does not justify halving only the outgoing low byte globally.

## Required next work

Keep generic encoding tests diagnostic until transport-versus-device semantics are resolved. Preserve legacy compatibility during investigation; never edit expected data to bless current output. Audit Digitakt and DigitaktII definitions separately, with firmware identity and coarse-only versus high-resolution parameter expectations. The current original-Digitakt map uses NRPN maxima127 in many places, while DigitaktII includes16383; max alone is not a reliable bit-depth declaration. Check source tune, filter frequency, delay, sample selection, midpoint/endpoints and low-byte rollover, plus parameter switches and FX/track routing.

If a receiver adjustment is supported by evidence, express it as an explicit device/parameter mapping with a regression and migration treatment rather than changing generic emulator behavior. Before any removal of the old adjustment, conduct focused Codex arbitration using this history and the user's hardware experience. Physical-device validation has not occurred. An automated capture/replay or receiver readback would strengthen empirical claims if equipment becomes available; it is not a new manual/hardware acceptance prerequisite. Continue independent persistence/recall work meanwhile.

## User scope clarification

The user explicitly instructed: do not generalise the Digitakt issue. Investigate the historical Digitakt II adjustment for specific parameters and firmware. Original Digitakt and Analog Heat reports above are context only, not evidence for Digitakt II receiver behaviour or a shared Elektron workaround. Preserve the current production encoder pending scoped evidence and arbitration; no physical receiver validation has been performed.

The user further clarified that this allowance is NRPN-only. It does not waive CC value, slide, musical timing, recording, routing, persistence, or other defects; those remain independently subject to the normal regression and fix requirements.

## Codex arbitration and serializer characterisation

Codex policy review `01a0837a-c2da-7833-be25-527ced94bead` approved explicit
standard encoding for new generic use, an explicit historical Digitakt II map
setting, and a versioned migration preserving pre-policy saved assignments and
stored controls. The raw review is `reviews/nrpn-compatibility-policy-review.json`.
No broad receiver exception or physical-device equivalence was approved.

The pinned official `Midi.to_data` forwards CC values unchanged. Matron's
`_midi_send` uses `lua_tointeger`, which under its linked Lua5.3 library returns
zero for a non-integral number. The integration probe
`tests/behaviour/test_nrpn_legacy_serializer.py` compiled the exact extracted
native serializer and used official norns Lua conversion. It passed all 16,384
historical low-byte conversions and all 16,384 standard conversions. Thus odd
historical values send low byte zero; even values send half the low byte.
This is **not** floor(value/2), nor floor((value%128)/2).
Receipt: `nrpn-legacy-serializer.json`; raw artifacts:
`/home/andy/projects/mosaic-behaviour-runs/nrpn-legacy-serializer-03`.
The first two isolated probe runs failed module registration setup and are
retained as failures. This boundary probe is not full-runtime or receiver acceptance.

The prepared pure codec `lib/devices/nrpn_codec.lua` provides standard packing,
explicit byte-preserving `legacy-half`, strict value/mode validation, and
override/parameter/device/default precedence. It is not wired into live MIDI
emission yet: migration, stored edit/recall/lock/slide propagation, cache and
assignment lifecycle, user-visible conversion documentation, and native
regressions must be implemented together before replacing the historical path.
The existing M-PATCH-007 generic failures remain failures with unchanged oracles.

Candidate0066 now wires the codec through stored edits, Play recall and locks/slides, versions new projects, and migrates pre-policy saved assignments (including serialized undo) and unassigned stored controls. M-PATCH007 and the standard/legacy two-cold-load workflows050/051 pass controlled and real time; full484 units pass. See patch-slide-progress.json for exact receipts. Boundary/slide matrices052-056, explicit conversion workflow, missing-map treatment and implementation review remain pending. This supersedes the earlier prepared-only status above.

## Choosing and converting encoding

Device and parameter maps accept `nrpn_lsb_mode`: `standard` packs the numeric
value into two 7-bit data bytes; `legacy-half` preserves the historical byte
conversion characterised above. The bundled Digitakt II map explicitly selects
historical mode. This does not establish firmware-specific receiver behaviour
and does not apply any exception to CC or timing correctness.

Saved assignment/control choices take precedence over current map defaults.
Pre-policy projects migrate before MIDI emission. When a map is temporarily
missing, the saved channel/device identity retains a historical fallback; other
devices and new projects are unaffected. A restored map's parameters inherit
that history until explicitly converted. For known maps, only parameters present
at migration are stamped, so newly added parameters use their declared defaults.

To deliberately convert every NRPN assignment/control in a project, including
saved undo/copy state, run from the Mosaic checkout:

```sh
python3 tools/nrpn-project-mode.py --norns-source /path/to/pinned/norns --project /path/to/song.ptn --output /path/to/song-standard.ptn --mode standard
```

The command uses official norns `tabutil` and Lua5.3. It requires the original
companion PSET, writes a new `.ptn`/`.pset` pair, refuses existing output files,
and leaves the input pair unchanged. Only encoding metadata changes: numeric
lock values are preserved and the PSET is copied byte-for-byte. `--mode
legacy-half` explicitly converts the copy in the reverse direction. Conversion
is project-wide; it is not automatic receiver detection. Load the new copy normally.

The native conversion scenario M-PATCH059 verifies the new copy through actual
Mosaic controls, edits, playback and two cold loads, plus original-file and
PSET identity and overwrite refusal. Controlled validation has passed; real-time
validation and focused implementation review are pending at this checkpoint.

## Validation checkpoint

M-PATCH059 conversion now passes in both controlled and real time (real-time
`bdc320dc5dc949e3bbde91ebe5e683f1`). Codex implementation review
`01a083ab-fbb9-78b0-9fcc-68da8aec97c1` inspected the source/evidence and found one
default-Off mismatch. Native CC and NRPN baselines reproduced it; candidate0068
normalizes playback/destination/display defaults. All four requested default-Off
cases060-063 pass in both lanes, including Off during an active slide;485 full
units pass. Exact records and review limits are in `nrpn-review-resolution.json`.
The earlier no-command review response inspected no files and is not counted as
an implementation review. The wider manual campaign and emulator release remain
incomplete; this checkpoint does not certify receiver hardware or refactor readiness.
