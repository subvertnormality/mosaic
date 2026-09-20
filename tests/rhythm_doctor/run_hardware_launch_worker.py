"""Opt-in physical-Norns end-to-end check for ``launch_worker.py``.

The runner deploys only a short, hash-verified source manifest to one new
``/tmp`` directory.  It refuses a device with the real-norns active guard,
builds through the production helper with ``system:capture_1/2``, drives the
production file-mailbox transport through PREFLIGHT/START/CANCEL/RELEASE
on the device's own Lua 5.3, which is what matron embeds,
and removes only paths and process IDs it created.  It never copies, loads, or
changes a user Mosaic project.  ``--execute`` is required deliberately: this
is a review-gated physical-device check, not CI or an ordinary local test.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
FILES = (
    "tools/rhythm_doctor/launch_worker.py",
    "tools/rhythm_doctor/rd_capture_worker.c",
    "tools/rhythm_doctor/rd_capture.c",
    "lib/rhythm_doctor/native_transport.lua",
    "lib/rhythm_doctor/file_mailbox.lua",
    "tests/rhythm_doctor/test_launch_worker_transport.lua",
)
ACTIVE_GUARD = "/home/we/.cache/mosaic-real-norns/active"
RUNTIME_FILES = (
    "mailbox", "mailbox.new", "error", "error.new", "rd-worker", "rd-worker.new",
    "rd-worker.sha256", "rd-worker.sha256.new", "worker.log", "pid", "pid.new", "cancel",
)


def launch_command(remote: str) -> str:
    """Return the exact production-helper invocation used on the device."""
    return " ".join(shlex.quote(value) for value in (
        "python3", remote + "/tools/rhythm_doctor/launch_worker.py",
        "--source", remote + "/tools/rhythm_doctor",
        "--runtime", remote + "/runtime",
        "--left", "system:capture_1", "--right", "system:capture_2",
    ))


def private_worker_root(mailbox_root: str, uid: int) -> str | None:
    """Accept only the mkdtemp root owned by this helper's worker process."""
    match = re.fullmatch(r"/tmp/mosaic-rd-" + re.escape(str(uid)) + r"-[A-Za-z0-9]{6,}", mailbox_root)
    return match.group(0) if match else None


class Remote:
    def __init__(self, host: str, control_path: str):
        self.ssh = ["ssh", "-S", control_path, "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", host]
        self.control_path = control_path
        self.host = host

    def call(self, command: str, *, timeout: int = 30, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(self.ssh + [command], text=True, capture_output=True, timeout=timeout)
        if check and result.returncode:
            raise RuntimeError("remote command failed: " + command + "\n" + result.stdout + result.stderr)
        return result

    def start(self, command: str, stdout_path: str, stderr_path: str) -> int:
        code = (
            "import subprocess;"
            "out=open(" + repr(stdout_path) + ", 'w');err=open(" + repr(stderr_path) + ", 'w');"
            "p=subprocess.Popen(" + repr(["/bin/sh", "-lc", command]) + ", stdin=subprocess.DEVNULL, "
            "stdout=out, stderr=err, start_new_session=True);print(p.pid)"
        )
        return int(self.call("python3 -c " + shlex.quote(code)).stdout.strip())

    def copy(self, local: Path, remote: str) -> None:
        subprocess.run(["scp", "-o", "ControlPath=" + self.control_path, str(local), self.host + ":" + remote],
                       text=True, capture_output=True, timeout=30, check=True)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def worker_build_identity(source: Path) -> str:
    """Match ``launch_worker.digest`` for the two C inputs it compiles."""
    value = hashlib.sha256()
    for name in ("rd_capture_worker.c", "rd_capture.c"):
        path = source / "tools/rhythm_doctor" / name
        value.update(path.name.encode("utf-8") + b"\0")
        value.update(path.read_bytes())
    return value.hexdigest()


def remote_text(remote: Remote, command: str, *, timeout: int = 30) -> str:
    return remote.call(command, timeout=timeout).stdout


def exact_remove(remote: Remote, remote_root: str, worker_root: str | None, launcher_pid: int | None,
                 worker_pid: int | None) -> list[str]:
    """Remove only known files, known empty directories, and owned PIDs."""
    failures: list[str] = []
    for pid in (worker_pid, launcher_pid):
        if pid is not None:
            result = remote.call("kill " + str(pid) + " 2>/dev/null || true", check=False)
            if result.returncode:
                failures.append("could not signal owned pid " + str(pid))
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline and remote.call("kill -0 " + str(pid), check=False).returncode == 0:
                time.sleep(.05)
            if remote.call("kill -0 " + str(pid), check=False).returncode == 0:
                failures.append("owned pid survived termination " + str(pid))
    if worker_root is not None:
        result = remote.call("rmdir " + shlex.quote(worker_root) + " 2>/dev/null || true", check=False)
        if result.returncode:
            failures.append("could not remove owned worker root")
    files = [remote_root + "/" + relative for relative in FILES]
    files += [remote_root + "/runtime/" + name for name in RUNTIME_FILES]
    files += [remote_root + "/launcher.stdout", remote_root + "/launcher.stderr", remote_root + "/transport.stdout", remote_root + "/transport.stderr"]
    result = remote.call("rm -f " + " ".join(shlex.quote(path) for path in files), check=False)
    if result.returncode:
        failures.append("could not remove known deployment files")
    directories = (remote_root + "/runtime", remote_root + "/tests/rhythm_doctor", remote_root + "/tests",
                   remote_root + "/lib/rhythm_doctor", remote_root + "/lib", remote_root + "/tools/rhythm_doctor",
                   remote_root + "/tools", remote_root)
    for directory in directories:
        result = remote.call("rmdir " + shlex.quote(directory) + " 2>/dev/null || true", check=False)
        if result.returncode:
            failures.append("could not remove empty directory " + directory)
    return failures


def run(args: argparse.Namespace) -> tuple[dict, int]:
    if args.output.exists():
        raise FileExistsError("evidence output must be new")
    remote = Remote(args.host, args.control_path)
    # This is intentionally the first device operation: a guarded device is untouched.
    remote.call("test ! -e " + shlex.quote(ACTIVE_GUARD))
    run_id = "mosaic-rd-launch-worker-" + uuid.uuid4().hex
    remote_root = "/tmp/" + run_id
    source_sha256: dict[str, str] = {}
    launcher_pid = worker_pid = None
    worker_root = None
    transport_result = None
    failure = None
    cleanup_failures: list[str] = []
    routes_before = routes_after = None
    built_worker_sha256 = None
    expected_worker_identity = worker_build_identity(ROOT)
    try:
        remote.call("mkdir " + shlex.quote(remote_root))
        remote.call("mkdir " + " ".join(shlex.quote(remote_root + "/" + path) for path in (
            "tools", "tools/rhythm_doctor", "lib", "lib/rhythm_doctor", "tests", "tests/rhythm_doctor", "runtime")))
        with tempfile.TemporaryDirectory(prefix=run_id + "-") as staging:
            stage = Path(staging)
            for relative in FILES:
                source = ROOT / relative
                frozen = stage / Path(relative).name
                frozen.write_bytes(source.read_bytes())
                source_sha256[relative] = sha256(frozen)
                destination = remote_root + "/" + relative
                remote.copy(frozen, destination)
                actual = remote_text(remote, "sha256sum " + shlex.quote(destination)).split()[0]
                if actual != source_sha256[relative]:
                    raise RuntimeError("deployed source hash differs: " + relative)
        routes_before = remote_text(remote, "jack_lsp -c")
        launcher_pid = remote.start(launch_command(remote_root), remote_root + "/launcher.stdout", remote_root + "/launcher.stderr")
        deadline = time.monotonic() + 70
        mailbox_root = ""
        while time.monotonic() < deadline:
            if remote.call("test -s " + shlex.quote(remote_root + "/runtime/error"), check=False).returncode == 0:
                raise RuntimeError(remote_text(remote, "cat " + shlex.quote(remote_root + "/runtime/error")))
            result = remote.call("test -s " + shlex.quote(remote_root + "/runtime/mailbox") + " && head -n 1 " + shlex.quote(remote_root + "/runtime/mailbox") + " || true")
            mailbox_root = result.stdout.strip()
            if mailbox_root:
                uid = int(remote_text(remote, "id -u").strip())
                worker_root = private_worker_root(mailbox_root, uid)
                if worker_root is None:
                    raise RuntimeError("worker published an unexpected mailbox root")
                worker_pid = int(remote_text(remote, "cat " + shlex.quote(remote_root + "/runtime/pid")).strip())
                if remote_text(remote, "cat " + shlex.quote(remote_root + "/runtime/rd-worker.sha256")).strip() != expected_worker_identity:
                    raise RuntimeError("launch_worker build identity differs from deployed capture sources")
                built_worker_sha256 = remote_text(remote, "sha256sum " + shlex.quote(remote_root + "/runtime/rd-worker")).split()[0]
                break
            time.sleep(.1)
        if not mailbox_root:
            raise RuntimeError("launch_worker did not publish a mailbox")
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and remote.call("kill -0 " + str(launcher_pid), check=False).returncode == 0:
            time.sleep(.05)
        if remote.call("kill -0 " + str(launcher_pid), check=False).returncode == 0:
            raise RuntimeError("launch_worker helper did not exit after publishing its mailbox")
        # matron embeds Lua 5.3 and a norns has no luajit, so only the device's
        # own interpreter proves anything about the deployed transport.
        device_lua = remote_text(remote, "command -v lua5.3 || command -v lua").strip()
        if not device_lua:
            raise RuntimeError("no Lua interpreter on the device; matron embeds Lua 5.3")
        command = "cd " + shlex.quote(remote_root) + " && " + device_lua + " tests/rhythm_doctor/test_launch_worker_transport.lua " + shlex.quote(mailbox_root) + " " + shlex.quote(remote_root + "/lib")
        transport_result = remote.call(command, timeout=60, check=False)
        if transport_result.returncode:
            raise RuntimeError(transport_result.stdout + transport_result.stderr)
        # A file mailbox has no hangup: the worker leaves once the client stops
        # stamping liveness, which takes its idle timeout.
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline and remote.call("kill -0 " + str(worker_pid), check=False).returncode == 0:
            time.sleep(.25)
        if remote.call("kill -0 " + str(worker_pid), check=False).returncode == 0:
            raise RuntimeError("worker remained after its client stopped stamping liveness")
        if remote.call("test ! -e " + shlex.quote(worker_root), check=False).returncode:
            raise RuntimeError("worker private mailbox root survived the client leaving")
        routes_after = remote_text(remote, "jack_lsp -c")
        if routes_after != routes_before:
            raise RuntimeError("JACK connections changed after cleanup")
    except Exception as error:
        failure = str(error)
    finally:
        cleanup_failures = exact_remove(remote, remote_root, worker_root, launcher_pid, worker_pid)
        if remote.call("test ! -e " + shlex.quote(remote_root), check=False).returncode:
            cleanup_failures.append("deployment root survives cleanup")
    report = {
        "schema_version": 1,
        "run_id": run_id,
        "profile": "physical-norns-launch-worker-system-capture",
        "source_sha256": source_sha256,
        "launch_worker_build_identity": expected_worker_identity,
        "built_worker_sha256": built_worker_sha256,
        "runner_sha256": sha256(Path(__file__)),
        "transport": None if transport_result is None else {
            "exit_code": transport_result.returncode,
            "stdout": transport_result.stdout,
            "stderr": transport_result.stderr,
        },
        "cleanup": {
            "worker_self_cleaned": worker_root is not None and remote.call("test ! -e " + shlex.quote(worker_root), check=False).returncode == 0,
            "deployment_root_removed": remote.call("test ! -e " + shlex.quote(remote_root), check=False).returncode == 0,
            "jack_routes_restored": routes_before is not None and routes_after == routes_before,
            "failures": cleanup_failures,
        },
        "failure": failure,
        "passed": bool(transport_result and transport_result.returncode == 0 and not failure and not cleanup_failures and
                       routes_before is not None and routes_after == routes_before),
        "scope": "production launch_worker plus file-mailbox transport on the device Lua with system capture ports; no Mosaic user project is deployed or loaded",
        "full_feature_acceptance": False,
    }
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(report, output, indent=2, sort_keys=True)
        output.write("\n")
    return report, int(not report["passed"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True)
    parser.add_argument("--control-path", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--execute", action="store_true", help="perform the review-gated physical-device operation")
    args = parser.parse_args()
    if not args.execute:
        parser.error("physical Norns runner is review-gated; pass --execute after review")
    report, result = run(args)
    print(json.dumps({"passed": report["passed"], "output": str(args.output), "failure": report["failure"]}))
    return result


if __name__ == "__main__":
    raise SystemExit(main())
