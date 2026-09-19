"""Create a resumable external BabySlakh preliminary corpus.

This intentionally produces a *preliminary* rendered-domain corpus.  It never
uses detector output for labels and writes a separate gate report rather than
claiming RD-02 acceptance.  Run from WSL with a cache root, never inside git.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import wave
from pathlib import Path

import yaml

SCHEMA_VERSION = 2
LANES = ("BD", "SD", "CHH", "OHH", "BASS")
DEV = (3, 4, 5, 7, 10, 12, 13, 17, 18)
HELD = (1, 2, 6, 8, 9, 11, 14, 15, 16, 19, 20)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def vlq(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    while True:
        byte = data[offset]
        offset += 1
        value = (value << 7) | (byte & 127)
        if not byte & 128:
            return value, offset


def midi_events(path: Path) -> tuple[list[tuple[float, int, int]], float]:
    """Return (seconds, note, velocity), using frozen MIDI tempo events."""
    data = path.read_bytes()
    if data[:4] != b"MThd":
        raise ValueError(f"not MIDI: {path}")
    tracks, division = struct.unpack(">HH", data[10:14])
    offset, raw, tempos = 14, [], []
    for _ in range(tracks):
        if data[offset : offset + 4] != b"MTrk":
            raise ValueError(f"bad MIDI track: {path}")
        end = offset + 8 + struct.unpack(">I", data[offset + 4 : offset + 8])[0]
        offset += 8
        tick, status = 0, None
        while offset < end:
            delta, offset = vlq(data, offset)
            tick += delta
            first = data[offset]
            if first >= 128:
                status = first
                offset += 1
            else:
                first = status
            if first == 255:
                kind = data[offset]
                offset += 1
                size, offset = vlq(data, offset)
                payload = data[offset : offset + size]
                offset += size
                if kind == 81 and size == 3:
                    tempos.append((tick, int.from_bytes(payload, "big")))
                continue
            if first in (240, 247):
                size, offset = vlq(data, offset)
                offset += size
                continue
            kind = first & 240
            size = 1 if kind in (192, 208) else 2
            payload = data[offset : offset + size]
            offset += size
            if kind == 144 and size == 2 and payload[1]:
                raw.append((tick, payload[0], payload[1]))
    tempos = sorted(tempos) or [(0, 500000)]

    def seconds(tick: int) -> float:
        total, prior_tick, tempo = 0.0, 0, 500000
        for changed_at, changed_to in tempos:
            if changed_at > tick:
                break
            total += (changed_at - prior_tick) * tempo / division / 1_000_000
            prior_tick, tempo = changed_at, changed_to
        return total + (tick - prior_tick) * tempo / division / 1_000_000

    return [(seconds(tick), note, velocity) for tick, note, velocity in raw], 60_000_000 / tempos[0][1]


def drum_lane(note: int) -> str | None:
    if note in (35, 36): return "BD"
    if note in (37, 38, 40): return "SD"
    if note in (42, 44): return "CHH"
    if note == 46: return "OHH"
    return None


def materialize(cache: Path, output: Path) -> Path:
    metadata_root = cache / "slakh/babyslakh-meta/babyslakh_16k"
    data_root = cache / "slakh/babyslakh-selected/babyslakh_16k"
    output.mkdir(parents=True, exist_ok=True)
    for part in ("audio", "annotations", "recipes", "timbres"):
        (output / part).mkdir(exist_ok=True)
    hash_cache: dict[Path, str] = {}
    def descriptor(path: Path) -> dict[str, str]:
        hash_cache.setdefault(path, sha256(path))
        return {"path": str(path.relative_to(cache)).replace("\\", "/"), "sha256": hash_cache[path]}

    def source(track_number: int):
        track = f"Track{track_number:05d}"
        metadata = yaml.safe_load((metadata_root / track / "metadata.yaml").read_text())
        events = {lane: [] for lane in LANES}
        bpm = None
        for stem, details in metadata["stems"].items():
            midi = data_root / track / "MIDI" / f"{stem}.mid"
            if not midi.exists(): continue
            notes, tempo = midi_events(midi)
            bpm = bpm or tempo
            if details.get("is_drum"):
                for time, note, velocity in notes:
                    if lane := drum_lane(note): events[lane].append((time, velocity))
            elif details.get("inst_class") == "Bass":
                events["BASS"].extend((time, velocity) for time, _note, velocity in notes)
        for lane in LANES: events[lane].sort()
        kit = next(details.get("plugin_name") for details in metadata["stems"].values() if details.get("is_drum"))
        return track, metadata["UUID"], kit, bpm or 120, events

    def candidates(track_number: int):
        track, song, kit, bpm, events = source(track_number)
        original = data_root / track / "mix.wav"
        with wave.open(str(original), "rb") as input_wav:
            duration = input_wav.getnframes() / input_wav.getframerate()
        span, bar, start, previous, result = 960 / bpm, 240 / bpm, 0.0, -1e99, []
        while start + span <= duration:
            selected = {lane: [(time - start, velocity) for time, velocity in events[lane] if start <= time < start + span] for lane in LANES}
            if all(selected.values()) and start - previous > span + 0.005:
                result.append((track, song, kit, bpm, start, span, selected))
                previous = start
            start += bar
        return result

    def select(numbers: tuple[int, ...], count: int):
        pools = [candidates(number) for number in numbers]
        pools = [pool for pool in pools if pool]
        if not pools: raise RuntimeError("no eligible four-bar windows")
        selected, cursor = [], 0
        while len(selected) < count:
            pool = pools[cursor % len(pools)]
            if pool: selected.append(pool.pop(0))
            cursor += 1
            if cursor > 100_000: raise RuntimeError(f"only {len(selected)} eligible windows")
        return selected

    def write(split: str, index: int, fixture):
        track, song, kit, bpm, start, span, events = fixture
        ident = f"prelim-{split}-{index:02d}"
        original, audio = data_root / track / "mix.wav", output / "audio" / f"{ident}.wav"
        if not audio.exists():
            with wave.open(str(original), "rb") as input_wav:
                rate = input_wav.getframerate()
                input_wav.setpos(round(start * rate))
                frames = input_wav.readframes(round(span * rate))
                with wave.open(str(audio), "wb") as cropped:
                    cropped.setparams(input_wav.getparams())
                    cropped.writeframes(frames)
        annotation = output / "annotations" / f"{ident}.json"
        if not annotation.exists(): annotation.write_text(json.dumps({"reference_origin":"independent_render_metadata", "annotator_id":"babyslakh-midi-v1", "events": {lane:[{"time_seconds":round(time,9),"velocity":velocity} for time, velocity in events[lane]] for lane in LANES}}, sort_keys=True) + "\n")
        recipe = output / "recipes" / f"{ident}.json"
        if not recipe.exists(): recipe.write_text(json.dumps({"kind":"source_mix", "source_track":track, "source_mix_sha256":descriptor(original)["sha256"], "source_start_seconds":start, "duration_seconds":span, "operation":"PCM frame crop; no classifier output"}, sort_keys=True) + "\n")
        evidence = output / "timbres" / f"{ident}.json"
        if not evidence.exists(): evidence.write_text(json.dumps({"lanes": {lane:{"timbre":"unverified","basis":"source_patch_metadata","source":f"{track}/metadata.yaml; no acoustic/electronic classification frozen"} for lane in LANES}}, sort_keys=True) + "\n")
        return {"id":ident,"split":split,"source_id":"babyslakh-v2","source_song_id":song,"kit_id":kit,"source_start_seconds":round(start,9),"render":{"kind":"source_mix","recipe":descriptor(recipe)},"audio":descriptor(audio),"annotation":descriptor(annotation),"timbre_evidence":descriptor(evidence),"duration_seconds":round(span,9),"bpm":round(bpm,6),"stratum":"full_mix","timbres":{lane:"unverified" for lane in LANES},"tags":["preliminary","rendered_domain"]}

    clips = [write("development", index, fixture) for index, fixture in enumerate(select(DEV, 40))]
    clips += [write("held_out", index, fixture) for index, fixture in enumerate(select(HELD, 40))]
    manifest = {"schema_version":SCHEMA_VERSION,"corpus_id":"rd02-babyslakh-preliminary-schema-v2","sources":[{"id":"babyslakh-v2","record_url":"https://zenodo.org/records/4603870","license":{"spdx":"CC-BY-4.0","url":"https://creativecommons.org/licenses/by/4.0/"},"archive":descriptor(cache / "slakh/babyslakh_16k.tar.gz"),"license_evidence":descriptor(cache / "slakh/zenodo-4603870-record.json"),"domain":"rendered"}],"clips":clips}
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    (output / "gate-report.json").write_text(json.dumps({"accepted":False,"structural_gaps":["all clips are full_mix", "all lane timbres are unverified", "no silence/clipping/phase-inverted/kick+bass controls", "no acquisition fixtures", "rendered-domain only"],"manifest":str(manifest_path)}, indent=2) + "\n")
    return manifest_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("cache", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    print(materialize(arguments.cache, arguments.output))
