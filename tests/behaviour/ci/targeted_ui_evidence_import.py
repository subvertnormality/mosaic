"""Import SHA-bound targeted CI evidence without claiming full-suite coverage.

Harness characterisation outside README. Only the uploaded recipe/results subset
can be revalidated offline; CI validated the full manifest inventory before upload.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ui_baseline_import import files_under, no_symlink, read_bytes, safe_relative


SHA = re.compile(r"[0-9a-f]{40}\Z")
CASE = re.compile(r"M-[A-Z0-9][A-Z0-9.-]*\Z")
LANES = {"real-time": "real-time", "controlled-experimental": "controlled"}
SIDES = ("before", "after")
NAMES = {"recipe.json", "results.json"}
PRESERVED_SIDECARS = {"fractional-clock-input-evidence.json"}
PROFILES = ("base-midi", "midi-modulation")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key: " + key)
        result[key] = value
    return result


def json_object(data, label):
    try:
        value = json.loads(data, object_pairs_hook=unique_object)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("invalid JSON %s: %s" % (label, error)) from error
    require(isinstance(value, dict), "expected JSON object: " + str(label))
    return value


def report_root(download):
    reports = [path for path in files_under(download)
               if path.name == "targeted-ui-migration.json"]
    require(len(reports) == 1, "expected exactly one targeted UI report")
    return reports[0].parent, reports[0]


def pair_payload(manifest, session):
    entries = manifest.get("artifacts")
    require(isinstance(entries, list), "missing manifest artifact inventory")
    listed = {}
    for entry in entries:
        require(isinstance(entry, dict), "invalid artifact entry")
        path = safe_relative(entry.get("path"))
        key = path.as_posix()
        require(key not in listed, "duplicate artifact entry: " + key)
        listed[key] = entry
    pairs = {key: value for key, value in listed.items()
             if Path(key).name in NAMES | PRESERVED_SIDECARS}
    recipes = {str(Path(key).parent) for key in pairs if Path(key).name == "recipe.json"}
    results = {str(Path(key).parent) for key in pairs if Path(key).name == "results.json"}
    require(recipes == results and "." in recipes,
            "missing or unmatched root/nested recipe/results pairs")
    actual = {path.relative_to(session).as_posix() for path in files_under(session)
              if path.name in NAMES | PRESERVED_SIDECARS}
    require(actual == set(pairs),
            "downloaded recipe/results/sidecar set differs from manifest")
    payload = {}
    for key, entry in sorted(pairs.items()):
        raw = read_bytes(session / safe_relative(key))
        require(type(entry.get("size")) is int and len(raw) == entry["size"]
                and digest(raw) == entry.get("sha256"),
                "evidence size/digest differs: " + key)
        if Path(key).name in PRESERVED_SIDECARS:
            json_object(raw, key)
            payload[key] = raw
            continue
        try:
            values = json.loads(raw, object_pairs_hook=unique_object)
        except (UnicodeError, json.JSONDecodeError) as error:
            raise ValueError("invalid evidence JSON %s: %s" % (key, error)) from error
        field = "type" if Path(key).name == "recipe.json" else "kind"
        require(isinstance(values, list) and all(
            isinstance(value, dict) and isinstance(value.get(field), str)
            and value[field] for value in values),
            "invalid evidence entries: " + key)
        payload[key] = raw
    return payload


def import_targeted(download, output, run_id, before_sha, after_sha, case_ids,
                    dry_run=False, profile="base-midi"):
    """Validate the entire selected artifact before creating any destination."""
    require(isinstance(run_id, str) and re.fullmatch(r"[1-9][0-9]*", run_id),
            "run ID must be a positive decimal number")
    require(all(isinstance(sha, str) and SHA.fullmatch(sha)
                for sha in (before_sha, after_sha)) and before_sha != after_sha,
            "expected distinct full 40-character source SHAs")
    require(profile in PROFILES,
            "invalid profile")
    require(isinstance(case_ids, list) and case_ids
            and all(isinstance(case, str) and CASE.fullmatch(case) for case in case_ids)
            and len(set(case_ids)) == len(case_ids), "invalid or duplicate selected cases")
    download, output = no_symlink(download), no_symlink(output)
    require(download != output and download not in output.parents
            and output not in download.parents, "download and output must be disjoint")
    root, report_path = report_root(download)
    report_raw = read_bytes(report_path)
    report = json_object(report_raw, report_path)
    require(report.get("schema_version") == 1 and report.get("passed") is True
            and report.get("complete_regression_run") is False,
            "targeted report must be passing and explicitly partial")
    require(report.get("before_sha") == before_sha
            and report.get("after_sha") == after_sha
            and report.get("selected_cases") == case_ids
            and isinstance(report.get("lanes"), list)
            and report.get("profile") == profile,
            "targeted selection/source/profile differs")
    source_delta = report.get("source_delta")
    require(isinstance(source_delta, dict)
            and source_delta.get("production_tree_unchanged") is True,
            "targeted source-delta gate did not pass")
    rows = report.get("cases")
    require(isinstance(rows, list) and len(rows) == len(case_ids)
            and [row.get("case") for row in rows if isinstance(row, dict)] == case_ids,
            "targeted case rows differ")
    repeat_path = root / "targeted-ui-repeatability.json"
    repeat = json_object(read_bytes(repeat_path), repeat_path)
    require(repeat.get("schema_version") == 1 and repeat.get("passed") is True
            and repeat.get("complete_regression_run") is False
            and repeat.get("after_sha") == after_sha
            and repeat.get("selected_cases") == case_ids
            and ("profile" not in repeat or repeat.get("profile") == profile),
            "candidate three-process repeatability report did not pass")
    modules, repeats = repeat.get("selected_modules"), repeat.get("repeats")
    require(isinstance(modules, dict) and modules
            and set(modules.values()) <= set(case_ids)
            and isinstance(repeats, list) and len(repeats) == len(modules)
            and {(row.get("module"), row.get("case")) for row in repeats
                 if isinstance(row, dict) and row.get("passed") is True
                 and type(row.get("returncode")) is int and row["returncode"] == 0}
            == set(modules.items()),
            "candidate module repeatability rows are incomplete")
    plans = []
    seen_manifests = set()
    selected_lanes = set()
    for case, row in zip(case_ids, rows):
        lanes = row.get("lanes")
        lane_names = ([lane.get("lane") for lane in lanes if isinstance(lane, dict)]
                      if isinstance(lanes, list) else [])
        require(lane_names in (list(LANES), ["controlled-experimental"]),
                "case lane rows differ: " + case)
        selected_lanes.update(lane_names)
        for lane_row in lanes:
            clock_mode = lane_row["lane"]
            lane = LANES[clock_mode]
            require(lane_row.get("gate_errors") == [] and
                    isinstance(lane_row.get("runs"), dict)
                    and set(lane_row["runs"]) == set(SIDES),
                    "targeted gate/runs incomplete: %s/%s" % (case, clock_mode))
            for side, revision in (("before", before_sha), ("after", after_sha)):
                run = lane_row["runs"][side]
                require(isinstance(run, dict)
                        and type(run.get("returncode")) is int
                        and run["returncode"] == 0,
                        "case run failed: %s/%s/%s" % (case, clock_mode, side))
                relative = safe_relative(run.get("manifest"))
                require(len(relative.parts) == 5
                        and relative.parts[:3] == (case, clock_mode, side)
                        and relative.name == "manifest.json",
                        "unexpected targeted manifest layout: " + str(relative))
                require(relative not in seen_manifests, "duplicate manifest path")
                seen_manifests.add(relative)
                manifest_path = root / relative
                manifest_raw = read_bytes(manifest_path)
                require(digest(manifest_raw) == run.get("manifest_sha256"),
                        "targeted report manifest digest differs")
                manifest = json_object(manifest_raw, manifest_path)
                require(manifest.get("schema_version") == 1
                        and manifest.get("mosaic_revision") == revision
                        and manifest.get("case") == case
                        and manifest.get("clock_mode") == clock_mode
                        and manifest.get("profile") == profile
                        and manifest.get("passed") is True
                        and manifest.get("failure") is None
                        and manifest.get("campaign_complete") is False
                        and manifest.get("diagnostic_only") is
                        (clock_mode == "controlled-experimental"),
                        "manifest source/lane/profile/pass identity differs")
                payload = pair_payload(manifest, manifest_path.parent)
                target = no_symlink(output / case / lane / side)
                require(not target.exists(), "existing evidence will not be overwritten: " + str(target))
                provenance = dict(schema_version=1, source_run=
                                  "https://github.com/subvertnormality/mosaic/actions/runs/" + run_id,
                                  source_run_id=run_id, source_revision=revision,
                                  case=case, lane=lane, clock_mode=clock_mode, side=side,
                                  profile=profile,
                                  targeted_report_sha256=digest(report_raw),
                                  repeatability_report_sha256=digest(read_bytes(repeat_path)),
                                  manifest=relative.as_posix(),
                                  manifest_sha256=digest(manifest_raw),
                                  evidence_sha256={key: digest(raw) for key, raw in payload.items()},
                                  complete_regression_run=False,
                                  verification_scope="uploaded recipe/results subset; full inventory validated by CI")
                payload["source-manifest.json"] = manifest_raw
                payload["source-targeted-report.json"] = report_raw
                payload["source-repeatability-report.json"] = read_bytes(repeat_path)
                payload["provenance.json"] = (json.dumps(provenance, indent=2) + "\n").encode()
                plans.append((target, payload))
    require(report.get("lanes") == [lane for lane in LANES if lane in selected_lanes],
            "targeted report lane summary differs from case rows")
    if not dry_run:
        for target, payload in plans:
            no_symlink(target)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.mkdir(exist_ok=False)
            for name, raw in payload.items():
                destination = no_symlink(target / safe_relative(name))
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open("xb") as handle:
                    handle.write(raw)
    return dict(dry_run=dry_run, source_run_id=run_id,
                imported=[str(target) for target, _ in plans],
                complete_regression_run=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("download", type=Path)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[3]
                        / "docs/testing/ui-migration-baselines")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--before-sha", required=True)
    parser.add_argument("--after-sha", required=True)
    parser.add_argument("--case", action="append", dest="cases", required=True)
    parser.add_argument("--profile", choices=PROFILES, default="base-midi")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = import_targeted(args.download, args.output, args.run_id,
                                 args.before_sha, args.after_sha, args.cases,
                                 dry_run=args.dry_run, profile=args.profile)
    except (ValueError, OSError) as error:
        parser.exit(1, "Targeted evidence import refused: %s\n" % error)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
