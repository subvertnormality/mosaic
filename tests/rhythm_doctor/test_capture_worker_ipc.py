"""Compiled AF_UNIX/JACK integration for the Rhythm Doctor capture worker."""
import hashlib
import os
import pathlib
import shutil
import socket
import struct
import subprocess
import tempfile
import time
import unittest
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[2]
WORKER = ROOT / "tools/rhythm_doctor/rd_capture_worker.c"
INJECTOR = ROOT / "tests/rhythm_doctor/test_capture_injector.c"


@unittest.skipUnless(all(shutil.which(x) for x in ("gcc", "jackd", "jack_lsp")), "requires GCC and JACK")
class CaptureWorkerIPC(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="rd-worker-")
        self.addCleanup(self.temporary.cleanup)
        self.root = pathlib.Path(self.temporary.name)
        self.binary = self.root / "rd_capture_worker"
        self.injector_binary = self.root / "rd_injector"
        subprocess.run(["gcc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", str(WORKER), "-o", str(self.binary), "-ljack"], check=True)
        subprocess.run(["gcc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", str(INJECTOR), "-o", str(self.injector_binary), "-ljack"], check=True)
        self.process = self.peer = self.server = self.injector = None

    def tearDown(self):
        for process in (self.process, self.injector, self.server):
            if process and process.poll() is None:
                process.terminate()
                try: process.wait(timeout=3)
                except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=3)
        if self.peer:
            self.peer.close()
        for process in (self.process, self.injector, self.server):
            if process:
                for stream in (process.stdin, process.stdout, process.stderr):
                    if stream: stream.close()

    def start_jack(self):
        name = "rd-worker-" + uuid.uuid4().hex
        self.environment = os.environ.copy(); self.environment["JACK_DEFAULT_SERVER"] = name
        self.server = subprocess.Popen(["jackd", "--name", name, "-d", "dummy", "-r", "48000", "-p", "128"],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, env=self.environment)
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if self.server.poll() is not None: self.fail("jackd exited: " + self.server.stderr.read().decode(errors="replace"))
            if subprocess.run(["jack_lsp"], env=self.environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0: return
            time.sleep(.05)
        self.fail("jackd did not become ready")

    def launch_worker(self, sources=("missing:left", "missing:right")):
        template = str(self.root / "owned-XXXXXX")
        self.process = subprocess.Popen([str(self.binary), template, *sources], stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True, env=getattr(self, "environment", None))
        socket_path = self.process.stdout.readline().strip()
        self.assertTrue(socket_path)
        return socket_path, pathlib.Path(socket_path).parent

    def start_worker(self, sources=("missing:left", "missing:right")):
        socket_path, owned = self.launch_worker(sources)
        self.peer = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET); self.peer.settimeout(3); self.peer.connect(socket_path)
        mode = stat_mode(pathlib.Path(socket_path)); self.assertEqual(mode, 0o600)
        self.assertEqual(stat_mode(pathlib.Path(socket_path).parent), 0o700)
        return owned

    def exchange(self, record):
        self.peer.send(record.encode()); return self.peer.recv(2048).decode().split("\t")

    def test_parser_rejects_malformed_overflow_long_and_unknown_records(self):
        self.start_worker()
        bad = [
            "RD1\tj\tp\t0\t0\tUNKNOWN\t", "RD1\tj\tp\t4294967296\t0\tEXIT\t",
            "RD1\tj\tp\t0\t0\tEXIT\t\textra", "RD1\t../j\tp\t0\t0\tEXIT\t",
            "RD1\t" + "j" * 65 + "\tp\t0\t0\tEXIT\t", "RD1\tj\tp\t0\t0\tEXIT\t\n",
        ]
        for record in bad:
            reply = self.exchange(record)
            self.assertEqual((reply[0], reply[6], reply[7]), ("RD1", "ERROR", "BAD_PROTOCOL"))
        reply = self.exchange("RD1\tj\tp\t0\t0\tPREFLIGHT\t1,manual")
        self.assertEqual(reply[1:6], ["j", "p", "0", "0", "PREFLIGHT"])
        self.assertEqual(reply[6], "FAILED")  # no named JACK server; fail visibly without auto-start

    def test_real_jack_pcm_publish_identity_release_and_cleanup(self):
        self.start_jack()
        self.injector = subprocess.Popen([str(self.injector_binary)], env=self.environment,
                                         stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        time.sleep(.15)
        owned = self.start_worker(("rd-capture-injector:left", "rd-capture-injector:right"))
        identity = "RD1\tjob-1\tproject-a\t7\t2\t"
        self.assertEqual(self.exchange(identity + "PREFLIGHT\t1,manual")[6], "READY")
        stale = self.exchange("RD1\tother\tproject-a\t7\t2\tSTART\t")
        self.assertEqual((stale[6], stale[7]), ("STALE", "STALE_JOB"))
        self.assertEqual(self.exchange(identity + "START\t")[6], "STARTED")
        time.sleep(.12)
        self.peer.send((identity + "STOP\t").encode())
        complete = self.peer.recv(2048).decode().split("\t")
        self.assertEqual((complete[1:5], complete[5:7]), (["job-1", "project-a", "7", "2"], ["EVENT", "COMPLETED"]))
        published = self.exchange(identity + "PUBLISH\t")
        self.assertEqual(published[6], "PUBLISHED")
        path, digest, frames, rate = published[7].split(",")
        wav = pathlib.Path(path); payload = wav.read_bytes()
        self.assertEqual(hashlib.sha256(payload).hexdigest(), digest)
        self.assertEqual(int(rate), 48000); self.assertGreater(int(frames), 256)
        self.assertEqual(payload[:4] + payload[8:12], b"RIFFWAVE")
        self.assertEqual(struct.unpack_from("<HHIIHH", payload, 20), (3, 2, 48000, 384000, 8, 32))
        self.assertEqual(self.exchange(identity + "RELEASE\t")[6], "RELEASED")
        self.assertEqual(self.exchange(identity + "RELEASE\t")[6], "RELEASED")  # later alignment lease
        bye = self.exchange(identity + "EXIT\t"); self.assertEqual(bye[6], "BYE")
        self.process.wait(timeout=3)
        self.assertFalse(wav.exists()); self.assertFalse(owned.exists())

    @unittest.skipUnless(shutil.which("luajit"), "requires LuaJIT")
    def test_machine_controller_transport_worker_flow(self):
        self.start_jack()
        self.injector = subprocess.Popen([str(self.injector_binary)], env=self.environment,
                                         stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        time.sleep(.15)
        socket_path, owned = self.launch_worker(("rd-capture-injector:left", "rd-capture-injector:right"))
        lua_path = str(ROOT / "lib/?.lua").replace("\\", "/")
        script = f'''package.path={lua_path!r}..';'..package.path
local ffi=require('ffi');ffi.cdef[[int usleep(unsigned int);]]
local Machine=require('rhythm_doctor.state_machine');local Controller=require('rhythm_doctor.capture_controller')
local Native=require('rhythm_doctor.native_transport');local transport=assert(Native.new({socket_path!r}))
local controller,machine,asset,saved
machine=Machine.new{{project_id='integration',on_capture_start=function(mode,token) controller:begin(mode,token,1) end,
 on_cancel=function(token) controller:cancel(token) end,on_release=function(token) controller:release(token) end,
 on_analyse=function(token) controller:analyse(token) end}}
controller=Controller.new{{machine=machine,transport=transport,now=os.clock,transport_stopped=function() return true end,
 on_capture_saved=function(value) saved=value end,on_analysis_ready=function(value,token)
  asset=value;machine:receive_analysis{{project_id=token.project_id,generation=token.generation,analysis_revision=token.analysis_revision,error='TEST_ANALYSIS_STOP'}} end}}
assert(machine:start_capture('manual',true).ok)
for i=1,500 do controller:poll();if controller.job.phase=='CAPTURING' then break end;ffi.C.usleep(10000) end
assert(controller.job.phase=='CAPTURING');ffi.C.usleep(120000);assert(machine:finish_capture(true,true).ok)
for i=1,500 do controller:poll();if machine.resources_are_released then break end;ffi.C.usleep(10000) end
assert(asset and saved and asset.wav_sha256==saved.wav_sha256 and machine.state=='FAILED' and machine.resources_are_released)
local file=assert(io.open(asset.wav_path,'rb'));local bytes=file:read('*a');file:close();assert(#bytes>44 and bytes:sub(1,4)=='RIFF')
transport:close()
'''
        result = subprocess.run(["luajit", "-e", script], cwd=ROOT, env=self.environment,
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.process.wait(timeout=3)
        self.assertFalse(owned.exists())


def stat_mode(path):
    return path.stat().st_mode & 0o777


if __name__ == "__main__":
    unittest.main()
