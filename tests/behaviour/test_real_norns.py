import contextlib,hashlib,io,json,re,struct,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from real_norns import check_repl_lines,Maiden,MaidenInput,OSC,OutputTrace,Runner,SSH,SSHOSC,WebSocketMaiden,export_head,main,osc_packet
from hardware_driver import HARDWARE_DRIVER_CAPABILITIES,HARDWARE_PERFORMANCE_RECIPES,HardwareDriver,hardware_applicability,run_hardware_case
from cases import CASES
from driver import Driver
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
class TimeoutWS(WS):
 def __init__(self):super().__init__();self.reads=0
 def recv(self,timeout=None):
  self.reads+=1
  if self.reads==1:return 'discarded-prefix-'+('x'*3000)
  raise TimeoutError('socket timed out')
class S:
 def __init__(self,events=None):self.scripts=[];self.synced=[];self.events=events
 def run(self,x):self.scripts.append(x);self.events is not None and self.events.append('ssh');return type('R',(),{'stdout':'client MIDI\n'})()
 def rsync(self,a,b):self.synced.append((a,b))
 def push(self,a,b):self.pushed=(a,b)
 def fetch(self,a,b):b.write_bytes(b'\x89PNG\r\n\x1a\n'+b'0'*8+struct.pack('!II',640,384)+b'x');self.fetched=(a,b)
class M:
 def __init__(self,events=None):self.commands=[];self.events=events;self.closed=0
 def eval(self,x,**kwargs):self.commands.append(x);self.events is not None and self.events.append('maiden');return 'ok'
 def close(self):self.closed+=1
 def send(self,x):self.commands.append(x)
 def load(self,x,**kwargs):self.commands.append('load '+x);return 'ok'
class O:
 def send(self,*x):return {'args':x}
class T:
 def __init__(self):self.installed=0;self.removed=0;self.install_output='ok';self.reset_output='ok';self.snapshot_output='ok';self.remove_output='ok'
 def install(self,**kwargs):self.installed+=1;return self.install_output
 def remove(self,**kwargs):self.removed+=1;return self.remove_output
 def reset_midi(self,**kwargs):return self.reset_output
 def snapshot(self,**kwargs):
  result={'grid':[0]*128,'raw_grid':[0]*128,'midi':[]}
  return (result,self.snapshot_output) if kwargs.get('return_output') else result
class ClockSSH:
 def __init__(self,stock):self.path='/home/we/norns/lua/core/clock.lua';self.files={self.path:stock};self.scripts=[]
 def run(self,script):
  self.scripts.append(script)
  if script.startswith('sha256sum -- '):
   path=script.split('sha256sum -- ',1)[1];value=hashlib.sha256(self.files[path]).hexdigest()+'  '+path+'\n';return type('R',(),{'stdout':value})()
  if '\nmv ' in script:
   move=script.split('\nmv ',1)[1].split();self.files[move[1]]=self.files.pop(move[0])
  return type('R',(),{'stdout':''})()
 def fetch(self,remote,local):local.write_bytes(self.files[remote])
 def push(self,local,remote):self.files[remote]=Path(local).read_bytes()
class StaleClockM(M):
 def __init__(self):super().__init__();self.active_reads=0
 def stale(self):return "lua/core/clock.lua:62: bad argument #1 to 'resume' (thread expected, got nil)\nstack traceback:\n"
 def eval(self,x,allow_lua_error=False):
  self.commands.append(x)
  if '__MOSAIC_ACTIVE__' in x:
   self.active_reads+=1;return (self.stale() if self.active_reads>1 else '')+'__MOSAIC_ACTIVE__/home/we/dust/code/mosaic/mosaic.lua\n'
  if x=='norns.script.clear()' or x.startswith('clock=dofile('):return self.stale()+'marker\n'
  return 'ok'
 def load(self,x,allow_lua_error=False):
  self.commands.append('load '+x);return self.eval("print('__MOSAIC_ACTIVE__'..(norns.state.script or ''))",allow_lua_error=allow_lua_error)
class ExecuteThenRaiseM(M):
 def __init__(self):super().__init__();self.wrapped=False;self.allow=[]
 def eval(self,x,allow_lua_error=False):
  self.commands.append(x);self.allow.append(allow_lua_error)
  if '_MOSAIC_HW_ORIG_MIDI=original_midi' in x:self.wrapped=True;raise RuntimeError('marker response failed after execution')
  if '__TRACE_REMOVED__' in x:self.wrapped=False;return '__TRACE_REMOVED__C'
  return 'ok'
class PublicMidiM(M):
 def __init__(self):super().__init__();self.public_midi=False
 def eval(self,x,**kwargs):
  self.commands.append(x)
  if '_norns.midi_send(1,' in x:raise TypeError('stock MIDI binding requires userdata')
  if 'local probe_midi=midi.connect(1)' in x:self.public_midi=True
  return 'ok'
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
 def test_maiden_can_drain_expected_lua_errors_until_its_marker(self):
  ws=WS();ws.recv=lambda timeout=None:'stack traceback: expected baseline\n'+ws.sent[-1].split("print('",1)[1].split("')",1)[0]
  m=WebSocketMaiden('ws://norns:5555/',connector=lambda *a,**k:ws);self.assertIn('stack traceback:',m.eval('print(1)',allow_lua_error=True));m.close()
  ws=WS();ws.recv=lambda timeout=None:'stack traceback: unexpected\n'+ws.sent[-1].split("print('",1)[1].split("')",1)[0]
  m=WebSocketMaiden('ws://norns:5555/',connector=lambda *a,**k:ws)
  with self.assertRaisesRegex(RuntimeError,'Maiden Lua error'):m.eval('print(1)')
 def test_websocket_timeout_includes_only_bounded_accumulated_output(self):
  m=WebSocketMaiden('ws://norns:5555/',connector=lambda *a,**k:TimeoutWS())
  with self.assertRaises(TimeoutError) as caught:m.eval('print(1)')
  message=str(caught.exception);self.assertIn('output tail:',message);self.assertIn('x'*2000,message);self.assertNotIn('discarded-prefix',message);self.assertLess(len(message),2100)
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
  r,s,m=self.r();source=r.out/'config';source.mkdir();r.seed_config(source);self.assertIn('test ! -e /home/we/dust/data/mosaic/config',s.scripts[-1]);self.assertNotIn('rm -rf',s.scripts[-1]);self.assertEqual(s.synced[-1][1],'/home/we/dust/data/mosaic/config');self.assertIn('norns.script.clear()',m.commands[-2]);self.assertIn('load /home/we/dust/code/mosaic/mosaic.lua',m.commands[-1])
 def test_tree_transfer_is_tar_into_empty_directory_without_delete(self):
  t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);root=Path(t.name);(root/'a.lua').write_text('x');ssh=SSH('we@norns',['-S','/tmp/control'])
  with patch('real_norns.subprocess.run') as run:ssh.rsync(root,'/home/we/dust/code/.staging')
  argv=run.call_args.args[0];self.assertEqual(argv[:4],['ssh','-S','/tmp/control','we@norns']);self.assertNotIn('--delete',' '.join(argv));self.assertIn('test -z',argv[-1]);self.assertIn('tar -C',argv[-1]);self.assertTrue(run.call_args.kwargs['input'])
 def test_expected_clock_error_maiden_records_queued_resume_and_rejects_other_errors(self):
  r,_,_=self.r();inner=type('M',(),{'eval':lambda self,code,allow_lua_error=False:self.out,'out':"lua: /home/we/norns/lua/core/clock.lua:62: bad argument #1 to 'resume' (thread expected)\nstack traceback:\n"})();wrapped=__import__('real_norns').ExpectedClockErrorMaiden(inner,r,'performance')
  wrapped.eval('x');self.assertEqual(r.clock_error_drains,[{'phase':'performance','expected_queued_resume_errors':1}])
  inner.out="lua: mosaic.lua:1: attempt to index a nil value\nstack traceback:\n"
  with self.assertRaises(RuntimeError):wrapped.eval('y')
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
  m=M();m.eval=lambda code,**kwargs:('__GRID_COUNTS__12,3\n'+rows+'\n__MIDI_COUNT__1\n') if '__GRID_COUNTS__' in code else '__MIDI__1|12.250000000|1|userdata: 0xabc|table|144,60,127\n'
  value=OutputTrace(m).snapshot();self.assertEqual(value['raw_grid'][112],-4);self.assertEqual(value['grid'][112],12);self.assertEqual((value['midi'][0]['port'],value['midi'][0]['bytes']),(1,[144,60,127]))
 def test_output_trace_reads_a_long_capture_in_chunks_and_retries_a_lost_reply(self):
  rows='\n'.join('__GRID_ROW__%d|%s'%(y,','.join(['0']*16)) for y in range(1,9));calls=[];lost=[]
  def event(i):return '__MIDI__%d|%d.000000000|1|userdata: 0xabc|table|176,1,%d'%(i,i,i%128)
  def eval(code,allow_lua_error=False,timeout_ms=None):
   calls.append((code,timeout_ms))
   if '__GRID_COUNTS__' in code:return '__GRID_COUNTS__0,0\n'+rows+'\n__MIDI_COUNT__900\n'
   first,last=[int(v) for v in re.search(r'for i=(\d+),(\d+)',code).groups()]
   if first==401 and not lost:lost.append(first);raise TimeoutError('marker lost')
   # A late reply from another range must not be taken for this one.
   return event(1)+'\n'+'\n'.join(event(i) for i in range(first,last+1))+'\n'
  m=M();m.eval=eval
  value=OutputTrace(m).snapshot()
  self.assertEqual([e['index'] for e in value['midi']],list(range(1,901)))
  ranges=[re.search(r'for i=(\d+),(\d+)',code).groups() for code,_ in calls[1:]]
  self.assertEqual(ranges,[('1','400'),('401','800'),('401','800'),('801','900')])
  self.assertTrue(all(timeout==OutputTrace.SNAPSHOT_CHUNK_TIMEOUT_MS for _,timeout in calls[1:]))
 def test_output_trace_gives_up_on_a_chunk_that_never_completes(self):
  rows='\n'.join('__GRID_ROW__%d|%s'%(y,','.join(['0']*16)) for y in range(1,9))
  m=M();m.eval=lambda code,**kwargs:('__GRID_COUNTS__0,0\n'+rows+'\n__MIDI_COUNT__2\n') if '__GRID_COUNTS__' in code else '__MIDI__1|1.0|1|d|table|144,60,1\n'
  with self.assertRaisesRegex(RuntimeError,'chunk 1-2 incomplete'):OutputTrace(m).snapshot()
 def test_output_trace_uses_persistent_globals_and_restores_c_binding(self):
  m=M();m.eval=lambda code,**kwargs:m.commands.append(code) or ('__TRACE_REMOVED__C' if '__TRACE_REMOVED__' in code else 'ok')
  trace=OutputTrace(m);trace.install();trace.remove();self.assertIn('__NOT_STOCK__',m.commands[0]);self.assertIn('local original_midi=_norns.midi_send',m.commands[1]);self.assertIn('return original_midi(dev,payload,...)',m.commands[1]);self.assertIn('return original_grid_all(dev,value,rel,...)',m.commands[1]);self.assertIn('return original_grid_led(dev,x,y,value,rel,...)',m.commands[1]);self.assertIn('grid_state.writes',m.commands[1]);self.assertIn('v.device.dev==dev',m.commands[1]);self.assertIn('_norns.midi_send=_MOSAIC_HW_ORIG_MIDI',m.commands[2])
 def test_output_trace_refuses_to_wrap_a_binding_an_earlier_trace_left_wrapped(self):
  class Wrapped(M):
   def eval(self,x,**kwargs):self.commands.append(x);return '__NOT_STOCK__midi_send\n__NOT_STOCK__grid_set_led\n<ok>' if '__NOT_STOCK__' in x else 'ok'
  m=Wrapped();trace=OutputTrace(m)
  with self.assertRaisesRegex(RuntimeError,'_norns.midi_send, _norns.grid_set_led is not the stock binding'):trace.install()
  self.assertEqual(len(m.commands),1);self.assertFalse(trace.installed)
 def test_trace_commands_fit_matrons_repl_line_buffer(self):
  class Removed(M):
   def eval(self,x,**kwargs):self.commands.append(x);return '__TRACE_REMOVED__C'
  m=Removed();trace=OutputTrace(m);trace.install();trace.reset_midi();trace.remove()
  self.assertEqual(len(m.commands),4)
  for command in m.commands:check_repl_lines(command.rstrip()+"; print('__MOSAIC_HW_0123456789abcdef__')\n")
 def test_maiden_refuses_a_line_matron_cannot_read_without_sending_it(self):
  sent=[]
  class Socket:
   def send(self,data):sent.append(data)
  maiden=WebSocketMaiden('ws://example',connector=lambda url,timeout:Socket())
  with self.assertRaisesRegex(ValueError,'exceeds the 4096-byte matron REPL buffer'):maiden.eval('x=1 '+'-'*4096)
  with self.assertRaisesRegex(ValueError,'4096-byte'):maiden.send('y=2 '+'-'*4096)
  self.assertEqual(sent,[]);check_repl_lines('z=3\n'+'-'*4094+'\n')
 def test_output_trace_reset_mutates_the_table_captured_by_wrappers(self):
  m=M();trace=OutputTrace(m);trace.reset_midi();self.assertIn('_MOSAIC_HW_MIDI.n=0',m.commands[0]);self.assertIn('_MOSAIC_HW_MIDI_REALTIME.count=0',m.commands[0]);self.assertNotIn('_MOSAIC_HW_MIDI={}',m.commands[0])
 def test_output_trace_install_cleans_up_when_code_executes_then_eval_raises(self):
  m=ExecuteThenRaiseM();trace=OutputTrace(m)
  with self.assertRaisesRegex(RuntimeError,'marker response failed'):trace.install(allow_lua_error=True)
  self.assertFalse(m.wrapped);self.assertFalse(trace.installed);self.assertEqual(len(m.commands),3);self.assertEqual(m.allow,[True,True,True]);self.assertIn('__TRACE_REMOVED__',m.commands[2])
 def test_device_map_index_is_selected_by_id_not_fixed_offset(self):
  r,_,m=self.r();m.eval=lambda code:m.commands.append(code) or '__MOSAIC_DEVICE_MAP_INDEX__34\nmarker';self.assertEqual(r.device_map_index('emu-test'),34);self.assertIn("d.id=='emu-test'",m.commands[-1])
 def test_a_grid_tap_reports_when_the_host_sent_and_finished_each_half(self):
  r,_,m=self.r();m.eval=lambda code:m.commands.append(code) or "__MOSAIC_TEMPO__120\nmarker";driver=HardwareDriver(r,2,'emu-test',T())
  with patch('hardware_driver.time.sleep'):tap=driver.tap(1,8)
  self.assertEqual((tap['press']['state'],tap['release']['state']),(1,0))
  self.assertTrue(tap['press']['host_monotonic_ns']<=tap['press']['host_completion_ns']<=tap['release']['host_monotonic_ns']<=tap['release']['host_completion_ns'])
  self.assertIn('_norns.grid.key(2,1,8,1)',m.commands[-2]);self.assertIn('_norns.grid.key(2,1,8,0)',m.commands[-1])
 def test_hardware_driver_exposes_the_recipe_surface_and_rejects_unknown_actions(self):
  r,_,m=self.r();m.eval=lambda code:"__MOSAIC_TEMPO__120\nmarker";trace=T();driver=HardwareDriver(r,2,'emu-test',trace)
  public={name for name,value in Driver.__dict__.items() if not name.startswith('_') and callable(value)}
  self.assertEqual(public,{'action','elapse','snapshot','wait','tap','key','enc','hold_tap','led_values','screen_header','configure','playback','finish'})
  self.assertTrue(all(callable(getattr(driver,name,None)) for name in public))
  with self.assertRaisesRegex(NotImplementedError,'midi'):driver.action(type='midi',port=1,bytes=[144,60,127])
  driver.finish();self.assertEqual((trace.installed,trace.removed),(1,1))
 def test_hardware_snapshot_normalizes_the_public_state_shape(self):
  r,_,m=self.r();m.eval=lambda code:"__MOSAIC_TEMPO__120\nmarker";trace=T();trace.snapshot=lambda:{'grid':[0]*128,'raw_grid':[0]*128,'midi':[{'index':1,'monotonic_seconds':12.25,'port':3,'device':'userdata: 0xabc','payload_type':'table','bytes':[144,60,127]}]}
  driver=HardwareDriver(r,2,'emu-test',trace);state=driver.snapshot();driver.finish()
  self.assertEqual((state['midi_count'],state['midi'][0]['port'],state['midi'][0]['monotonic_ns']),(1,3,12250000000));self.assertTrue(state['midi_capture']['outstanding'])
  self.assertEqual(driver.observations[0]['source'],'stock-norns-output-trace')
 def test_hardware_snapshot_rejects_unresolved_userdata_instead_of_parsing_pointer_digits(self):
  r,_,m=self.r();m.eval=lambda code:"__MOSAIC_TEMPO__120\nmarker";trace=T();trace.snapshot=lambda:{'grid':[0]*128,'raw_grid':[0]*128,'midi':[{'index':1,'monotonic_seconds':12.25,'port':0,'device':'userdata: 0x683c60','payload_type':'table','bytes':[144,60,127]}]}
  driver=HardwareDriver(r,2,'emu-test',trace)
  with self.assertRaisesRegex(RuntimeError,'Cannot map traced MIDI device'):driver.snapshot()
  driver.finish()
 def test_hardware_case_executes_the_registered_recipe(self):
  r,_,m=self.r();m.eval=lambda code:"__MOSAIC_TEMPO__120\nmarker";trace=T();seen=[]
  original=CASES['M-PAT-001']['run'];CASES['M-PAT-001']['run']=lambda driver:(seen.append(driver),driver.results.append({'kind':'selected-pattern-blink-cycle','levels':[4,2]}))
  try:evidence=run_hardware_case(r,'M-PAT-001',2,'emu-test',trace)
  finally:CASES['M-PAT-001']['run']=original
  self.assertEqual(len(seen),1);self.assertIsInstance(seen[0],HardwareDriver);self.assertEqual(evidence['case'],'M-PAT-001');self.assertEqual(trace.removed,1)
 def test_applicability_is_fail_closed_and_distinguishes_lane_and_fault_limits(self):
  report=hardware_applicability(CASES);rows={row['case']:row for row in report['cases']}
  self.assertEqual(set(rows),set(CASES));self.assertEqual([row['case'] for row in rows.values() if row['applicable']],['M-PAT-001'])
  self.assertEqual(rows['M-ARP-005']['category'],'controlled-only');self.assertEqual(rows['M-TIM-005']['category'],'emulator-only-fault')
  self.assertEqual(rows['M-TIM-001']['category'],'targeted-hardware-qualification');self.assertEqual(rows['M-SYNC-009']['qualification_targets'],['midi-master-slave-sync'])
  self.assertEqual(rows['M-SYNC-022']['qualification_targets'],['musical-timing-drift','midi-master-slave-sync'])
  self.assertEqual(rows['M-PAT-002']['category'],'broad-functional-emulator-coverage')
  self.assertEqual(report['capabilities']['broad_functional_suite'],'emulator-coverage')
  self.assertEqual(report['capabilities']['qualification_targets']['performance-load']['status'],'partial-unverified');self.assertFalse(report['performance_recipes']['perf_dense.py']['hardware_verified'])
  self.assertEqual(report['capabilities']['qualification_targets']['stock-clock-cancel-queued-resume']['status'],'implemented')
  self.assertEqual(report['performance_recipes'],HARDWARE_PERFORMANCE_RECIPES)
  self.assertEqual(report['performance_recipes']['perf_dense.py']['adaptation'],'hardware-calibration')
  self.assertIn('scheduled external-MIDI ingress',report['performance_recipes']['perf_input.py']['capability_gaps'])
  self.assertIn('bounded repeatable on-device load generator',report['performance_recipes']['perf_overload.py']['capability_gaps'])
  self.assertEqual(report['performance_recipes']['perf_storage.py']['status'],'excluded')
 def test_applicability_command_needs_no_hardware_or_emulator(self):
  with contextlib.redirect_stdout(io.StringIO()) as output:self.assertEqual(main(['applicability']),0)
  report=json.loads(output.getvalue());self.assertEqual(report['schema_version'],1);self.assertEqual(report['capabilities'],HARDWARE_DRIVER_CAPABILITIES)
 def test_clock_cancel_probe_requires_immediate_and_delayed_midi(self):
  r,_,_=self.r();m=PublicMidiM();r.maiden=m;trace=T();trace.snapshot=lambda **kwargs:({'grid':[0]*128,'raw_grid':[0]*128,'midi':[{'bytes':[176,77,1]},{'bytes':[176,78,1]}]},'ok') if kwargs.get('return_output') else {}
  with patch('real_norns.OutputTrace',return_value=trace),patch('real_norns.time.sleep'):
   result=r.clock_cancel_probe('candidate')
  self.assertTrue(result['passed']);self.assertTrue(m.public_midi);self.assertIn('pcall(clock.resume,99999999)',m.commands[0]);self.assertIn('probe_midi:cc(77,1,1)',m.commands[0]);self.assertNotIn('_norns.midi_send(1,',m.commands[0]);self.assertEqual(trace.removed,1)
 def test_clock_cancel_probe_drains_only_expected_trace_install_and_remove_errors(self):
  r,_,m=self.r();trace=T();stale="bad argument #1 to 'resume' (thread expected, got nil)\nstack traceback:\n";trace.install_output=stale;trace.reset_output=stale;trace.snapshot_output=stale;trace.remove_output=stale
  trace.snapshot=lambda **kwargs:({'midi':[{'bytes':[176,77,1]},{'bytes':[176,78,1]}]},trace.snapshot_output) if kwargs.get('return_output') else {'midi':[]}
  m.eval=lambda code,**kwargs:m.commands.append(code) or stale
  with patch('real_norns.OutputTrace',return_value=trace),patch('real_norns.time.sleep'):result=r.clock_cancel_probe('stock-baseline')
  self.assertFalse(result['passed']);self.assertEqual(result['expected_queued_resume_errors'],6);self.assertIn('Expected stock queued-resume',result['failure'])
  self.assertEqual([row['phase'] for row in r.clock_error_drains],['install-stock-baseline-trace','reset-stock-baseline-trace','exercise-stock-baseline','settle-stock-baseline','snapshot-stock-baseline-trace','remove-stock-baseline-trace']);self.assertEqual(trace.removed,1)
  trace=T();trace.install_output='unrelated failure\nstack traceback:\n'
  with patch('real_norns.OutputTrace',return_value=trace):result=r.clock_cancel_probe('stock-baseline')
  self.assertFalse(result['passed']);self.assertIn('Unexpected Lua error',result['failure']);self.assertEqual(trace.removed,1)
 def test_clock_cancel_comparison_restores_exact_stock_hash_without_service_restart(self):
  temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);out=Path(temporary.name);candidate=out/'candidate-clock.lua';candidate.write_bytes(b'candidate')
  ssh=ClockSSH(b'stock');m=M();m.eval=lambda code,**kwargs:m.commands.append(code) or '__MOSAIC_ACTIVE__/home/we/dust/code/mosaic/mosaic.lua\n';r=Runner(ssh,m,O(),out,'clock-run')
  seen=[]
  def probe(label):seen.append((label,hashlib.sha256(ssh.files[ssh.path]).hexdigest()));return {'label':label,'passed':label=='temporary-candidate','failure':None,'midi':[]}
  with patch.object(r,'clock_cancel_probe',side_effect=probe):evidence=r.clock_cancel_comparison(candidate)
  self.assertEqual([label for label,_ in seen],['stock-baseline','temporary-candidate']);self.assertNotEqual(seen[0][1],seen[1][1])
  self.assertTrue(evidence['stock_restored']);self.assertEqual(ssh.files[ssh.path],b'stock');self.assertTrue(evidence['no_reboot_or_jack_restart'])
  self.assertFalse(any('reboot' in script or 'systemctl restart' in script for script in ssh.scripts));self.assertIn('load /home/we/dust/code/mosaic/mosaic.lua',m.commands[-1])
 def test_clock_cancel_comparison_drains_stale_stock_errors_during_control_and_reload(self):
  temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);out=Path(temporary.name);candidate=out/'candidate-clock.lua';candidate.write_bytes(b'candidate')
  ssh=ClockSSH(b'stock');m=StaleClockM();r=Runner(ssh,m,O(),out,'stale-run')
  with patch.object(r,'clock_cancel_probe',side_effect=[{'label':'stock-baseline','passed':False},{'label':'temporary-candidate','passed':True}]):evidence=r.clock_cancel_comparison(candidate)
  self.assertTrue(evidence['stock_restored']);self.assertEqual(ssh.files[ssh.path],b'stock');self.assertTrue(evidence['active_script_reloaded'])
  self.assertEqual([row['phase'] for row in evidence['expected_error_drains']],['clear-before-stock-baseline','load-stock-baseline','load-temporary-candidate','reload-restored-stock','reload-prior-active-script'])
 def test_clock_control_rejects_unrelated_lua_errors(self):
  r,_,m=self.r();m.eval=lambda code,**kwargs:'different failure\nstack traceback:\n'
  r.clock_error_drains=[]
  with self.assertRaisesRegex(RuntimeError,'Unexpected Lua error'):r.clock_control_eval('x','test')
if __name__=='__main__':unittest.main()
