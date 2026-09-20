"""Run pure RD core tests on Norns without loading/changing the user's script.

This is CPU/Lua evidence only, not actual-app capture/transcription acceptance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[2]
FILES = ["lib/rhythm_doctor/" + name + ".lua" for name in
         ("bank", "state_machine", "paint", "paint_journal", "paint_transactions", "assets", "capture_controller", "analysis_controller",
          "runtime", "ui_adapter", "worker_host", "bank_persistence", "analysis_worker_host",
          "analysis_transport", "file_mailbox")]
# analysis_transport decodes the worker's result file, so its JSON helper has
# to be deployed alongside it, and it reaches the worker through file_mailbox.
FILES.append("lib/helpers/json.lua")
FILES.append("lib/project_lifecycle.lua")
FILES.append("lib/ui.lua")
FILES.extend(("lib/pages/trigger_edit_page/trigger_edit_page.lua",
              "lib/pages/trigger_edit_page/trigger_edit_page_ui.lua"))
TESTS = ["tests/rhythm_doctor/test_" + name + ".lua" for name in
         ("core", "integration", "lifecycle", "journal", "bank_schema", "paint_boundaries", "paint_transactions",
          "capture_transitions", "assets", "capture_controller", "analysis_controller", "analysis_runtime", "runtime",
          "project_lifecycle_runtime", "ui_adapter", "worker_host", "app_surface",
          "analysis_transport", "file_mailbox")]


def isolated_lua_command(remote, relative):
    """Run against the deployed modules, not norns' global ``include`` path."""
    return "cd " + shlex.quote(remote) + " && lua -e 'include=nil' " + shlex.quote(relative)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True)
    parser.add_argument("--control-path", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output already exists; earlier evidence must remain immutable")
    run_id = "mosaic-rd-core-" + uuid.uuid4().hex
    remote = "/tmp/" + run_id
    ssh = ["ssh", "-S", args.control_path, "-o", "BatchMode=yes",
           "-o", "ConnectTimeout=5", args.host]
    def run(command):
        return subprocess.run(ssh + [command], text=True, capture_output=True, timeout=45)
    def checked(command):
        result = run(command)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        return result.stdout
    checked("test ! -e /home/we/.cache/mosaic-real-norns/active")
    device = checked("uname -sm; lua -v 2>&1")
    checked("mkdir -p " + shlex.quote(remote + "/lib/rhythm_doctor") + " " +
            shlex.quote(remote + "/lib/helpers") + " " +
            shlex.quote(remote + "/lib/pages/trigger_edit_page") + " " +
            shlex.quote(remote + "/tests/rhythm_doctor"))
    identities, results = {}, []
    try:
        with tempfile.TemporaryDirectory(prefix=run_id) as temporary:
            for relative in FILES + TESTS:
                frozen = Path(temporary) / Path(relative).name
                frozen.write_bytes((ROOT / relative).read_bytes())
                identities[relative] = hashlib.sha256(frozen.read_bytes()).hexdigest()
                subprocess.run(["scp", "-o", "ControlPath=" + args.control_path,
                                str(frozen), args.host + ":" + remote + "/" + relative],
                               check=True, capture_output=True, timeout=30)
            for relative, expected in identities.items():
                actual = checked("sha256sum " + shlex.quote(remote + "/" + relative)).split()[0]
                if actual != expected:
                    raise RuntimeError("deployed source mismatch: " + relative)
            for relative in TESTS:
                result = run(isolated_lua_command(remote, relative))
                results.append(dict(test=relative, exit_code=result.returncode,
                                    stdout=result.stdout, stderr=result.stderr))
    finally:
        # Remove only this run's exact known files/directories; no recursive deletion.
        for relative in FILES + TESTS:
            checked("rm -f " + shlex.quote(remote + "/" + relative))
        checked("rmdir " + " ".join(shlex.quote(remote + suffix) for suffix in
                ("/lib/rhythm_doctor", "/lib/helpers", "/lib/pages/trigger_edit_page", "/lib/pages",
                 "/tests/rhythm_doctor", "/lib", "/tests", "")))
    report = dict(run_id=run_id, profile="physical-norns", device=device,
                  source_sha256=identities, tests=results,
                  passed=len(results) == len(TESTS) and all(r["exit_code"] == 0 for r in results),
                  scope="pure Lua component tests only", full_feature_acceptance=False)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return int(not report["passed"])


if __name__ == "__main__":
    raise SystemExit(main())
