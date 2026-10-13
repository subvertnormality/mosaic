-- Paced garbage collection.
--
-- Lua's automatic collector does its work when Lua allocates, and Mosaic
-- allocates inside clock resumes. Once the heap passes the collector's pause
-- threshold, a whole cycle's marking and sweeping is paid for by the next few
-- allocations, so on the norns a dense 16-channel pattern delayed notes by up
-- to 164 ms every 20 seconds or so.
--
-- The pacer stops the automatic collector and does the work from its own timer
-- instead, in slices with a fixed CPU budget. It uses basic steps only
-- (step size 0): a sized step would also pay off all the debt accumulated
-- while automatic collection was stopped, which is the burst being avoided.
-- After a completed cycle it waits until the heap has grown by `growth`, as
-- the automatic collector's pause would, so light patterns cost little.
--
-- Two safety limits keep memory bounded if a workload outpaces the budget:
-- above `ceiling_kb` each slice gets four times the budget, and above twice
-- the ceiling the automatic collector is restarted until the heap is back
-- under the ceiling.

local gc_pacer = {}

local DEFAULTS = {
  hz = 100,
  budget_seconds = 0.001,
  growth = 1.5,
  ceiling_kb = 64 * 1024,
}

function gc_pacer.new(config)
  config = config or {}
  local collect = config.collect or collectgarbage
  local clock = config.clock or os.clock
  local timers = config.metro or metro
  local hz = config.hz or DEFAULTS.hz
  local budget = config.budget_seconds or DEFAULTS.budget_seconds
  local growth = config.growth or DEFAULTS.growth
  local ceiling = config.ceiling_kb or DEFAULTS.ceiling_kb

  local self = {}
  local timer = nil
  local threshold = 0
  local automatic = false

  local function slice(seconds)
    local start = clock()
    repeat
      if collect("step", 0) then
        threshold = collect("count") * growth
        return
      end
    until clock() - start >= seconds
  end

  function self:tick()
    local heap = collect("count")
    if automatic then
      if heap >= ceiling then return end
      collect("stop")
      automatic = false
    elseif heap > 2 * ceiling then
      collect("restart")
      automatic = true
      return
    end
    if heap < threshold and heap < ceiling then return end
    slice(heap > ceiling and budget * 4 or budget)
  end

  function self:start()
    if timer then return end
    collect("stop")
    automatic = false
    threshold = 0
    timer = timers.init(function() self:tick() end, 1 / hz, -1)
    timer:start()
  end

  function self:stop()
    if not timer then return end
    timer:stop()
    if timers.free and timer.id then timers.free(timer.id) end
    timer = nil
    automatic = false
    collect("restart")
  end

  return self
end

return gc_pacer
