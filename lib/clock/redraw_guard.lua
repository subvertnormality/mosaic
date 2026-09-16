-- A redraw runs native drawing that cannot be interrupted, so it must not start
-- in front of a step's notes. How long one takes varies with the page, the
-- device and Cairo itself, and a redraw that overruns a fixed guard delays the
-- whole step: traced windows show a step starting 7-8 ms late and the next
-- recovering by the same amount. Follow the slowest recent redraw instead of
-- assuming a cost, and decay back when the page is cheap again. The ceiling
-- keeps a pathological frame from starving the display.
local redraw_guard = {}

redraw_guard.FLOOR = 0.025
redraw_guard.CEILING = 0.06
redraw_guard.DECAY = 0.95

-- seconds_to_next_step returns nil when the transport is stopped or unknown,
-- which leaves the redraw unguarded; now returns monotonic seconds.
function redraw_guard.new(seconds_to_next_step, now)
  local guard = redraw_guard.FLOOR
  local self = {}

  function self.guard_seconds() return guard end

  -- Returns true when draw ran.
  function self.run(draw)
    local remaining = seconds_to_next_step()
    if remaining and remaining <= guard then return false end
    local started = now()
    draw()
    local took = now() - started
    if took > guard then
      guard = math.min(redraw_guard.CEILING, took)
    elseif guard > redraw_guard.FLOOR then
      guard = math.max(redraw_guard.FLOOR, guard * redraw_guard.DECAY)
    end
    return true
  end

  return self
end

return redraw_guard
