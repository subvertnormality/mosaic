-- Coordinate a lattice with the native MIDI clock output transaction.
-- Coincident pulses have one owner: the after-F8 callback. Intermediate pulses
-- use scheduler deadlines and may never run ahead of that output boundary.
local transport = {}
function transport.available()
  return clock.midi and type(clock.midi.subscribe_output)=="function"
end
function transport.start(lattice, on_start)
  assert(transport.available(), "native MIDI output boundary unavailable")
  local active, started = true, false
  local subscription, intermediate
  local origin, epoch, last_boundary
  local next_pulse = 0
  local generation = 0
  lattice.auto = false
  local function through(due)
    while active and next_pulse <= due do
      lattice:pulse()
      next_pulse = next_pulse + 1
    end
  end
  local function start_intermediate()
    generation = generation + 1
    local mine = generation
    if intermediate then clock.cancel(intermediate) end
    intermediate = clock.run(function()
      while active and mine == generation do
        local _, deadline, resumed_epoch = clock.sync(1/lattice.ppqn)
        if active and mine == generation and resumed_epoch == epoch then
          local due = math.floor((deadline-origin)*lattice.ppqn+1e-9)
          -- Never emit the next coincident pulse before its outgoing F8.
          through(math.min(due,last_boundary+lattice.ppqn/24-1))
        end
      end
    end)
  end
  subscription = clock.midi.subscribe_output({
    before = function()
      if active and not started then on_start() end
    end,
    after = function(deadline, current_epoch)
      if not active then return end
      local changed = epoch ~= current_epoch
      if not started then
        origin, epoch, last_boundary = deadline, current_epoch, 0
        started = true
        lattice:start()
      elseif changed then
        -- Preserve receiver pulse count across a native source epoch change.
        last_boundary = last_boundary + lattice.ppqn/24
        origin = deadline-last_boundary/lattice.ppqn
        epoch = current_epoch
      else
        last_boundary = math.floor((deadline-origin)*lattice.ppqn+1e-9)
      end
      through(last_boundary)
      if changed then start_intermediate() end
    end
  })
  return function()
    if not active then return end
    active = false
    generation = generation + 1
    clock.midi.cancel_output(subscription)
    if intermediate then clock.cancel(intermediate);intermediate=nil end
  end
end
return transport
