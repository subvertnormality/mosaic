-- Actual scheduler functions; dependency stubs only, no timing/workflow claim.
program = {}
local slide_state
local function include_slide_lifetime(name)
 if name=='mosaic/lib/clock/slide_lifetime' then
  return {new=function(...)
   slide_state=dofile('lib/clock/slide_lifetime.lua').new(...)
   return slide_state
  end}
 end
end
function include(name)
 if name=='mosaic/lib/clock/transport_lifecycle' then return dofile('lib/clock/transport_lifecycle.lua') end
 if name=='mosaic/lib/clock/arp_lifetime' then return dofile('lib/clock/arp_lifetime.lua') end
  local slide_lifetime=include_slide_lifetime(name)
  if slide_lifetime then return slide_lifetime end
  if name=='mosaic/lib/devices/nrpn_codec' then return dofile('lib/devices/nrpn_codec.lua') end
  return {clock_divisions={}}
end
program.get=function()return {} end
local clock = dofile('lib/clock/m_clock.lua')

local initialise=function() return slide_state:reset() end
local sample=function() return slide_state:process() end
clock_lattice={transport=0}
local function tick() clock_lattice.transport=clock_lattice.transport+8;sample() end
initialise()
-- This is an ownership/callback unit fixture, not a musical timing oracle.
-- Explicit distance avoids unrelated program state; projection has dedicated
-- actual-lattice conformance and native application tests.
local function projected(_,distance) assert(distance==4);return 96 end
clock.channel_1_clock={project_onset_pulses=projected}
clock.channel_2_clock={project_onset_pulses=projected}
local function begin(channel,lock,callback)
  clock.execute_action_across_steps_by_pulses{channel_number=channel,trig_lock=lock,start_step=1,end_step=5,distance=4,start_value=24,end_value=96,quant=1,func=callback}
end
local tests={}
for _,count in ipairs({0,1,3}) do
  tests['silent_cancel_after_'..count]=function()
    local output={};begin(1,1,function(v) output[#output+1]=v end)
    for i=1,count do tick() end
    local before=#output
    clock.cancel_spread_actions_for_channel_trig_lock(1,1)
    assert(#output==before,'Cancellation emitted a stale value')
    for i=1,20 do tick() end
    assert(#output==before,'Cancelled slide emitted later')
    assert(not clock.channel_is_sliding({number=1},1))
  end
end
for _,count in ipairs({0,3}) do
  tests['explicit_finish_after_'..count]=function()
    local output={};begin(1,1,function(v) output[#output+1]=v end)
    for i=1,count do tick() end
    local before=#output
    clock.cancel_spread_actions_for_channel_trig_lock(1,1,true)
    assert(#output==before+1 and output[#output]==96,'Explicit finish must emit target exactly once, including before first sample')
    clock.cancel_spread_actions_for_channel_trig_lock(1,1,true)
    for i=1,20 do tick() end
    assert(#output==before+1,'Finished action emitted again')
  end
end
tests.channel_and_slot_isolation=function()
  begin(1,1,function() end);begin(1,2,function() end);begin(2,1,function() end)
  clock.cancel_spread_actions_for_channel_trig_lock(1,1)
  assert(not clock.channel_is_sliding({number=1},1))
  assert(clock.channel_is_sliding({number=1},2) and clock.channel_is_sliding({number=2},1))
  clock.cancel_spread_actions_for_channel_trig_lock(1)
  assert(not clock.channel_is_sliding({number=1},2) and clock.channel_is_sliding({number=2},1))
end
tests.reentrant_finish_cannot_repeat_old_action=function()
  local calls=0
  begin(1,1,function(v)
    if v==96 then
      calls=calls+1;assert(calls==1,'Old action still active during completion callback')
      clock.cancel_spread_actions_for_channel_trig_lock(1,1,true)
    end
  end)
  tick();clock.cancel_spread_actions_for_channel_trig_lock(1,1,true)
  assert(calls==1)
end
tests.reentrant_finish_preserves_replacement=function()
  local old_calls,new_calls=0,0
  begin(1,1,function(value)
    if value==96 then
      old_calls=old_calls+1
      begin(1,1,function() new_calls=new_calls+1 end)
    end
  end)
  clock.cancel_spread_actions_for_channel_trig_lock(1,1,true)
  assert(old_calls==1,'Original completion must run once')
  assert(clock.channel_is_sliding({number=1},1),'Outer cancellation consumed a reentrant replacement')
  tick()
  assert(new_calls==1 and old_calls==1,'Replacement must remain independently runnable')
  clock.cancel_spread_actions_for_channel_trig_lock(1,1)
  for i=1,20 do tick() end
  assert(new_calls==1,'Replacement ignored later explicit cancellation')
end
recorder=dofile('lib/recorder.lua')
local manager=dofile('lib/devices/param_manager.lua')
m_clock=clock
fn={deep_copy=function(t) local o={};for k,v in pairs(t) do o[k]=v end;return o end}
local function assigned_channel()
  return {number=1,trig_lock_params={{id='cc1',param_id='midi_device_params_channel_1_1',type='midi',device_name='CC'}}}
end
local meta={type='midi',device_name='CC'}
tests.reassignment_retires_only_old_parameter=function()
  local channel=assigned_channel();local old_calls=0
  begin(1,1,function() old_calls=old_calls+1 end)
  begin(1,2,function() end);begin(2,1,function() end)
  recorder.set_trig_lock_dirty(1,1,64);recorder.set_trig_lock_dirty(1,2,48);recorder.set_trig_lock_dirty(2,1,96)
  manager.update_param(1,channel,{id='cc2',index=2},meta)
  assert(recorder.trig_lock_is_dirty(1,1)==false)
  assert(recorder.trig_lock_is_dirty(1,2)==48 and recorder.trig_lock_is_dirty(2,1)==96)
  assert(not clock.channel_is_sliding(channel,1),'Reassigned parameter retained old slide')
  assert(clock.channel_is_sliding(channel,2) and clock.channel_is_sliding({number=2},1),'Reassignment cancelled unrelated slide')
  assert(old_calls==0,'Reassignment emitted stale completion')
  assert(not clock.handoff_spread_lock(1,1,5,96),'Old slide consumed new parameter endpoint')
  for i=1,20 do tick() end
  assert(old_calls==0)
end
tests.same_assignment_preserves_active_slide=function()
  local channel=assigned_channel()
  begin(1,1,function() end)
  recorder.set_trig_lock_dirty(1,1,64)
  manager.update_param(1,channel,{id='cc1',index=1},meta)
  assert(recorder.trig_lock_is_dirty(1,1)==64,'Unchanged assignment cleared recording')
  assert(clock.channel_is_sliding(channel,1),'Unchanged assignment cancelled slide')
end
tests.unassign_retires_old_slide=function()
  local channel=assigned_channel()
  begin(1,1,function() error('Unassigned callback emitted') end)
  manager.update_param(1,channel,{id='none'},meta)
  assert(not clock.channel_is_sliding(channel,1),'Unassigned slot retained active slide')
end
for _,field in ipairs({'id','param_id','type','device_name'}) do
  tests['reassignment_identity_'..field]=function()
    local channel=assigned_channel()
    local param={id='cc1',index=1,param_id='midi_device_params_channel_1_1'}
    local metadata={type='midi',device_name='CC'}
    if field=='id' then param.id='different'
    elseif field=='param_id' then param.index=2
    elseif field=='type' then metadata.type='norns'
    else metadata.device_name='Other' end
    begin(1,1,function() error('Changed identity emitted stale callback') end)
    manager.update_param(1,channel,param,metadata)
    assert(not clock.channel_is_sliding(channel,1),'Identity field failed to retire ownership: '..field)
  end
end
for _,changed in ipairs({false,true}) do
  tests['nrpn_mode_ownership_'..tostring(changed)]=function()
    local channel={number=1,trig_lock_params={{id='nrpn',param_id='midi_device_params_channel_1_1',
      type='midi',device_name='CC',nrpn_lsb_mode='legacy-half'}}}
    local mode=changed and 'standard' or 'legacy-half'
    begin(1,1,function() if changed then error('Old encoding callback survived mode change') end end)
    begin(1,2,function() end)
    manager.update_param(1,channel,{id='nrpn',index=1,nrpn_msb=4,nrpn_lsb=5,nrpn_lsb_mode=mode},meta)
    assert(clock.channel_is_sliding(channel,1)==not changed)
    assert(clock.channel_is_sliding(channel,2),'Mode edit cancelled a different slot')
    assert(channel.trig_lock_params[1].nrpn_lsb_mode==mode)
  end
end
tests.automatic_assignment_clears_only_its_channel_recording=function()
  local channel=assigned_channel()
  recorder.set_trig_lock_dirty(1,1,64);recorder.set_trig_lock_dirty(1,2,48)
  recorder.set_trig_lock_dirty(2,1,96)
  device_map={get_params=function()return {{id='cc2',index=2}} end}
  fn.find_in_table_by_id=function(values,id)for _,v in ipairs(values) do if v.id==id then return v end end end
  channel_edit_page_ui={refresh_trig_lock_values=function()end}
  manager.update_default_params(channel,{id='new',type='midi',device_name='CC',map_params_automatically={'cc2'}})
  assert(channel.trig_lock_params[1].id=='cc2')
  for slot=1,10 do assert(recorder.trig_lock_is_dirty(1,slot)==false) end
  assert(recorder.trig_lock_is_dirty(2,1)==96)
end
local failures=0;local count=0
local names={};for name in pairs(tests) do names[#names+1]=name end;table.sort(names)
for _,name in ipairs(names) do
  count=count+1
  local ok,err=pcall(tests[name]);if not ok then failures=failures+1 end
  print((ok and 'PASS ' or 'FAIL ')..name..(ok and '' or ': '..tostring(err)))
  -- Retire fixture-owned jobs even when an assertion fails.
  for channel=1,2 do pcall(clock.cancel_spread_actions_for_channel_trig_lock,channel) end
  for i=1,20 do tick() end
end
print(string.format('Collected %d; passed %d; failed %d',count,count-failures,failures))
os.exit(failures==0 and 0 or 1)
