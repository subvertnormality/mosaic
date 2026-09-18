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
  -- Everything waits for its own deadline. Letting a clock pulse carry delayed
  -- output instead looks steadier, because a pulse is steadier than a timer
  -- callback queued behind one, but it rounds every wait up to the next pulse:
  -- a 25 ms lead at 130 bpm is 5.2 pulses and was heard as 6, and at 200 bpm,
  -- where it is exactly 8, it was heard correctly. A lead measured in
  -- milliseconds has to be those milliseconds at every tempo, so the pulse is
  -- only a rescue for output already overdue, and the clock's own steadiness has
  -- to come from the deadline being reachable rather than from waiting for a
  -- pulse.
  local firing
  local function arm(lane)
    local first=lane.groups[lane.head]
    if first and not lane.armed then
      lane.armed=true
      lane.timer:start(math.max(0.000001,first.due-deps.now()))
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
  local function send_due()
    local now=deps.now()
    local resolution=deps.resolution or 1e-9
    while true do
      local best,first
      local function consider(lane)
        local group=lane.groups[lane.head]
        if group and group.due<=now+resolution and (not first or group.due<first.due-resolution or
            (group.due<=first.due+resolution and group.items[1].serial<first.items[1].serial)) then
          best,first=lane,group
        end
      end
      for _,lane in pairs(lanes) do consider(lane) end
      if held then consider(held) end
      if not best then break end
      -- A value held for a gap belongs before the note it leads. If that note is
      -- going out now, the value goes with it even though its own deadline has
      -- not quite arrived: a note must never be heard under the value it was
      -- meant to replace.
      while held and held.groups[held.head] and held.groups[held.head]~=first
          and held.groups[held.head].due<first.due-resolution do
        send_group(held)
      end
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
  -- A pulse is starting: send anything already overdue into its write, ahead of
  -- what the pulse itself produces, which is always due later than now. This is
  -- the rescue for a deadline that has passed unserved, never the way output is
  -- meant to leave: waiting for a pulse is what rounded the lead up to one.
  function q:begin()
    if firing then pulse=true;pulse_time=nil;return end
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
      group={due=(pulse_time or deps.now())+ms/1000,items={}}
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
