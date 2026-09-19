"""RD-02 Candidate B: weakly supervised fixed-template NMF pilot.

This diagnostic trains spectral templates only from original BabySlakh
development DRUM/BASS stems and literal MIDI. It is not product code.
"""
import argparse
import ctypes
import hashlib
import json
import re
import shutil
import sys
import time
from pathlib import Path

import mido
import numpy as np
import soundfile as sf
from sklearn.decomposition import non_negative_factorization

# A frozen artifact copy lives below tests/...; find the repository rather than
# assuming this module is still directly below tools/.
ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "AGENTS.md").exists())
sys.path.insert(0, str(ROOT / "tests" / "rhythm_doctor"))
from quality import onset_score

LANES = ("BD", "SD", "HH", "TOM", "BASS")
DEV = (3, 4, 5, 7, 10, 12, 13, 17, 18)
HELD = (1, 2, 6, 8, 9, 11, 14, 15, 16, 19, 20)
NOTES = {"BD": (35, 36), "SD": (37, 38, 40), "HH": (42, 44, 46),
         "TOM": (41, 43, 45, 47, 48, 50)}
HOP, TOLERANCE, WINDOW = .020, .050, 1024


def finite_audio_path(source, stage):
    """Stage UNC audio locally because Windows libsndfile rejects some UNC stems."""
    source = Path(source)
    # Both stem and mix sources are distinct by their Track000NN parent.
    target = stage / (source.parents[1].name + "-" + source.name)
    if not target.exists() or target.stat().st_size != source.stat().st_size:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return target


def stem_roles(path):
    roles, current = {"DRUM": [], "BASS": []}, None
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        match = re.match(r"^  (S\d+):", line)
        if match:
            current = match.group(1)
        if current and "is_drum: true" in line:
            roles["DRUM"].append(current)
        if current and "inst_class: Bass" in line:
            roles["BASS"].append(current)
    if len(roles["DRUM"]) != 1 or not roles["BASS"]:
        raise ValueError("missing unique DRUM or BASS metadata role: " + str(path))
    return roles


def midi_events(path, role):
    """Read literal source-MIDI note-ons; prediction output never enters labels."""
    output, seconds = [], 0.0
    for message in mido.MidiFile(path):
        seconds += message.time
        if message.type != "note_on" or not message.velocity:
            continue
        if role == "DRUM":
            lane = next((name for name, notes in NOTES.items() if message.note in notes), None)
            if lane:
                output.append((float(seconds), lane))
        elif role == "BASS":
            output.append((float(seconds), "BASS"))
    return output


def available_stems(selected, track, stem_names):
    """Keep only metadata stems with literal exported MIDI, recording no proxy."""
    return [stem for stem in stem_names if (selected / track / "MIDI" / (stem + ".mid")).is_file()]


def select_isolated_events(events, lane, radius=.15, tail_gap=.10):
    """Keep literal lane events absent a cross-lane collision or earlier tail."""
    if lane not in LANES or radius <= 0 or tail_gap <= 0:
        raise ValueError("invalid isolation arguments")
    selected = []
    for moment, event_lane in events:
        if event_lane != lane:
            continue
        cross_lane = any(other_lane != lane and abs(other - moment) <= radius
                         for other, other_lane in events)
        preceding_tail = any(moment - tail_gap <= other < moment - 1e-9
                             for other, _ in events)
        if not cross_lane and not preceding_tail:
            selected.append(moment)
    return selected


def mono_from(source, stage, seconds=None):
    local = finite_audio_path(source, stage)
    info = sf.info(local)
    frame_count = min(info.frames, int(seconds * info.samplerate)) if seconds else -1
    audio, rate = sf.read(local, frames=frame_count, always_2d=True)
    return audio.mean(axis=1, dtype=np.float64), rate


def spectrum(audio, rate, moment):
    start = int(moment * rate) - WINDOW // 4
    part = audio[max(0, start):start + WINDOW]
    part = np.pad(part, (0, max(0, WINDOW - len(part))))
    return np.maximum(np.abs(np.fft.rfft(part * np.hanning(WINDOW))), 0.0)


def template_rows(audio, rate, moments):
    return [spectrum(audio, rate, moment) for moment in moments
            if moment + WINDOW / rate < len(audio) / rate]


def make_templates(selected, stems, meta, stage):
    rows = {lane: [] for lane in LANES}
    retained = {lane: 0 for lane in LANES}
    for number in DEV:
        track = f"Track{number:05d}"
        roles = stem_roles(meta / track / "metadata.yaml")
        drum_stems = available_stems(selected, track, roles["DRUM"])
        if len(drum_stems) != 1:
            raise ValueError("missing DRUM source MIDI for " + track)
        drum_events = midi_events(selected / track / "MIDI" / (drum_stems[0] + ".mid"), "DRUM")
        drum_audio, drum_rate = mono_from(stems / track / "stems" / (roles["DRUM"][0] + ".wav"), stage)
        for lane in NOTES:
            samples = template_rows(drum_audio, drum_rate, select_isolated_events(drum_events, lane))
            rows[lane].extend(samples)
            retained[lane] += len(samples)
        for bass_stem in available_stems(selected, track, roles["BASS"]):
            bass_events = midi_events(selected / track / "MIDI" / (bass_stem + ".mid"), "BASS")
            bass_audio, bass_rate = mono_from(stems / track / "stems" / (bass_stem + ".wav"), stage)
            samples = template_rows(bass_audio, bass_rate,
                                    select_isolated_events(bass_events, "BASS", radius=.001, tail_gap=.10))
            rows["BASS"].extend(samples)
            retained["BASS"] += len(samples)
    missing = [lane for lane in LANES if not rows[lane]]
    if missing:
        raise ValueError("no isolated development templates for " + ", ".join(missing))
    components = np.vstack([np.mean(rows[lane], axis=0) for lane in LANES])
    components /= np.maximum(components.sum(axis=1, keepdims=True), 1e-12)
    return components, retained


def frames(audio, rate, seconds):
    moments = np.arange(.10, min(len(audio) / rate, seconds), HOP)
    matrix = np.vstack([spectrum(audio, rate, moment) for moment in moments])
    matrix /= np.maximum(matrix.sum(axis=1, keepdims=True), 1e-12)
    return moments, matrix


def activations(matrix, components):
    """Infer W while holding development H fixed, using NMF non-negative updates."""
    weights, _, _ = non_negative_factorization(
        matrix, H=components, n_components=len(LANES), init="custom",
        update_H=False, random_state=20260919, max_iter=80, tol=1e-4)
    return weights


def pick_peaks(values, moments, threshold, refractory=.060):
    output, prior = [], -float("inf")
    for index, value in enumerate(values):
        left = values[index - 1] if index else -float("inf")
        right = values[index + 1] if index + 1 < len(values) else -float("inf")
        if value >= threshold and value >= left and value > right and moments[index] - prior >= refractory:
            output.append(float(moments[index]))
            prior = moments[index]
    return output


def references(selected, meta, number, seconds):
    track = f"Track{number:05d}"
    result = {lane: [] for lane in LANES}
    for role, stem_names in stem_roles(meta / track / "metadata.yaml").items():
        for stem in available_stems(selected, track, stem_names):
            for moment, lane in midi_events(selected / track / "MIDI" / (stem + ".mid"), role):
                if moment < seconds:
                    result[lane].append(moment)
    return result


def unavailable_bass_midi(selected, meta, numbers):
    return [f"Track{number:05d}" for number in numbers
            if not available_stems(selected, f"Track{number:05d}",
                                   stem_roles(meta / f"Track{number:05d}" / "metadata.yaml")["BASS"])]


def track_run(selected, meta, stage, components, number, seconds):
    track = f"Track{number:05d}"
    audio, rate = mono_from(selected / track / "mix.wav", stage, seconds)
    moments, matrix = frames(audio, rate, seconds)
    return moments, activations(matrix, components), references(selected, meta, number, seconds)


def aggregate(reference_sets, prediction_by_lane):
    result = {}
    for index, lane in enumerate(LANES):
        values = [onset_score(refs[lane], predicted, TOLERANCE)
                  for refs, predicted in zip(reference_sets, prediction_by_lane[index])]
        tp, fp, fn = (sum(value[key] for value in values) for key in ("tp", "fp", "fn"))
        result[lane] = {"tp": tp, "fp": fp, "fn": fn,
                        "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 1.0}
    return result


def choose_thresholds(dev_runs):
    thresholds, diagnostics = {}, {}
    refs = [run[2] for run in dev_runs]
    for index, lane in enumerate(LANES):
        values = np.concatenate([run[1][:, index] for run in dev_runs])
        best = None
        for candidate in np.unique(np.quantile(values, np.linspace(.20, .995, 40))):
            predicted = [pick_peaks(run[1][:, index], run[0], float(candidate)) for run in dev_runs]
            metric_values = [onset_score(reference[lane], prediction, TOLERANCE)
                             for reference, prediction in zip(refs, predicted)]
            tp, fp, fn = (sum(value[key] for value in metric_values) for key in ("tp", "fp", "fn"))
            metric = {"tp": tp, "fp": fp, "fn": fn,
                      "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 1.0}
            if best is None or (metric["f1"], -float(candidate)) > (best[1]["f1"], -best[0]):
                best = (float(candidate), metric)
        thresholds[lane], diagnostics[lane] = best
    return thresholds, diagnostics


def rss_bytes():
    if sys.platform != "win32":
        return None, None
    class Counters(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
    counters = Counters(); counters.cb = ctypes.sizeof(counters)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    psapi.GetProcessMemoryInfo.argtypes = (ctypes.c_void_p, ctypes.POINTER(Counters), ctypes.c_ulong)
    psapi.GetProcessMemoryInfo.restype = ctypes.c_bool
    if not psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return int(counters.WorkingSetSize), int(counters.PeakWorkingSetSize)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--selected", type=Path, required=True)
    parser.add_argument("--stems", type=Path, required=True)
    parser.add_argument("--meta", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seconds", type=float, default=60.0)
    args = parser.parse_args()
    if args.seconds <= 0:
        raise ValueError("seconds must be positive")
    args.out.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    source_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    stage = args.out / "staged-audio"
    components, retained = make_templates(args.selected, args.stems, args.meta, stage)
    dev_runs = [track_run(args.selected, args.meta, stage, components, number, args.seconds) for number in DEV]
    thresholds, dev_metrics = choose_thresholds(dev_runs)
    held_runs = [track_run(args.selected, args.meta, stage, components, number, args.seconds) for number in HELD]
    held_predictions = [[pick_peaks(run[1][:, index], run[0], thresholds[lane]) for run in held_runs]
                        for index, lane in enumerate(LANES)]
    np.save(args.out / "fixed_components.npy", components)
    current_rss, peak_rss = rss_bytes()
    report = {"kind": "candidate_b_weak_template_fixed_nmf_pilot", "acceptance_claimed": False,
              "source_sha256": source_hash, "seed": 20260919, "development_tracks": list(DEV),
              "held_tracks": list(HELD), "analysis_seconds_per_track": args.seconds,
              "template_window": {"other_lane_radius_seconds": .15, "preceding_tail_gap_seconds": .10},
              "template_counts": retained, "thresholds_development_only": thresholds,
              "development_threshold_metrics": dev_metrics,
              "unavailable_bass_midi_development": unavailable_bass_midi(args.selected, args.meta, DEV),
              "unavailable_bass_midi_held": unavailable_bass_midi(args.selected, args.meta, HELD),
              "held_onset_metrics": aggregate([run[2] for run in held_runs], held_predictions),
              "wall_seconds": time.perf_counter() - started, "rss_bytes_end": current_rss,
              "rss_bytes_peak_process": peak_rss,
              "limitations": ["Aggregate DRUM templates are weak MIDI-window supervision, not lane-isolated audio.",
                              "Missing exported Bass MIDI is excluded rather than relabelled from audio.",
                              "Thresholds are in-sample development choices; held pilot is not an acceptance corpus.",
                              "No grid-F1 or device inference claim is made."]}
    (args.out / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
