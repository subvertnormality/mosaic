import hashlib,struct,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from real_norns import Maiden,MaidenInput,OSC,OutputTrace,Runner,SSH,SSHOSC,WebSocketMaiden,export_head,osc_packet
class Fn:
 def __init__(self,call):self.call=call
 def __call__(self,*a):return self.call(*a)
class NN:
 def __init__(self):self.sent=b'';self.options=[]
 def socket(self,*a):return 7
 def connect(self,*a):return 1
 def setopt(self,fd,level,opt,*a):self.options.append((level,opt));return 0
 def send(self,fd,buf,n,flags):self.sent=bytes(buf.raw[:n]);return n
 def recv(self,fd,buf,n,flags):
  value=b'answer '+self.sent.split(b"print('",1)[1].split(b"')",1)[0];buf[:len(value)]=value;return len(value)
 def close(self,*a):return 0
 def lib(self):
  x=type('L',(),{})();x.nn_socket=Fn(self.socket);x.nn_connect=Fn(self.connect);x.nn_setsockopt=Fn(self.setopt);x.nn_send=Fn(self.send);x.nn_recv=Fn(self.recv);x.nn_close=Fn(self.close);return x
class WS:
 def __init__(self):self.sent=[];self.closed=False
 def send(self,value):self.sent.append(value)
 def recv(self,timeout=None):
  marker=self.sent[-1].split("print('",1)[1].split("')",1)[0];return 'answer '+marker
 def close(self):self.closed=True
class S:
 def __init__(self,events=None):self.scripts=[];self.synced=[];self.events=events
 def run(self,x):self.scripts.append(x);self.events is not None and self.events.append('ssh');return type('R',(),{'stdout':'client MIDI\n'})()
 def rsync(self,a,b):self.synced.append((a,b))
 def push(self,a,b):self.pushed=(a,b)
 def fetch(self,a,b):b.write_bytes(b'\x89PNG\r\n\x1a\n'+b'0'*8+struct.pack('!II',640,384)+b'x');self.fetched=(a,b)
class M:
 def __init__(self,events=None):self.commands=[];self.events=events;self.closed=0
 def eval(self,x):self.commands.append(x);self.events is not None and self.events.append('maiden');return 'ok'
 def close(self):self.closed+=1
 def send(self,x):self.commands.append(x)
 def load(self,x):self.commands.append('load '+x);return 'ok'
class O:
 def send(self,*x):return {'args':x}
class Tests(unittest.TestCase):
 def r(self,events=None):t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);s=S(events);m=M(events);return Runner(s,m,O(),Path(t.name),'safe-run'),s,m
 def test_osc_packet_padding_and_network_integers(self):
  self.assertEqual(osc_packet('/remote/key',2,1),b'/remote/key\0,ii\0'+struct.pack('!ii',2,1));self.assertEqual(len(osc_packet('/remote/enc',1,-2))%4,0)
 def test_nanobus_uses_bus_and_timeouts_and_waits_marker(self):
  nn=NN()
  with patch('real_norns.ctypes.CDLL',return_value=nn.lib()):self.assertIn('answer',Maiden('ws://norns:5555/').eval('print(1)'))
  self.assertEqual(nn.options,[(0,5),(0,4)]);self.assertIn(b'print(1)',nn.sent);self.assertTrue(nn.sent.endswith(b'\n\0'))
 def test_official_websocket_uses_bus_subprotocol_and_text_framing(self):
  ws=WS();calls=[]
  def connect(*args,**kwargs):calls.append((args,kwargs));return ws
  m=WebSocketMaiden('ws://norns:5555/',connector=connect);self.assertIn('answer',m.eval('print(1)'));m.close();self.assertEqual(calls[0][1]['subprotocols'],['bus.sp.nanomsg.org']);self.assertIsInstance(ws.sent[0],str);self.assertTrue(ws.sent[0].endswith('\n'));self.assertNotIn('\0',ws.sent[0]);self.assertTrue(ws.closed)
 def test_nanobus_reuses_one_connection_until_explicit_close(self):
  nn=NN();m=Maiden('ws://norns:5555/')
  with patch('real_norns.ctypes.CDLL',return_value=nn.lib()),patch('real_norns.time.sleep'):m.eval('print(1)');m.eval('print(2)');m.close()
  self.assertIsNone(m.fd)
 def test_runner_closes_maiden_before_ssh_loopback_input(self):
  r,s,m=self.r();r.osc=SSHOSC(s,10111)
  with patch('real_norns.time.sleep'):r.action('enc',1,1)
  self.assertEqual(m.closed,1)
 def test_maiden_input_uses_exact_native_callback(self):
  m=M();event=MaidenInput(m).send('key',2,1);self.assertEqual(m.commands[-1],'key(2,1)');self.assertEqual(event['transport'],'maiden-script-hardware-callback')
 def test_ssh_osc_uses_stock_loopback_endpoint(self):
  s=S();event=SSHOSC(s,10111).send('enc',1,1);self.assertIn("('127.0.0.1',10111)",s.scripts[-1]);self.assertEqual(event['transport'],'ssh-loopback-udp')
 def test_nanobus_fire_and_forget_load_does_not_wait_for_old_context(self):
  nn=NN();m=Maiden('ws://norns:5555/')
  with patch('real_norns.ctypes.CDLL',return_value=nn.lib()),patch('real_norns.time.sleep'):m.send("norns.script.load('/x.lua')")
  self.assertIn(b"norns.script.load('/x.lua')",nn.sent);self.assertTrue(nn.sent.endswith(b'\n\0'))
 def test_backup_is_before_clear_and_tracks_recovery(self):
  events=[];r,s,m=self.r(events);r.backup();r.maiden.eval('norns.script.clear()');self.assertEqual(events[:2],['ssh','maiden']);self.assertIn('cp -a /home/we/dust/data/system.state',s.scripts[0])
 def test_export_head_excludes_untracked(self):
  t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);root=Path(t.name);subprocess.run(['git','init','-q'],cwd=root);(root/'tracked').write_text('yes');subprocess.run(['git','add','tracked'],cwd=root);subprocess.run(['git','-c','user.name=T','-c','user.email=t@t','commit','-qm','x'],cwd=root);(root/'untracked').write_text('no');hold,tree,manifest,rows=export_head(root);self.addCleanup(hold.cleanup);self.assertTrue((tree/'tracked').exists());self.assertFalse((tree/'untracked').exists());self.assertEqual(rows,[(hashlib.sha256(b'yes').hexdigest(),'tracked')])
 def test_screenshot_exact_dimensions_and_restore_finalize(self):
  r,s,m=self.r();shot=r.screenshot('before');self.assertEqual((shot['width'],shot['height']),(640,384));r.restore();self.assertIn('system.state',s.scripts[-1]);r.finalize();self.assertIn('data-mosaic /home/we/dust/data/mosaic',s.scripts[-1]);self.assertNotIn('rm -rf /home/we/dust/code/mosaic',s.scripts[-1]);self.assertIn('restored_user_data_and_state', (r.out/'finalized.json').read_text())
 def test_finalize_records_filesystem_restoration_before_reload(self):
  r,_,_=self.r();r.reload_saved=lambda:(_ for _ in ()).throw(RuntimeError('reload failed'))
  with self.assertRaises(RuntimeError):r.finalize()
  receipt=__import__('json').loads((r.out/'finalized.json').read_text());self.assertTrue(receipt['filesystem_finalized']);self.assertFalse(receipt['reload_complete'])
 def test_seed_config_is_explicit_isolated_data_and_reloads(self):
  r,s,m=self.r();source=r.out/'config';source.mkdir();r.seed_config(source);self.assertIn('rm -rf /home/we/dust/data/mosaic/config',s.scripts[-1]);self.assertEqual(s.synced[-1][1],'/home/we/dust/data/mosaic/config');self.assertIn('norns.script.clear()',m.commands[-2]);self.assertIn('load /home/we/dust/code/mosaic/mosaic.lua',m.commands[-1])
 def test_ssh_transfers_keep_ssh_control_options(self):
  t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);root=Path(t.name);src=root/'in';dst=root/'out';src.write_bytes(b'abc');ssh=SSH('we@norns',['-S','/tmp/control'])
  with patch('real_norns.subprocess.run') as run:ssh.push(src,'/remote/file');self.assertEqual(run.call_args.args[0][:5],['ssh','-S','/tmp/control','we@norns','tee'])
  with patch('real_norns.subprocess.check_output',return_value=b'png') as get:ssh.fetch('/remote/shot',dst);self.assertEqual(dst.read_bytes(),b'png');self.assertEqual(get.call_args.args[0][:5],['ssh','-S','/tmp/control','we@norns','cat'])
 def test_resume_requires_matching_recovery_marker_and_rechecks_source(self):
  r,s,m=self.r();s.fetch=lambda remote,local:local.write_text('abc  mosaic.lua\n');m.eval=lambda code:m.commands.append(code) or '__MOSAIC_ACTIVE__/home/we/dust/code/mosaic/mosaic.lua';count=r.resume();self.assertEqual(count,1);self.assertIn('cat /home/we/.cache/mosaic-real-norns/active',s.scripts[-1]);self.assertIn('sha256sum -c /home/we/.cache/mosaic-real-norns/safe-run/source.sha256',s.scripts[-1]);self.assertIn('__MOSAIC_ACTIVE__',m.commands[-1])
 def test_channel_subpage_parses_public_ui_observation(self):
  r,_,m=self.r();m.eval=lambda code:'__MOSAIC_SUBPAGE__6\nmarker';self.assertEqual(r.channel_subpage(),6)
 def test_grid_is_explicit_synthetic_lua_only(self):
  r,_,m=self.r();r.synthetic_grid(4,3,8,1);self.assertEqual(m.commands[-1],'_norns.grid.key(4,3,8,1)')
 def test_grid_device_auto_discovers_runtime_id(self):
  r,_,m=self.r();m.eval=lambda code:'__MOSAIC_GRID_ID__2\nmarker';self.assertEqual(r.grid_device(),2);self.assertEqual(r.grid_device(7),7)
 def test_output_trace_preserves_raw_signed_led_and_exposes_physical_nibble(self):
  rows='\n'.join('__GRID_ROW__%d|%s'%(y,','.join(['-4' if y==8 and x==1 else '2' for x in range(1,17)])) for y in range(1,9))
  m=M();m.eval=lambda code:'__GRID_COUNTS__12,3\n'+rows+'\n__MIDI__1|12.250000000|userdata: 1|table|144,60,127\n'
  value=OutputTrace(m).snapshot();self.assertEqual(value['raw_grid'][112],-4);self.assertEqual(value['grid'][112],12);self.assertEqual(value['midi'][0]['bytes'],[144,60,127])
 def test_output_trace_uses_persistent_globals_and_restores_c_binding(self):
  m=M();m.eval=lambda code:m.commands.append(code) or ('__TRACE_REMOVED__C' if '__TRACE_REMOVED__' in code else 'ok')
  trace=OutputTrace(m);trace.install();trace.remove();self.assertIn('_MOSAIC_HW_ORIG_MIDI=_norns.midi_send',m.commands[0]);self.assertIn('_norns.midi_send=_MOSAIC_HW_ORIG_MIDI',m.commands[1])
 def test_device_map_index_is_selected_by_id_not_fixed_offset(self):
  r,_,m=self.r();m.eval=lambda code:m.commands.append(code) or '__MOSAIC_DEVICE_MAP_INDEX__34\nmarker';self.assertEqual(r.device_map_index('emu-test'),34);self.assertIn("d.id=='emu-test'",m.commands[-1])
if __name__=='__main__':unittest.main()
