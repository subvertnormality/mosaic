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
  local function arm(lane)
    local first=lane.groups[lane.head]
    if first and not lane.armed then
      lane.armed=true
      lane.timer:start(math.max(0.000001,first.due-deps.now()))
    end
  end
  local function fire(lane)
    lane.armed=false
    local now=deps.now()
    deps.begin()
    while lane.head<=#lane.groups and lane.groups[lane.head].due<=now+(deps.resolution or 1e-9) do
      local group=lane.groups[lane.head]
      for _,item in ipairs(group.items) do deps.send(item.message) end
      lane.head=lane.head+1
    end
    deps.flush()
    if lane.head>#lane.groups then
      lane.groups={};lane.head=1
    elseif lane.head>64 then
      -- Sustained streams with leads longer than a pulse never empty. Release
      -- consumed groups instead of retaining the whole performance in memory.
      local remaining={}
      for i=lane.head,#lane.groups do remaining[#remaining+1]=lane.groups[i] end
      lane.groups=remaining;lane.head=1
    end
    arm(lane)
  end
  function q:begin() pulse=true;pulse_time=nil end
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
  end
  function q:drain()
    local pending={}
    for _,lane in pairs(lanes) do
      lane.timer:stop();lane.armed=false
      for i=lane.head,#lane.groups do
        for _,item in ipairs(lane.groups[i].items) do pending[#pending+1]=item end
      end
      lane.groups={};lane.head=1;lane.pulse_group=nil
    end
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
    lanes={}
  end
  return q
end
return delay_line
