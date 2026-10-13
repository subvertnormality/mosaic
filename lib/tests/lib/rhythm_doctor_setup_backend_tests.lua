-- Characterisation: authorized new Manual BPM/Input backend functionality,
-- 3 October 2026. The former README explicitly called these display-only.
-- Native public ADC cases supply player-visible and recorded-signal acceptance.
local Adapter=include("mosaic/lib/rhythm_doctor/ui_adapter")
local Runtime=include("mosaic/lib/rhythm_doctor/runtime")
local Recorder=include("mosaic/lib/rhythm_doctor/softcut_recorder")
local function transport()
  local value={sent={}}
  function value:send(message)self.sent[#self.sent+1]=message;return true end
  function value:poll()return nil end
  function value:close()end
  return value
end
local function runtime()
  local capture,analysis=transport(),transport()
  local worker={opens=0}
  function worker:open()self.opens=self.opens+1;return capture end
  function worker:close()end
  local value=Runtime.new{project_id="setup-test",worker=worker,analysis_transport=analysis,
    now=function()return 0 end,transport_stopped=function()return true end}
  return value,capture,analysis,worker
end
local function asset(value,frames)
  local token=value.machine:job_token()
  return {wav_path="/tmp/capture.wav",wav_sha256=string.rep("a",64),frames=frames,sample_rate=48000,
    project_id=token.project_id,generation=token.generation,analysis_revision=token.analysis_revision}
end
function test_rhythm_doctor_setup_backend_adapter_commits_and_forwards_values()
  local received
  local runtime={machine={state="EMPTY"},record_action=function()error("unexpected modal")end,
    confirm_modal=function()error("unexpected confirmation")end,finish=function()error("unexpected finish")end}
  function runtime:start_capture(mode,settings)received={mode=mode,settings=settings};return {ok=true,code="OK"}end
  local owner=Adapter.new{runtime=runtime,transport_stopped=function()return true end}
  owner:enc(3,1);owner:enc(2,1);owner:enc(3,-20);owner:enc(2,1);owner:enc(3,1)
  owner:key(3,1);owner:grid_key(1,2,1)
  luaunit.assert_equals(received.mode,"manual")
  luaunit.assert_equals(received.settings,{manual_bpm=100,input_source="left"})
end
function test_rhythm_doctor_setup_backend_runtime_freezes_source_and_manual_analysis()
  local value,capture,analysis=runtime()
  local settings={manual_bpm=100,input_source="right"}
  luaunit.assert_true(value:start_capture("manual",settings).ok)
  settings.manual_bpm=200;settings.input_source="left"
  luaunit.assert_equals(capture.sent[1].input_source,"right")
  value.machine.state="ANALYSING"
  local token=value.machine:job_token()
  value:_analysis_ready(asset(value,480000),token)
  luaunit.assert_equals(analysis.sent[1].alignment.bpm,100)
  luaunit.assert_equals(analysis.sent[1].alignment.origin_sample,0)
end
function test_rhythm_doctor_setup_backend_auto_omits_manual_alignment()
  local value,capture,analysis=runtime()
  luaunit.assert_true(value:start_capture("auto",{manual_bpm=100,input_source="left"}).ok)
  luaunit.assert_equals(capture.sent[1].input_source,"left")
  value.machine.state="ANALYSING"
  value:_analysis_ready(asset(value,480000),value.machine:job_token())
  luaunit.assert_nil(analysis.sent[1].alignment)
end
function test_rhythm_doctor_setup_backend_rejects_invalid_values_before_open()
  for _,settings in ipairs({{manual_bpm=39,input_source="left"},{manual_bpm=241,input_source="right"},
    {manual_bpm=0/0,input_source="stereo"},{manual_bpm=100,input_source="both"},{manual_bpm=100.5,input_source="stereo"}})do
    local value,_,_,worker=runtime()
    luaunit.assert_false(value:start_capture("manual",settings).ok)
    luaunit.assert_equals(worker.opens,0)
    luaunit.assert_equals(value.machine.state,"EMPTY")
  end
end
local function recorder()
  local levels={};local sc=setmetatable({}, {__index=function()return function()end end})
  sc.level_input_cut=function(input,voice,level)levels[input..":"..voice]=level end
  local owner=Recorder.new{directory="/tmp/setup-test",softcut=sc,audio={level_adc_cut=function()end},
    now=function()return 0 end,execute=function()return true end,adc_cut_level=function()return .5 end}
  return owner,levels
end
local function request(source)
  return {protocol_version=1,job_id="capture-1",project_id="setup-test",generation=1,analysis_revision=0,
    command="PREFLIGHT",mode="manual",seconds=25,input_source=source}
end
function test_rhythm_doctor_setup_backend_recorder_routes_only_selected_adc()
  for _,source in ipairs({"stereo","left","right"})do
    local owner,levels=recorder();owner:send(request(source))
    luaunit.assert_equals(owner:poll().status,"READY")
    for voice=1,2 do
      local input=source=="left" and 1 or source=="right" and 2 or voice
      luaunit.assert_equals(levels[input..":"..voice],1)
      luaunit.assert_equals(levels[(3-input)..":"..voice],0)
    end
  end
end
function test_rhythm_doctor_setup_backend_recorder_invalid_source_refuses_acquisition()
  for _,source in ipairs({"invalid",false,100})do
    local owner,levels=recorder();owner:send(request(source))
    local reply=owner:poll();luaunit.assert_equals(reply.status,"FAILED")
    luaunit.assert_equals(reply.capture_error,"INVALID_INPUT_SOURCE")
    luaunit.assert_equals(levels,{})
  end
end

function test_rhythm_doctor_setup_backend_manual_bounds_reach_analysis_exactly()
  for _,bpm in ipairs({40,240})do
    local value,capture,analysis=runtime()
    luaunit.assert_true(value:start_capture("manual",{manual_bpm=bpm,input_source="stereo"}).ok)
    value.machine.state="ANALYSING"
    value:_analysis_ready(asset(value,1200000),value.machine:job_token())
    luaunit.assert_equals(analysis.sent[1] and analysis.sent[1].alignment,{bpm=bpm,origin_sample=0})
  end
end
function test_rhythm_doctor_setup_backend_explicit_alignment_takes_precedence()
  local value,_,analysis=runtime()
  value:start_capture("manual",{manual_bpm=100,input_source="left"})
  value.alignment={bpm=130,origin_sample=48000,start_beat=2,fine_start_ms=0}
  value.machine.state="ANALYSING"
  value:_analysis_ready(asset(value,1200000),value.machine:job_token())
  luaunit.assert_equals(analysis.sent[1].alignment,value.alignment)
end
function test_rhythm_doctor_setup_backend_bad_settings_shape_has_no_worker_side_effect()
  for _,settings in ipairs({false,100,"left"})do
    local value,_,_,worker=runtime()
    local ok,outcome=pcall(value.start_capture,value,"manual",settings)
    luaunit.assert_true(ok)
    luaunit.assert_false(outcome.ok)
    luaunit.assert_equals(worker.opens,0)
  end
end
