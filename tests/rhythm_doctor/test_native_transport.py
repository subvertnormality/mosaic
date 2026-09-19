"""Real LuaJIT/AF_UNIX tests for the nonblocking worker transport."""
import pathlib
import shutil
import socket
import subprocess
import tempfile
import threading
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]

@unittest.skipUnless(shutil.which('luajit'), 'requires LuaJIT')
class NativeTransport(unittest.TestCase):
    def run_exchange(self,response,assertion):
        with tempfile.TemporaryDirectory(prefix='rd-transport-') as temporary:
            path=str(pathlib.Path(temporary)/'worker.sock')
            server=socket.socket(socket.AF_UNIX,socket.SOCK_SEQPACKET);server.bind(path);server.listen(1)
            seen=[]
            def peer():
                connection,_=server.accept()
                with connection:
                    seen.append(connection.recv(2048).decode());connection.send(response.encode())
            thread=threading.Thread(target=peer);thread.start()
            script=f'''package.path={str(ROOT/'lib/?.lua').__repr__()}..';'..package.path
local T=require('rhythm_doctor.native_transport');local t,e=T.new({path!r});assert(t,e and e.code)
assert(t:send{{protocol_version=1,job_id='job-1',project_id='project-a',generation=7,analysis_revision=2,command='PREFLIGHT',seconds=45,mode='manual'}})
local m;for i=1,100000 do m=t:poll();if m then break end end
assert(m);{assertion};t:close()
'''
            result=subprocess.run(['luajit','-e',script],cwd=ROOT,text=True,capture_output=True,timeout=5)
            thread.join(timeout=3);server.close()
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual(seen,['RD1\tjob-1\tproject-a\t7\t2\tPREFLIGHT\t45,manual'])

    def test_round_trip_decodes_matching_identity(self):
        self.run_exchange('RD1\tjob-1\tproject-a\t7\t2\tPREFLIGHT\tREADY\t',
                          "assert(m.status=='READY' and m.command=='PREFLIGHT' and m.generation==7)")

    def test_malformed_reply_fails_closed_for_current_identity(self):
        self.run_exchange('malformed',
                          "assert(m.status=='FAILED' and m.capture_error=='CAPTURE_PROTOCOL_ERROR' and m.job_id=='job-1')")

    def test_invalid_messages_and_paths_fail_before_io(self):
        script=f'''package.path={str(ROOT/'lib/?.lua').__repr__()}..';'..package.path
local T=require('rhythm_doctor.native_transport');local t,e=T.new('relative');assert(not t and e.code=='INVALID_SOCKET_PATH')
'''
        result=subprocess.run(['luajit','-e',script],cwd=ROOT,text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

if __name__=='__main__':unittest.main()
