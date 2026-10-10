"""Refresh a published audio report after an editorial-only authoring change.

An example's feature_ids say which features it belongs to; they cannot change a recording.
Instead of re-recording real-time audio, this tool re-publishes the unchanged native report with
the current authored editorial fields. It refuses any other authored difference, and the normal
publication audit (manual_audio.audit_publication) re-verifies the result against the
immutable native run, including its frozen source.yaml.
"""
import argparse
import copy
import hashlib
import json
import sys
import tempfile
from pathlib import Path

import yaml

from manual_model import MANUAL


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def refresh(expected_sha256, output=None, source=None):
    """Return the refreshed report; write it to output (atomically) only after its audit passes."""
    import manual_audio as audio
    published = MANUAL / "generated/audio-scenes.json"
    source = Path(source or MANUAL / "audio-scenes.yaml")
    if sha(published) != expected_sha256:
        raise ValueError("Audio report SHA256 does not match the explicit pin")
    report = json.loads(published.read_text())
    if report.get("publication") is not None:
        raise ValueError("Report is already an editorial publication; refresh from the native report")
    if report.get("passed") is not True or report.get("complete_regression_run") is not False:
        raise ValueError("Only a passed controlled report can be refreshed")
    native_run = Path(report["examples"][0]["evidence"]["path"]).parent
    if sha(native_run / "audio-scenes.json") != expected_sha256:
        raise ValueError("Native baseline is not the pinned report")
    authored = audio.validate(yaml.safe_load(source.read_text()))
    refreshed = copy.deepcopy(report)
    by_id = {example["id"]: example for example in authored["examples"]}
    for row in refreshed["examples"]:
        for field in audio.EDITORIAL_FIELDS:
            row[field] = copy.deepcopy(by_id[row["id"]][field])
    refreshed["source_sha256"] = sha(source)
    refreshed["publication"] = dict(
        kind="editorial-refresh",
        native_source_sha256=report["source_sha256"],
        native_report_sha256=expected_sha256,
        editorial_fields=list(audio.EDITORIAL_FIELDS),
    )
    # The audit reads the published report and current authoring; audit the candidate before replacing anything.
    with tempfile.TemporaryDirectory() as directory:
        candidate = Path(directory) / "audio-scenes.json"
        candidate.write_text(json.dumps(refreshed, indent=2) + "\n")
        audio.audit_controlled_publication(candidate)
        if output:
            temporary = Path(str(output) + ".tmp")
            temporary.write_text(candidate.read_text())
            temporary.replace(output)
    return refreshed


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-sha256", required=True)
    parser.add_argument("--output", type=Path)
    options = parser.parse_args(argv)
    refreshed = refresh(options.report_sha256, options.output)
    print(json.dumps(dict(source_sha256=refreshed["source_sha256"], publication=refreshed["publication"]), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
