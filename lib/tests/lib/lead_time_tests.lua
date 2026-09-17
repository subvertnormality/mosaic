-- README: MIDI Device Configuration / Lock lead time. Inject time and timers;
-- no wall-clock sleeps, so pulse grouping and preserved gate lengths are exact.
local delay_line = include("mosaic/lib/clock/midi_delay_line")
local function fixture()
  local now, timers, sent, begins, flushes = 0, {}, {}, 0, 0
  local q = delay_line.new({
    now = function() return now end,
    timer = function(callback)
      local t = {callback=callback, starts=0}
      function t:start(seconds) self.due=now+seconds;self.starts=self.starts+1 end
      function t:stop() self.due=nil end
      function t:free() self:stop() end
      timers[#timers+1]=t
      return t
    end,
    begin = function() begins=begins+1 end,
    flush = function() flushes=flushes+1 end,
    send = function(message) sent[#sent+1]={now,message} end
  })
  local function advance(value)
    now=value
    for _,t in ipairs(timers) do
      if t.due and t.due<=now+1e-10 then t.due=nil;t.callback() end
    end
  end
  return q,sent,timers,advance,function() return begins,flushes end
end
function test_lead_time_zero_is_synchronous_without_timer_or_batch()
  local q,sent,timers,_,counts=fixture()
  q:push(0,"on")
  luaunit.assert_equals(sent,{{0,"on"}})
  luaunit.assert_equals(#timers,0)
  luaunit.assert_equals({counts()},{0,0})
end
function test_lead_time_groups_pulse_and_preserves_longer_than_pulse_gates()
  local q,sent,timers,advance,counts=fixture()
  q:begin();q:push(5,"start");q:push(5,"clock");q:push(5,"on1");q:push(5,"on2");q:finish()
  advance(.002)
  q:begin();q:push(5,"off1");q:push(5,"off2");q:finish()
  luaunit.assert_equals(sent,{})
  luaunit.assert_equals(#timers,1)
  luaunit.assert_equals(timers[1].starts,1)
  advance(.005)
  luaunit.assert_equals(sent,{{.005,"start"},{.005,"clock"},{.005,"on1"},{.005,"on2"}})
  advance(.007)
  luaunit.assert_equals(sent[5],{.007,"off1"})
  luaunit.assert_equals(sent[6],{.007,"off2"})
  luaunit.assert_equals({counts()},{2,2})
end
function test_lead_time_drain_preserves_generation_order_across_leads_and_cancels()
  local q,sent,timers,advance=fixture()
  q:begin();q:push(10,"on1");q:push(5,"on2");q:push(10,"off1");q:finish()
  q:drain()
  luaunit.assert_equals(sent,{{0,"on1"},{0,"on2"},{0,"off1"}})
  advance(1)
  luaunit.assert_equals(#sent,3)
  for _,t in ipairs(timers) do luaunit.assert_nil(t.due) end
end
function test_lead_time_distinct_leads_and_overdue_groups()
  local q,sent,timers,advance=fixture()
  q:begin();q:push(5,"a");q:push(10,"b");q:finish()
  advance(.002);q:push(5,"c")
  luaunit.assert_equals(#timers,2)
  advance(.009)
  luaunit.assert_equals(sent,{{.009,"a"},{.009,"c"}})
  advance(.010)
  luaunit.assert_equals(sent[3],{.010,"b"})
  q:close()
end

local function with_midi_lead(run, fallback)
  local saved={midi_devices=midi_devices,midi=midi,metro=metro,clock=clock,
    program=program,device_map=device_map,time=util.time,
    m_clock=m_clock,clock_lattice=clock_lattice,handle=handle_midi_event_data}
  local now,timers,writes=0,{},{}
  util.time=function() return now end
  local function timer(callback)
    local t={event=callback,id=#timers+1}
    function t:start(delay) self.due=now+delay end
    function t:stop() self.due=nil end
    timers[#timers+1]=t;return t
  end
  metro={init=function(callback) if not fallback then return timer(callback) end end,
    free=function(id) timers[id]:stop() end}
  clock={run=function(f)
    local co=coroutine.create(f);local ok,delay=coroutine.resume(co);assert(ok,delay)
    local t=timer(function() local ok,err=coroutine.resume(co);assert(ok,err) end)
    t:start(delay);return t.id
  end,sleep=function(delay) coroutine.yield(delay) end,cancel=function(id) timers[id]:stop() end}
  local Device={};Device.__index=Device
  function Device:send(bytes)
    local copy={} for i,v in ipairs(bytes) do copy[i]=v end
    writes[#writes+1]={now,copy}
  end
  local port={device=setmetatable({},Device)}
  function port:note_off(n,v,c) if self.device then self.device:send({0x80+c-1,n,v}) end end
  function port:start() self.device:send({250}) end
  function port:clock() self.device:send({248}) end
  function port:stop() self.device:send({252}) end
  function port:continue() self.device:send({251}) end
  function port:song_position(a,b) self.device:send({242,a,b}) end
  midi={vports={port}}
  local output=include("mosaic/lib/m_midi")
  midi_devices={port}
  output.set_lead_time(5)
  local function advance(t)
    now=t
    for _,timer in ipairs(timers) do
      if timer.due and timer.due<=now+1e-9 then timer.due=nil;timer.event() end
    end
  end
  local ok,err=pcall(run,output,writes,timers,advance,port)
  output.cleanup()
  midi_devices=saved.midi_devices;midi=saved.midi;metro=saved.metro;clock=saved.clock
  program=saved.program;device_map=saved.device_map;util.time=saved.time
  m_clock=saved.m_clock;clock_lattice=saved.clock_lattice;handle_midi_event_data=saved.handle
  if not ok then error(err,0) end
end
function test_lead_time_midi_locks_immediate_notes_batched_and_gates_unchanged()
  with_midi_lead(function(out,writes,timers,advance)
    out.begin_output_batch();out.cc(74,nil,90,1,1);out.flush_output_batch()
    out:note_on(60,100,1,1,5);out:note_on(64,90,2,1,5);out.flush_output_batch(true)
    luaunit.assert_equals(writes,{{0,{176,74,90}}})
    luaunit.assert_equals(#timers,1)
    advance(.005)
    luaunit.assert_equals(writes[2],{.005,{144,60,100,145,64,90}})
    advance(.100)
    out.begin_output_batch();out:note_off(60,100,1,1,5);out:note_off(64,90,2,1,5);out.flush_output_batch(true)
    advance(.105)
    luaunit.assert_equals(writes[3],{.105,{128,60,100,129,64,90}})
  end)
end
function test_lead_time_stop_drains_notes_before_releases_and_delayed_stop()
  with_midi_lead(function(out,writes,_,advance,port)
    local original=port.clock
    out.install_clock_hooks();port:start();port:clock();out:note_on(60,100,1,1,5)
    out.stop()
    luaunit.assert_equals(writes,{{0,{250}},{0,{248}},{0,{144,60,100}},{0,{128,60,0}}})
    advance(.005)
    luaunit.assert_equals(writes[5],{.005,{252}})
    advance(.050);luaunit.assert_equals(#writes,5)
    out.cleanup();luaunit.assert_equals(port.clock,original)
  end)
end
function test_lead_time_clock_start_spp_and_continue_shift_together()
  with_midi_lead(function(out,writes,_,advance,port)
    out.install_clock_hooks()
    port:song_position(1,2);port:start();port:clock();port:continue()
    luaunit.assert_equals(writes,{})
    advance(.005)
    luaunit.assert_equals(writes,{{.005,{242,1,2}},{.005,{250}},{.005,{248}},{.005,{251}}})
  end)
end
function test_lead_time_clock_fallback_without_free_metros()
  with_midi_lead(function(out,writes,_,advance)
    out:note_on(60,100,1,1,5)
    advance(.005);luaunit.assert_equals(writes,{{.005,{144,60,100}}})
  end,true)
end
function test_lead_time_disconnected_pending_note_is_not_rerouted()
  with_midi_lead(function(out,writes,_,advance,port)
    out:note_on(60,100,1,1,5);port.device=nil
    advance(.005);luaunit.assert_equals(writes,{})
  end)
end

function test_lead_time_sustained_overlapping_pulses_do_not_drop_or_reorder()
  local q,sent,_,advance=fixture()
  for i=0,199 do
    advance(i*.001);q:begin();q:push(50,i);q:finish()
  end
  advance(.3)
  luaunit.assert_equals(#sent,200)
  for i,item in ipairs(sent) do luaunit.assert_equals(item[2],i-1) end
end
function test_lead_time_global_zero_bypasses_queue_and_clock_is_immediate()
  with_midi_lead(function(out,writes,timers,_,port)
    out.set_lead_time(0);out.install_clock_hooks()
    port:start();port:clock();out:note_on(60,100,1,1);out:note_off(60,100,1,1)
    luaunit.assert_equals(writes,{{0,{250}},{0,{248}},{0,{144,60,100}},{0,{128,60,100}}})
    luaunit.assert_equals(#timers,0)
  end)
end
function test_lead_time_panic_drains_pending_onsets_before_sweep()
  with_midi_lead(function(out,writes,_,advance)
    local old=scheduler
    scheduler={debounce=function(f) return function()
      local co=coroutine.create(f)
      while coroutine.status(co)~="dead" do local ok,err=coroutine.resume(co);assert(ok,err) end
    end end}
    local ok,err=pcall(function()
      out:note_on(60,100,1,1);out.panic()
      luaunit.assert_equals(writes[1],{0,{144,60,100}})
      luaunit.assert_equals(writes[2],{0,{128,0,0}})
      local count=#writes;advance(.1);luaunit.assert_equals(#writes,count)
    end)
    scheduler=old;if not ok then error(err,0) end
  end)
end
