"""Pinned manual CI audio-source and runtime command contracts."""
import argparse
import json
import subprocess
from pathlib import Path

VOICE_PINS = {
    "oilcan": ("https://github.com/zjb-s/oilcan.git", "257915f433c7d2c32b2b09c4fe5eed5434a16de5"),
    "nb_polyperc": ("https://github.com/dstroud/nb_polyperc.git", "714bd0c5b811f7cb21b7a7b8340891ffee4b5670"),
    "doubledecker": ("https://github.com/sixolet/doubledecker.git", "8729b9ceee71d2b07067e89fbef5d8b98d6a0c89"),
}
MODULATION_PINS = {
    "matrix": ("https://github.com/sixolet/matrix.git", "41e11286bee8dbe48e8746e7a456400f93dc739a"),
    "toolkit": ("https://github.com/sixolet/toolkit.git", "2e9fb56fe7b2b25bd6a0d80c40e82f7a7f9368a7"),
}


def validate_voice_lock(path):
    lock = json.loads(Path(path).read_text(encoding="utf-8"))
    for name, (url, commit) in VOICE_PINS.items():
        value = lock.get(name)
        if not isinstance(value, dict) or value.get("url") != url or value.get("commit") != commit:
            raise ValueError("Voice lock differs from the allowed manual audio pin: " + name)
    return dict(VOICE_PINS)


def clone_pins(pins, destination):
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=True)
    for name, (url, commit) in pins.items():
        target = root / name
        if target.exists() or target.is_symlink():
            raise ValueError("Pinned source destination already exists: " + name)
        subprocess.check_call(["git", "clone", "--no-checkout", url, str(target)])
        subprocess.check_call(["git", "-C", str(target), "checkout", "--detach", commit])
        actual = subprocess.check_output(["git", "-C", str(target), "rev-parse", "HEAD"], text=True).strip()
        if actual != commit:
            raise ValueError("Pinned source SHA mismatch: " + name)


def audio_runtime_commands(emulator, build_output, monitor_output):
    return [
        ["python3", "scripts/build_audio_candidate.py", "--output", str(build_output),
         "--sdl-ownership", "--screen-worker-shutdown"],
        ["python3", str(Path(emulator) / "scripts/prepare_audio_monitor.py"),
         "--install", str(Path(build_output) / "installation.json"), "--output", str(monitor_output)],
    ]


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    voices = sub.add_parser("clone-voices")
    voices.add_argument("--lock", required=True)
    voices.add_argument("--output", required=True)
    mods = sub.add_parser("clone-modulation")
    mods.add_argument("--output", required=True)
    audio = sub.add_parser("build-audio")
    audio.add_argument("--emulator", required=True)
    audio.add_argument("--output", required=True)
    audio.add_argument("--monitor-output", required=True)
    args = parser.parse_args()
    if args.command == "clone-voices":
        clone_pins(validate_voice_lock(args.lock), args.output)
    elif args.command == "clone-modulation":
        clone_pins(MODULATION_PINS, args.output)
    else:
        first, second = audio_runtime_commands(args.emulator, args.output, args.monitor_output)
        subprocess.check_call(first, cwd=args.emulator)
        subprocess.check_call(second)


if __name__ == "__main__":
    main()