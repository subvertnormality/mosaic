package.path = './lib/?.lua;' .. package.path
local Host = require('rhythm_doctor.worker_host')
local calls, files = {}, {}
local host = Host.new({ code_root='/code/mosaic', runtime_root='/data/rd runtime',
  execute=function(command) calls[#calls+1]=command; return true end,
  read_line=function(path) return files[path] end,
  transport_factory=function(path) return {socket=path,send=function() end,poll=function() end} end })
local value, reason = host:open()
assert(value == nil and reason == 'worker starting' and #calls == 1)
assert(calls[1]:find("'/data/rd runtime'", 1, true), 'runtime path was not quoted')
host:open(); assert(#calls == 1, 'launcher repeated while starting')
files['/data/rd runtime/socket']='/tmp/owned/worker.sock'
files['/data/rd runtime/pid']='1234'
local transport=assert(host:open()); assert(transport.socket=='/tmp/owned/worker.sock')
host:close(); assert(#calls == 4 and calls[3]=='kill 1234 2>/dev/null')
assert(calls[4]:find("rm -f '/data/rd runtime/socket'", 1, true))
assert(select(2,host:open())=='worker host closed')
assert(Host.shell_quote("a'b") == "'a'\\''b'")
local AnalysisHost = require('rhythm_doctor.analysis_worker_host')
local analysis_calls, analysis_files = {}, {}
local analysis = AnalysisHost.new({ code_root='/code/mosaic', runtime_root='/data/analysis runtime', backend='/opt/rd-analysis',
  backend_sha256=string.rep('a',64), drum_artifact_sha256=string.rep('b',64), bass_artifact_sha256=string.rep('c',64),
  execute=function(command) analysis_calls[#analysis_calls+1]=command; return true end,
  read_line=function(path) return analysis_files[path] end,
  transport_factory=function(path) return {socket=path,send=function() end,poll=function() end} end })
assert(select(2,analysis:open())=='analysis worker starting')
assert(analysis_calls[1]:find("--backend '/opt/rd-analysis'",1,true))
assert(analysis_calls[1]:find("--backend-sha256 '"..string.rep('a',64).."'",1,true))
assert(analysis_calls[1]:find("--drum-artifact-sha256 '"..string.rep('b',64).."'",1,true))
assert(analysis_calls[1]:find("--bass-artifact-sha256 '"..string.rep('c',64).."'",1,true))
local incomplete = AnalysisHost.new({ code_root='/code/mosaic', runtime_root='/data/analysis incomplete', backend='/opt/rd-analysis',
  execute=function() error('partial configuration must not launch') end, read_line=function() end,
  transport_factory=function() error('partial configuration must not connect') end })
assert(select(2,incomplete:open())=='invalid pretrained analysis backend configuration')
print('rhythm_doctor worker_host: 1 test passed')
