"""Transport round trips on the interpreter matron embeds, over a file mailbox.

These once ran under `luajit` against AF_UNIX.  A norns has neither, so they
proved nothing about the device and skipped on CI; see test_matron_compatibility.
"""
import pathlib
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from mailbox_client import MailboxClient
from matron import LUA, SKIP_REASON

ROOT = pathlib.Path(__file__).resolve().parents[2]
PREFLIGHT = 'RD1\tjob-1\tproject-a\t7\t2\tPREFLIGHT\t45,manual'


def worker_mailbox(root):
    """Stand in for a worker that has published its mailbox and is waiting."""
    for direction in ('c2w', 'w2c'):
        (root / direction).mkdir(mode=0o700)
    (root / 'claim').write_bytes(b''); (root / 'up').write_bytes(b'')
    return MailboxClient(root, outbound='w2c', inbound='c2w', limit=1023, claim=False)


@unittest.skipUnless(LUA, SKIP_REASON)
class NativeTransport(unittest.TestCase):
    def run_exchange(self, response, assertion):
        with tempfile.TemporaryDirectory(prefix='rd-transport-') as temporary:
            root = pathlib.Path(temporary) / 'owned'
            root.mkdir(mode=0o700)
            worker = worker_mailbox(root)
            script = f'''package.path={str(ROOT/'lib/?.lua').__repr__()}..';'..package.path
local T=require('rhythm_doctor.native_transport');local t,e=T.new({str(root)!r});assert(t,e and e.code)
assert(t:send{{protocol_version=1,job_id='job-1',project_id='project-a',generation=7,analysis_revision=2,command='PREFLIGHT',seconds=45,mode='manual'}})
local m;for i=1,2000 do m=t:poll();if m then break end;os.execute('sleep 0.005') end
assert(m,'no reply');{assertion};t:close()
'''
            process = subprocess.Popen([LUA, '-e', script], cwd=ROOT, text=True,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                request = worker.receive(5).decode()
                worker.send(response.encode())
                output, problem = process.communicate(timeout=20)
            finally:
                if process.poll() is None:
                    process.kill(); process.communicate()
            self.assertEqual(process.returncode, 0, output + problem)
            self.assertEqual(request, PREFLIGHT)

    def test_round_trip_decodes_matching_identity(self):
        self.run_exchange('RD1\tjob-1\tproject-a\t7\t2\tPREFLIGHT\tREADY\t',
                          "assert(m.status=='READY' and m.command=='PREFLIGHT' and m.generation==7)")

    def test_malformed_reply_fails_closed_for_current_identity(self):
        self.run_exchange('malformed',
                          "assert(m.status=='FAILED' and m.capture_error=='CAPTURE_PROTOCOL_ERROR' and m.job_id=='job-1')")

    def test_invalid_roots_fail_before_any_io(self):
        script = f'''package.path={str(ROOT/'lib/?.lua').__repr__()}..';'..package.path
local T=require('rhythm_doctor.native_transport')
local t,e=T.new('relative');assert(not t and e.code=='INVALID_MAILBOX_ROOT',e and e.code)
t,e=T.new('/nonexistent/rd-mailbox');assert(not t and e.code=='MAILBOX_UNAVAILABLE',e and e.code)
'''
        result = subprocess.run([LUA, '-e', script], cwd=ROOT, text=True, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_a_second_transport_cannot_claim_the_same_mailbox(self):
        """One client at a time, decided atomically by rename."""
        with tempfile.TemporaryDirectory(prefix='rd-transport-') as temporary:
            root = pathlib.Path(temporary) / 'owned'
            root.mkdir(mode=0o700)
            worker_mailbox(root)
            script = f'''package.path={str(ROOT/'lib/?.lua').__repr__()}..';'..package.path
local T=require('rhythm_doctor.native_transport')
local first=assert(T.new({str(root)!r}))
local second,e=T.new({str(root)!r});assert(not second and e.code=='MAILBOX_UNAVAILABLE',e and e.code)
first:close()
'''
            result = subprocess.run([LUA, '-e', script], cwd=ROOT, text=True, capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_a_departed_worker_is_reported_as_a_protocol_failure(self):
        """Without a socket there is no hangup, so the sentinel stands in for one."""
        with tempfile.TemporaryDirectory(prefix='rd-transport-') as temporary:
            root = pathlib.Path(temporary) / 'owned'
            root.mkdir(mode=0o700)
            worker_mailbox(root)
            (root / 'up').unlink()
            script = f'''package.path={str(ROOT/'lib/?.lua').__repr__()}..';'..package.path
local T=require('rhythm_doctor.native_transport');local t=assert(T.new({str(root)!r}))
assert(t:send{{protocol_version=1,job_id='job-1',project_id='project-a',generation=7,analysis_revision=2,command='PREFLIGHT',seconds=45,mode='manual'}})
local m=t:poll()
assert(m and m.status=='FAILED' and m.capture_error=='CAPTURE_PROTOCOL_ERROR' and m.job_id=='job-1',m and m.status)
t:close()
'''
            result = subprocess.run([LUA, '-e', script], cwd=ROOT, text=True, capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
