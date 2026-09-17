-- Output-only delay: callers have already made every musical decision.
-- A lane owns one reusable timer per lead, and a FIFO of pulse groups. Timers
-- and clock coroutines run on matron's Lua thread; neither interrupts a pulse.
local delay_line = {}

function delay_line.timer(callback)
  local m = metro and metro.init(callback)
  if m then
    return {
      start=function(_,seconds) m:start(seconds,1) end,
      stop=function() m:stop() end,
      free=function() metro.free(m.id) end
    }
  end
  local thread
  local function stop()
    if thread then clock.cancel(thread);thread=nil end
  end
  return {
    start=function(_,seconds)
      stop()
      thread=clock.run(function() clock.sleep(seconds);thread=nil;callback() end)
    end,
    stop=stop, free=stop
  }
end

function delay_line.new(deps)
  local q = {}
  local lanes, pulse, pulse_time, serial = {}, false, nil, 0
  -- While the transport runs, a delayed message leaves on a clock pulse, a
  -- counted number of pulses after the pulse that produced it. A timer callback
  -- waits behind whatever pulse is running, and on a busy step that wait moved
  -- delayed notes several milliseconds off the beat; comparing the deadline
  -- against the clock instead moved them a whole pulse whenever the pulse ran
  -- either side of it. Counting pulses gives a delayed note the same steadiness
  -- as an undelayed one: both leave on a pulse, a fixed number of pulses apart.
  -- The lead is rounded up to whole pulses, so it is never shorter than asked.
  -- The timer stays as the fallback for output produced while no pulse is
  -- coming (MIDI thru with the transport stopped), and is armed late while
  -- pulses are arriving so the pulse itself normally sends first.
  local last_pulse, pulse_interval, firing, pulse_count = nil, nil, nil, 0
  local function pulsing(now)
    return pulse_interval and last_pulse and (now-last_pulse) < pulse_interval*4
  end
  local function arm(lane)
    local first=lane.groups[lane.head]
    if first and not lane.armed then
      lane.armed=true
      local now=deps.now()
      local wait=first.due-now
      -- A group counting pulses is normally sent by its pulse, so its timer is
      -- only the fallback for pulses that stop; a group waiting on a deadline
      -- (a value held for the gap) keeps its exact timer.
      if first.pulse_due and pulsing(now) then wait=wait+pulse_interval*1.5 end
      lane.timer:start(math.max(0.000001,wait))
    end
  end
  -- Parameter values held for a gap (push_at) have their own lane ordered by
  -- deadline. Whichever timer fires sends every due group from every lane, in
  -- deadline order and, for equal deadlines, in the order they were produced: a
  -- lock produced before its note precedes it, a slide value produced after a
  -- note follows it, even when separate timers hold them.
  local held
  local function send_group(lane)
    for _,item in ipairs(lane.groups[lane.head].items) do deps.send(item.message) end
    lane.head=lane.head+1
  end
  local function settle(lane)
    if lane.head>#lane.groups then
      lane.groups={};lane.head=1
    elseif lane.head>64 then
      -- Sustained streams with leads longer than a pulse never empty. Release
      -- consumed groups instead of retaining the whole performance in memory.
      local remaining={}
      for i=lane.head,#lane.groups do remaining[#remaining+1]=lane.groups[i] end
      lane.groups=remaining;lane.head=1
    end
    if lane.armed and not lane.groups[lane.head] then lane.timer:stop();lane.armed=false end
    arm(lane)
  end
  -- A group counting pulses waits for its pulse, however the clock has drifted
  -- against it; a group without one waits for its deadline.
  local function ready(group,now,resolution)
    -- While the clock still pulses, a counted group waits for its pulse. If the
    -- pulses stop (the transport stopped, or an external clock went quiet) its
    -- deadline releases it, so nothing is ever stranded.
    if group.pulse_due and pulsing(now) then return pulse_count>=group.pulse_due end
    return group.due<=now+resolution
  end
  local function send_due()
    local now=deps.now()
    local resolution=deps.resolution or 1e-9
    while true do
      local best,first
      local function consider(lane)
        local group=lane.groups[lane.head]
        if group and ready(group,now,resolution) and (not first or group.due<first.due-resolution or
            (group.due<=first.due+resolution and group.items[1].serial<first.items[1].serial)) then
          best,first=lane,group
        end
      end
      for _,lane in pairs(lanes) do consider(lane) end
      if held then consider(held) end
      if not best then break end
      send_group(best)
    end
  end
  local function settle_all()
    for _,lane in pairs(lanes) do settle(lane) end
    if held then settle(held) end
  end
  local function fire(fired)
    fired.armed=false
    -- Opening a batch calls back into begin(), which sends what is due; the
    -- flag keeps that callback from being counted as a clock pulse.
    firing=true
    deps.begin()
    send_due()
    deps.flush()
    settle_all()
    firing=false
  end
  function q:now() return deps.now() end
  -- The pulse a message anchored at this moment and delayed by ms leaves on,
  -- and when that pulse falls. Everything delayed rides the same grid, whether
  -- it was produced inside a pulse (a step's notes) or between pulses (MIDI
  -- clock ticks), so a lead never moves one against another.
  local function schedule(anchor,ms)
    local wait=ms/1000
    local now=deps.now()
    if not (pulse_interval and last_pulse and pulsing(now)) then return anchor+wait,nil end
    -- Count from the pulse itself, not from the moment inside it when the
    -- message happened to be made: a lead of exactly so many pulses must not
    -- become one more because the step spent a moment working first.
    local base=pulse and last_pulse or now
    local pulses=math.ceil((base+wait-last_pulse)/pulse_interval-1e-9)
    if pulses<1 then pulses=1 end
    return last_pulse+pulses*pulse_interval,pulse_count+pulses
  end
  -- When a message pushed now with this lead would leave: the pulse the note
  -- itself will wait for, so a value's gap is measured against the moment its
  -- note is really heard.
  function q:deadline(ms)
    local due=schedule(self:time(),ms)
    return due
  end
  -- The time a pulse's delayed output is measured from: its first delayed
  -- message, or now outside a pulse. Values and notes of one step share it.
  function q:time()
    if pulse then
      if not pulse_time then pulse_time=deps.now() end
      return pulse_time
    end
    return deps.now()
  end
  -- Send a message at an absolute deadline on this line's clock. Deadlines may
  -- arrive out of order across channels; equal deadlines keep push order.
  function q:push_at(due,message)
    if not held then
      held={groups={},head=1}
      held.timer=(deps.timer or delay_line.timer)(function() fire(held) end)
    end
    local groups=held.groups
    local index=#groups+1
    while index>held.head and groups[index-1].due>due do index=index-1 end
    serial=serial+1
    table.insert(groups,index,{due=due,items={{message=message,serial=serial}}})
    if index==held.head and held.armed then held.timer:stop();held.armed=false end
    arm(held)
  end
  -- A pulse is starting: send what has come due into its write, ahead of
  -- anything the pulse itself produces (everything the pulse produces is due
  -- later than now). A delayed note then leaves on the pulse grid, as steady as
  -- an undelayed one, instead of on a timer callback queued behind a busy step.
  function q:begin()
    if firing then pulse=true;pulse_time=nil;return end
    local now=deps.now()
    -- The clock states its own pulse spacing. Measuring it instead would read a
    -- run of catch-up pulses as a much finer grid than the clock really has.
    local stated=deps.interval and deps.interval()
    if type(stated)=="number" and stated>0.0001 and stated<0.25 then pulse_interval=stated end
    last_pulse=now
    pulse_count=pulse_count+1
    pulse=true;pulse_time=nil
    send_due()
    settle_all()
  end
  function q:finish()
    pulse=false;pulse_time=nil
    for _,lane in pairs(lanes) do lane.pulse_group=nil;arm(lane) end
  end
  function q:push(ms,message)
    if not ms or ms==0 then deps.send(message);return end
    local lane=lanes[ms]
    if not lane then
      lane={groups={},head=1}
      lane.timer=(deps.timer or delay_line.timer)(function() fire(lane) end)
      lanes[ms]=lane
    end
    local group=pulse and lane.pulse_group
    if not group then
      if pulse and not pulse_time then pulse_time=deps.now() end
      local due,pulse_due=schedule(pulse_time or deps.now(),ms)
      group={due=due,pulse_due=pulse_due,items={}}
      lane.groups[#lane.groups+1]=group
      if pulse then lane.pulse_group=group end
    end
    serial=serial+1
    group.items[#group.items+1]={message=message,serial=serial}
    if not pulse then arm(lane) end
    return group.due
  end
  function q:drain()
    local pending={}
    local function take(lane)
      lane.timer:stop();lane.armed=false
      for i=lane.head,#lane.groups do
        for _,item in ipairs(lane.groups[i].items) do pending[#pending+1]=item end
      end
      lane.groups={};lane.head=1;lane.pulse_group=nil
    end
    for _,lane in pairs(lanes) do take(lane) end
    if held then take(held) end
    table.sort(pending,function(a,b) return a.serial<b.serial end)
    if #pending>0 then
      deps.begin()
      for _,item in ipairs(pending) do deps.send(item.message) end
      deps.flush()
    end
  end
  function q:close()
    self:drain()
    for _,lane in pairs(lanes) do lane.timer:free() end
    if held then held.timer:free();held=nil end
    lanes={}
  end
  return q
end
return delay_line
