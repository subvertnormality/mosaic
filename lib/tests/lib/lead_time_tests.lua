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

function test_lead_time_zero_cleanup_preserves_legacy_output()
  with_midi_lead(function(out,writes,_,_,port)
    out.set_lead_time(0);out.install_clock_hooks();out:note_on(60,100,1,1)
    out.cleanup()
    luaunit.assert_equals(writes,{{0,{144,60,100}}})
    out:reset_note_counts()
  end)
end
function test_lead_time_cleanup_drains_delayed_notes_and_restores_hooks()
  with_midi_lead(function(out,writes,_,advance,port)
    local original=port.clock
    out.install_clock_hooks();port:start();out:note_on(60,100,1,1)
    out.cleanup()
    luaunit.assert_equals(writes,{{0,{250}},{0,{144,60,100}},{0,{128,60,0}},{0,{252}}})
    luaunit.assert_equals(port.clock,original)
    advance(.050);luaunit.assert_equals(#writes,4)
  end)
end

-- README Lock lead time: when two notes on one MIDI channel are closer together
-- than twice the lead, a parameter value waits until halfway between the previous
-- note-on and its own note-on. Each note then sounds with its own step's value,
-- keeps half the gap before the next value moves the receiver, and the next value
-- gets the other half to settle. Farther apart, values leave at step time.
-- Advance through every timer deadline up to limit, firing each exactly on time.
local function run_until(timers, advance, limit)
  while true do
    local next_due
    for _, t in ipairs(timers) do
      if t.due and (not next_due or t.due < next_due) then next_due = t.due end
    end
    if not next_due or next_due > limit + 1e-12 then advance(limit); return end
    advance(next_due)
  end
end
local function lead_step(out, t, advance, value, note, lead, timers)
  if timers then run_until(timers, advance, t) else advance(t) end
  out.begin_output_batch()
  out.cc(74, nil, value, 1, 1)
  out.flush_output_batch()
  out:note_on(note, 100, 1, 1, lead)
  out.flush_output_batch(true)
end
local function wire_order(writes)
  local rows = {}
  for _, w in ipairs(writes) do
    local b = w[2]
    for i = 1, #b, 3 do rows[#rows + 1] = {w[1], b[i], b[i + 1], b[i + 2]} end
  end
  return rows
end
local function near(a, b) return math.abs(a - b) < 1e-6 end

function test_lead_time_values_leave_at_step_time_when_notes_are_far_apart()
  with_midi_lead(function(out, writes, timers, advance)
    out.set_lead_time(25)
    lead_step(out, 0, advance, 10, 60, 25, timers)
    run_until(timers, advance, .025)
    lead_step(out, .115, advance, 20, 62, 25, timers)
    run_until(timers, advance, .140)
    local rows = wire_order(writes)
    luaunit.assert_equals(#rows, 4)
    luaunit.assert_equals({rows[1][2], rows[1][4]}, {176, 10}); luaunit.assert_true(near(rows[1][1], 0))
    luaunit.assert_equals({rows[2][2], rows[2][3]}, {144, 60}); luaunit.assert_true(near(rows[2][1], .025))
    luaunit.assert_equals({rows[3][2], rows[3][4]}, {176, 20}); luaunit.assert_true(near(rows[3][1], .115))
    luaunit.assert_equals({rows[4][2], rows[4][3]}, {144, 62}); luaunit.assert_true(near(rows[4][1], .140))
  end)
end

function test_lead_time_value_closer_than_the_lead_waits_for_the_gap_midpoint()
  with_midi_lead(function(out, writes, timers, advance)
    out.set_lead_time(25)
    -- 200 bpm with a x4 channel clock: steps 18.75 ms apart.
    local gap = .01875
    local values, notes = {10, 20, 30, 40}, {60, 62, 64, 65}
    for i = 1, 4 do
      local t = (i - 1) * gap
      lead_step(out, t, advance, values[i], notes[i], 25, timers)
    end
    run_until(timers, advance, 1)
    local rows = wire_order(writes)
    luaunit.assert_equals(#rows, 8)
    for i = 1, 4 do
      local lock, note = rows[2 * i - 1], rows[2 * i]
      luaunit.assert_equals({lock[2], lock[4]}, {176, values[i]}, "value " .. i)
      luaunit.assert_equals({note[2], note[3]}, {144, notes[i]}, "note " .. i)
      local t = (i - 1) * gap
      luaunit.assert_true(near(note[1], t + .025), "note " .. i .. " at " .. note[1])
      local expected = i == 1 and 0 or t + .025 - gap / 2
      luaunit.assert_true(near(lock[1], expected), "value " .. i .. " at " .. lock[1] .. " not " .. expected)
    end
  end)
end

function test_lead_time_value_between_one_and_two_leads_waits_only_to_the_midpoint()
  with_midi_lead(function(out, writes, timers, advance)
    out.set_lead_time(25)
    lead_step(out, 0, advance, 10, 60, 25, timers)
    run_until(timers, advance, .025)
    lead_step(out, .040, advance, 20, 62, 25, timers)
    run_until(timers, advance, .044); luaunit.assert_equals(#wire_order(writes), 2)
    run_until(timers, advance, .045)
    local rows = wire_order(writes)
    luaunit.assert_equals({rows[3][2], rows[3][4]}, {176, 20}); luaunit.assert_true(near(rows[3][1], .045))
    run_until(timers, advance, .065)
    rows = wire_order(writes)
    luaunit.assert_equals({rows[4][2], rows[4][3]}, {144, 62}); luaunit.assert_true(near(rows[4][1], .065))
  end)
end

function test_lead_time_held_values_keep_their_order_and_nrpn_stays_whole()
  with_midi_lead(function(out, writes, timers, advance)
    out.set_lead_time(25)
    lead_step(out, 0, advance, 10, 60, 25, timers)
    run_until(timers, advance, .010)
    out.nrpn(1, 20, 7262, 1, 1, "standard")
    out.cc(74, nil, 11, 1, 1)
    run_until(timers, advance, .011); out.cc(74, nil, 12, 1, 1)
    run_until(timers, advance, 1)
    local after_rows = nil
    local rows = wire_order(writes)
    local after = {}
    for i = 3, #rows do after[#after + 1] = {rows[i][3], rows[i][4]} end
    luaunit.assert_equals({rows[2][2], rows[2][3]}, {144, 60})
    luaunit.assert_equals(after, {{99, 1}, {98, 20}, {6, 56}, {38, 94}, {74, 11}, {74, 12}})
    for i = 4, #rows do luaunit.assert_true(rows[i][1] >= rows[i - 1][1]) end
  end)
end

function test_lead_time_other_channels_and_ports_are_not_held()
  with_midi_lead(function(out, writes, timers, advance)
    out.set_lead_time(25)
    lead_step(out, 0, advance, 10, 60, 25, timers)
    run_until(timers, advance, .005); out.cc(74, nil, 50, 2, 1)
    local rows = wire_order(writes)
    luaunit.assert_equals(#rows, 2)
    luaunit.assert_equals({rows[2][2], rows[2][4]}, {177, 50}); luaunit.assert_true(near(rows[2][1], .005))
  end)
end

function test_lead_time_stop_sends_held_values_in_order_before_releases()
  with_midi_lead(function(out, writes, timers, advance)
    out.set_lead_time(25)
    lead_step(out, 0, advance, 10, 60, 25, timers)
    lead_step(out, .010, advance, 20, 62, 25, timers)
    out.stop(false)
    local rows = wire_order(writes)
    local kinds = {}
    for _, r in ipairs(rows) do kinds[#kinds + 1] = {r[2], r[3]} end
    luaunit.assert_equals(kinds, {{176, 74}, {144, 60}, {176, 74}, {144, 62}, {128, 60}, {128, 62}})
    local count = #writes; run_until(timers, advance, 1); luaunit.assert_equals(#writes, count)
  end)
end

function test_lead_time_zero_never_holds_values_between_close_notes()
  with_midi_lead(function(out, writes, timers, advance)
    out.set_lead_time(0)
    for i = 0, 3 do lead_step(out, i * .005, advance, 10 + i, 60 + i, 0) end
    local rows = wire_order(writes)
    luaunit.assert_equals(#rows, 8)
    for i = 0, 3 do
      luaunit.assert_true(near(rows[2 * i + 1][1], i * .005)); luaunit.assert_true(near(rows[2 * i + 2][1], i * .005))
    end
    luaunit.assert_equals(#timers, 0)
  end)
end

-- A value's gap midpoint is measured from its step's pulse, like its note. A
-- stall between a pulse's releases and its locks must not push the value later.
function test_lead_time_value_midpoint_uses_the_pulse_time_after_a_stall()
  with_midi_lead(function(out, writes, timers, advance)
    out.set_lead_time(25)
    lead_step(out, 0, advance, 10, 60, 25, timers)
    run_until(timers, advance, .040)
    out.begin_output_batch()
    out:note_off(60, 100, 1, 1, 25)
    advance(.042)
    out.cc(74, nil, 20, 1, 1)
    out.flush_output_batch()
    out:note_on(62, 100, 1, 1, 25)
    out.flush_output_batch(true)
    run_until(timers, advance, 1)
    local rows = wire_order(writes)
    local value = rows[3]
    luaunit.assert_equals({value[2], value[4]}, {176, 20})
    luaunit.assert_true(near(value[1], .045), "value at " .. value[1])
    luaunit.assert_equals({rows[4][2], rows[4][3]}, {128, 60}); luaunit.assert_true(near(rows[4][1], .065))
    luaunit.assert_equals({rows[5][2], rows[5][3]}, {144, 62}); luaunit.assert_true(near(rows[5][1], .065))
  end)
end

-- A value produced after a note in the same pulse, and due at the same moment
-- (a slide value right after the previous note), follows that note.
function test_lead_time_equal_deadlines_keep_the_order_values_and_notes_were_produced()
  with_midi_lead(function(out, writes, timers, advance)
    out.set_lead_time(25)
    lead_step(out, 0, advance, 10, 60, 25, timers)
    out.begin_output_batch()
    out:note_on(62, 100, 1, 1, 25)
    out.cc(74, nil, 20, 1, 1)
    out.flush_output_batch(true)
    run_until(timers, advance, 1)
    local kinds = {}
    for _, r in ipairs(wire_order(writes)) do kinds[#kinds + 1] = {r[2], r[3], r[4]} end
    luaunit.assert_equals(kinds, {{176, 74, 10}, {144, 60, 100}, {144, 62, 100}, {176, 74, 20}})
  end)
end
