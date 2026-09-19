"""Add licensed AVP vocal-percussion isolated fixtures without relabelling them.

This produces v4 alongside, never in place of, a preliminary BabySlakh corpus.
The AVP material is a recorded vocal-percussion source.  Its published per-class
recordings and CSV annotations identify kick, snare, and closed hi-hat gestures;
the four-bar references below are the frozen render schedules, not detector output.
It deliberately does not manufacture a TOM label or an acoustic/electronic label.
"""
import argparse
import audioop
import hashlib
import json
import wave
from pathlib import Path

LANES = ("BD", "SD", "HH", "TOM", "BASS")


def sha(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def desc(root, path):
    return {"path": str(path.relative_to(root)).replace("\\", "/"), "sha256": sha(path)}


def first_onset(path):
    line = path.read_text(encoding="utf-8").splitlines()[0]
    return float(line.split(",", 1)[0])


def hit_segment(source, onset):
    with wave.open(str(source), "rb") as inp:
        params = inp.getparams()
        start = max(0, int((onset - 0.015) * params.framerate))
        inp.setpos(start)
        return params, inp.readframes(max(1, int(0.18 * params.framerate)))


def schedule(source, onset, target):
    params, hit = hit_segment(source, onset)
    total = params.framerate * 8  # four bars at 120 BPM
    frame_width = params.sampwidth * params.nchannels
    raw = bytearray(total * frame_width)
    event_times = [float(value) for value in range(8)]
    for time in event_times:
        offset = int(time * params.framerate) * frame_width
        raw[offset:offset + len(hit)] = hit[:len(raw) - offset]
    with wave.open(str(target), "wb") as out:
        out.setparams(params)
        out.writeframes(raw)
    return event_times


def main(root, v3, v4):
    v4.mkdir(parents=True, exist_ok=True)
    for part in ("audio", "annotations", "recipes", "timbres"):
        (v4 / part).mkdir(exist_ok=True)
    manifest = json.loads((v3 / "manifest.json").read_text(encoding="utf-8"))
    # v2/v3 controls reused a source interval verbatim.  Retain their immutable
    # directories for investigation, but do not carry that overlap into v4's
    # acceptance candidate.  New controls below have their own source recording.
    excluded_overlap = [clip["id"] for clip in manifest["clips"]
                        if clip["id"].startswith("control-") or clip["id"].startswith("v3-")]
    manifest["clips"] = [clip for clip in manifest["clips"] if clip["id"] not in excluded_overlap]
    # A crop covers [start, start + duration).  Preserve v1--v3 unchanged, but
    # pin corrected references in v4 when a source MIDI event is exactly at the
    # right endpoint (and therefore outside the frozen PCM crop).
    corrected = 0
    for clip in manifest["clips"]:
        original = root / clip["annotation"]["path"]
        payload = json.loads(original.read_text(encoding="utf-8"))
        bounded = {lane: [event for event in events
                          if event["time_seconds"] < clip["duration_seconds"]]
                   for lane, events in payload["events"].items()}
        if bounded != payload["events"]:
            corrected += 1
            payload["events"] = bounded
            annotation = v4 / "annotations" / f"{clip['id']}-bounded.json"
            annotation.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
            clip["annotation"] = desc(root, annotation)
    archive = root / "avp" / "AVP-LVT_Dataset.zip"
    evidence = root / "avp" / "record-5578744.json"
    manifest["sources"].append({
        "id": "avp-lvt-v1",
        "record_url": "https://zenodo.org/records/5578744",
        "license": {"spdx": "CC-BY-4.0", "url": "https://creativecommons.org/licenses/by/4.0/"},
        "archive": desc(root, archive),
        "license_evidence": desc(root, evidence),
        "domain": "recorded",
    })
    avp = root / "avp" / "unpacked" / "AVP-LVT_Dataset" / "AVP_Dataset" / "Personal"
    specs = (("BD", "Kick", 1), ("BD", "Kick", 2), ("SD", "Snare", 3),
             ("SD", "Snare", 4), ("HH", "HHclosed", 5), ("HH", "HHclosed", 6))
    created = []
    for index, (lane, label, participant) in enumerate(specs):
        folder = avp / f"Participant_{participant}"
        stem = f"P{participant}_{label}_Personal"
        source = folder / f"{stem}.wav"
        csv = folder / f"{stem}.csv"
        onset = first_onset(csv)
        identity = f"avp-p{participant}-{label.lower()}"
        clip_id = f"v4-avp-isolated-{lane.lower()}-{index:02d}"
        audio = v4 / "audio" / f"{clip_id}.wav"
        schedule_times = schedule(source, onset, audio)
        events = {name: [] for name in LANES}
        events[lane] = [{"time_seconds": time, "velocity": 100} for time in schedule_times]
        annotation = v4 / "annotations" / f"{clip_id}.json"
        annotation.write_text(json.dumps({
            "reference_origin": "independent_render_metadata",
            "annotator_id": "avp-published-class-csv-plus-frozen-render-v1",
            "events": events,
        }, sort_keys=True) + "\n", encoding="utf-8")
        recipe = v4 / "recipes" / f"{clip_id}.json"
        recipe.write_text(json.dumps({
            "kind": "isolated_stem",
            "original_recording": str(source.relative_to(root)).replace("\\", "/"),
            "published_annotation": str(csv.relative_to(root)).replace("\\", "/"),
            "published_class": label,
            "source_onset_seconds": onset,
            "operation": "repeat a 180 ms original recorded gesture at frozen 1-second schedule; no model separation",
        }, sort_keys=True) + "\n", encoding="utf-8")
        timbre = {name: {"timbre": "unverified", "basis": "source_render_spec",
                         "source": "AVP-LVT is recorded vocal percussion; it does not establish acoustic/electronic instrument timbre"}
                  for name in LANES}
        evidence_path = v4 / "timbres" / f"{clip_id}.json"
        evidence_path.write_text(json.dumps({"lanes": timbre}, sort_keys=True) + "\n", encoding="utf-8")
        created.append({
            "id": clip_id, "split": "held_out", "source_id": "avp-lvt-v1",
            "source_song_id": identity, "kit_id": f"avp-participant-{participant}",
            "source_start_seconds": onset, "render": {"kind": "isolated_stem", "recipe": desc(root, recipe)},
            "audio": desc(root, audio), "annotation": desc(root, annotation),
            "timbre_evidence": desc(root, evidence_path), "duration_seconds": 8.0, "bpm": 120.0,
            "stratum": "isolated", "timbres": {name: "unverified" for name in LANES},
            "tags": ["preliminary", "recorded_vocal_percussion", "isolated_render_schedule"],
        })
    # Controls use otherwise unused AVP participants so each gets a disjoint
    # original recording identity.  They are explicit synthetic perturbations,
    # not evidence of musical-mixture realism.
    control_specs = (("clipping", "BD", "Kick", 7), ("phase_inverted_stereo", "SD", "Snare", 8))
    for index, (tag, lane, label, participant) in enumerate(control_specs):
        folder = avp / f"Participant_{participant}"
        stem = f"P{participant}_{label}_Personal"
        source, csv = folder / f"{stem}.wav", folder / f"{stem}.csv"
        onset, clip_id = first_onset(csv), f"v4-avp-control-{tag}"
        audio = v4 / "audio" / f"{clip_id}.wav"
        times = schedule(source, onset, audio)
        with wave.open(str(audio), "rb") as inp:
            params, raw = inp.getparams(), inp.readframes(inp.getnframes())
        if tag == "clipping":
            raw = audioop.mul(raw, params.sampwidth, 4.0)
            with wave.open(str(audio), "wb") as out: out.setparams(params); out.writeframes(raw)
            operation = "four-times gain with integer PCM saturation"
        else:
            mono = raw if params.nchannels == 1 else audioop.tomono(raw, params.sampwidth, .5, .5)
            raw = audioop.tostereo(mono, params.sampwidth, 1, -1)
            params = params._replace(nchannels=2)
            with wave.open(str(audio), "wb") as out: out.setparams(params); out.writeframes(raw)
            operation = "left original, right exact polarity inversion"
        events = {name: [] for name in LANES}; events[lane] = [{"time_seconds": time, "velocity": 100} for time in times]
        annotation, recipe, evidence_path = (v4 / "annotations" / f"{clip_id}.json",
            v4 / "recipes" / f"{clip_id}.json", v4 / "timbres" / f"{clip_id}.json")
        annotation.write_text(json.dumps({"reference_origin":"independent_render_metadata", "annotator_id":"avp-published-class-csv-plus-frozen-render-v1", "events":events}, sort_keys=True)+"\n")
        recipe.write_text(json.dumps({"kind":"isolated_stem", "original_recording":str(source.relative_to(root)).replace("\\", "/"), "published_annotation":str(csv.relative_to(root)).replace("\\", "/"), "operation":operation}, sort_keys=True)+"\n")
        evidence_path.write_text(json.dumps({"lanes":{name:{"timbre":"unverified", "basis":"source_render_spec", "source":"AVP-LVT recorded vocal percussion; no acoustic/electronic instrument timbre claim"} for name in LANES}}, sort_keys=True)+"\n")
        created.append({"id":clip_id,"split":"held_out","source_id":"avp-lvt-v1","source_song_id":f"avp-p{participant}-{label.lower()}","kit_id":f"avp-participant-{participant}","source_start_seconds":onset,"render":{"kind":"isolated_stem","recipe":desc(root,recipe)},"audio":desc(root,audio),"annotation":desc(root,annotation),"timbre_evidence":desc(root,evidence_path),"duration_seconds":8.0,"bpm":120.0,"stratum":"isolated","timbres":{name:"unverified" for name in LANES},"tags":["preliminary","recorded_vocal_percussion",tag]})
    for index, participant in enumerate((9, 10, 11)):
        clip_id, audio = f"v4-silence-{index:02d}", v4 / "audio" / f"v4-silence-{index:02d}.wav"
        with wave.open(str(avp / "Participant_7" / "P7_Kick_Personal.wav"), "rb") as source:
            params = source.getparams()
        with wave.open(str(audio), "wb") as out: out.setparams(params); out.writeframes(bytes(params.framerate * 8 * params.sampwidth * params.nchannels))
        events = {name:[] for name in LANES}; annotation, recipe, evidence_path = (v4 / "annotations" / f"{clip_id}.json",v4 / "recipes" / f"{clip_id}.json",v4 / "timbres" / f"{clip_id}.json")
        annotation.write_text(json.dumps({"reference_origin":"independent_render_metadata","annotator_id":"frozen-silence-render-v1","events":events},sort_keys=True)+"\n")
        recipe.write_text(json.dumps({"kind":"frozen_submix","operation":"8 seconds of zero PCM; no source audio"},sort_keys=True)+"\n")
        evidence_path.write_text(json.dumps({"lanes":{name:{"timbre":"unverified","basis":"source_render_spec","source":"zero PCM control has no instrument timbre"} for name in LANES}},sort_keys=True)+"\n")
        created.append({"id":clip_id,"split":"held_out","source_id":"avp-lvt-v1","source_song_id":f"silence-control-{index}","kit_id":f"silence-control-{index}","source_start_seconds":0.0,"render":{"kind":"frozen_submix","recipe":desc(root,recipe)},"audio":desc(root,audio),"annotation":desc(root,annotation),"timbre_evidence":desc(root,evidence_path),"duration_seconds":8.0,"bpm":120.0,"stratum":"full_mix","timbres":{name:"unverified" for name in LANES},"tags":["preliminary","silence"]})
    manifest["corpus_id"] = "rd02-babyslakh-avp-preliminary-v4"
    manifest["clips"] += created
    (v4 / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = {
        "accepted": False,
        "created": {"held_isolated_BD": 2, "held_isolated_SD": 2, "held_isolated_HH": 2,
                    "disjoint_clipping_phase_silence_controls": 5,
                    "v1_to_v3_endpoint_annotation_corrections": corrected,
                    "excluded_overlapping_v2_v3_variants": len(excluded_overlap)},
        "truth": "CC-BY AVP original recorded vocal-percussion gestures with published class CSVs and frozen independent render schedules",
        "unresolved": [
            "no TOM source or isolated TOM fixture", "AVP is vocal percussion, not an acoustic/electronic drum timbre assertion",
            "all corpus timbres remain unverified", "long acquisition fixtures and complete lane-negative inventory absent",
            "these isolated renders do not establish mixed-music quality",
        ],
    }
    (v4 / "gate-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(v4 / "manifest.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("v3", type=Path)
    parser.add_argument("v4", type=Path)
    args = parser.parse_args()
    main(args.root, args.v3, args.v4)
