---- module for creating a lattice of sprockets based on a single fast "superclock"
--
-- @module Lattice
-- @release v2.0
-- @author tyleretters & ezra & zack & rylee
local Lattice, Sprocket = {}, {}

local fn = include("mosaic/lib/functions")


local drunk_map = {
  {2/9, 3/9, 2/9, 2/9, 2/9, 3/9, 2/9, 2/9},
  {2/7, 2/7, 2/7, 1/7, 2/7, 2/7, 2/7, 1/7},
  {1/5, 2/5, 1/5, 1/5, 1/5, 2/5, 1/5, 1/5},
  {1/6, 3/6, 1/6, 1/6, 1/6, 3/6, 1/6, 1/6},
  {1/8, 4/8, 2/8, 1/8, 1/8, 4/8, 2/8, 1/8},
  {1/9, 5/9, 2/9, 1/9, 1/9, 5/9, 2/9, 1/9},
}

local smooth_map = {
  {5/18, 5/18, 4/18, 4/18, 5/18, 5/18, 4/18, 4/18},
  {4/14, 4/14, 3/14, 3/14, 4/14, 4/14, 3/14, 3/14},
  {3/10, 3/10, 2/10, 2/10, 3/10, 3/10, 2/10, 2/10},
  {2/6, 2/6, 1/6, 1/6, 2/6, 2/6, 1/6, 1/6},
  {5/16, 5/16, 3/16, 3/16, 5/16, 5/16, 3/16, 3/16},
  {6/18, 7/18, 3/18, 2/18, 6/18, 7/18, 3/18, 2/18},
}

local heavy_map = {
  {4/9, 2/9, 2/9, 1/9, 4/9, 2/9, 2/9, 1/9},
  {3/7, 1/7, 2/7, 1/7, 3/7, 1/7, 2/7, 1/7},
  {2/5, 1/5, 1/5, 1/5, 2/5, 1/5, 1/5, 1/5},
  {3/6, 1/6, 1/6, 1/6, 3/6, 1/6, 1/6, 1/6},
  {4/8, 1/8, 2/8, 1/8, 4/8, 1/8, 2/8, 1/8},
  {5/9, 1/9, 2/9, 1/9, 5/9, 1/9, 2/9, 1/9},
}

local clave_map = {
  {2/9, 3/9, 2/9, 2/9, 3/9, 2/9, 2/9, 2/9},
  {2/7, 2/7, 1/7, 2/7, 2/7, 1/7, 2/7, 2/7},
  {1/5, 2/5, 1/5, 1/5, 2/5, 1/5, 1/5, 1/5},
  {3/12, 4/12, 2/12, 3/12, 4/12, 2/12, 3/12, 3/12},
  {3/16, 6/16, 3/16, 4/16, 5/16, 3/16, 4/16, 4/16},
  {4/18, 7/18, 3/18, 4/18, 7/18, 2/18, 5/18, 4/18},
}

local shuffle_feels = {
  drunk_map,
  smooth_map,
  heavy_map,
  clave_map
}


--- instantiate a new lattice
-- @tparam[opt] table args optional named attributes are:
-- - "auto" (boolean) turn off "auto" pulses from the norns clock, defaults to true
-- - "ppqn" (number) the number of pulses per quarter cycle of this superclock, defaults to 96
-- @treturn table a new lattice
function Lattice:new(args)
  local l = setmetatable({}, { __index = Lattice })
  args = args == nil and {} or args
  l.auto = args.auto == nil and true or args.auto
  l.ppqn = args.ppqn == nil and 96 or args.ppqn
  l.enabled = false
  l.transport = 0
  l.superclock_id = nil
  l.sprocket_id_counter = 100
  l.sprockets = {}
  l.sprocket_ordering = {{}, {}, {}, {}, {}}
  return l
end

--- start running the lattice
function Lattice:start()
  self.enabled = true
  if self.auto and self.superclock_id == nil then
    self.superclock_id = clock.run(self.auto_pulse, self)
  end
end

--- reset the norns clock without restarting lattice
function Lattice:reset()
  -- destroy clock, but not the sprockets
  self:stop()
  if self.superclock_id ~= nil then
    clock.cancel(self.superclock_id)
    self.superclock_id = nil
  end
  for i, sprocket in pairs(self.sprockets) do
    sprocket.phase = sprocket.division * self.ppqn * 4 * (1 - sprocket.delay) -- "4" because in music a "quarter note" == "1/4"
  end
  self.transport = 0
  params:set("clock_reset", 1)
end

--- reset the norns clock and restart lattice
function Lattice:hard_restart()
  self:reset()
  self:start()
end

--- stop the lattice
function Lattice:stop()
  self.enabled = false
end

--- toggle the lattice
function Lattice:toggle()
  self.enabled = not self.enabled
end

--- destroy the lattice
function Lattice:destroy()
  self:stop()
  if self.superclock_id ~= nil then
    clock.cancel(self.superclock_id)
  end
  self.sprockets = {}
  self.sprocket_ordering = {}
end

--- set_meter is deprecated
function Lattice:set_meter(_)
  print("meter is deprecated")
end


--- use the norns clock to pulse
-- @tparam table s this lattice
function Lattice.auto_pulse(s)
  while true do
    s:pulse()
    clock.sync(1/s.ppqn)
  end
end


function Lattice:pulse()
  if self.enabled then
    local ppc = self.ppqn * 4 -- pulses per cycle
    local flagged = false
    for i = 1, 5 do
      for _, id in ipairs(self.sprocket_ordering[i]) do
        local sprocket = self.sprockets[id]
        sprocket.step = sprocket.step or 1
        if sprocket.enabled then

          if sprocket.shuffle_feel > 0 then
            sprocket:update_shuffle_feel(shuffle_feels[sprocket.shuffle_feel], self.transport)
          end

          local swing_val = (sprocket.step % 2 == 0) and (sprocket.even_swing) or (sprocket.odd_swing)


          sprocket.phase = sprocket.phase + 1

          if sprocket.phase > sprocket.division * ppc * swing_val then
            sprocket.phase = sprocket.phase - (sprocket.division * ppc)
            if sprocket.delay_new ~= nil then
              sprocket.phase = sprocket.phase - (sprocket.division * ppc) * (1 - (sprocket.delay - sprocket.delay_new))
              sprocket.delay = sprocket.delay_new
              sprocket.delay_new = nil
            end
            sprocket.step = sprocket.step + 1
            sprocket.action(self.transport)
          end
        elseif sprocket.flag then
          self.sprockets[sprocket.id] = nil
          flagged = true
        end
      end
    end
    if flagged then
      self:order_sprockets()
    end
    self.transport = self.transport + 1
  end
end


--- factory method to add a new sprocket to this lattice
-- @tparam[opt] table args optional named attributes are:
-- - "action" (function) called on each step of this division (lattice.transport is passed as the argument), defaults to a no-op
-- - "division" (number) the division of the sprocket, defaults to 1/4
-- - "enabled" (boolean) is this sprocket enabled, defaults to true
-- - "delay" (number) specifies amount of delay, as fraction of division (0.0 - 1.0), defaults to 0
-- - "swing" (number) specifies amount of swing, as percentage of division (-50 - 50), defaults to 0
-- - "order" (number) specifies the place in line this lattice occupies from 1 to 5, lower first, defaults to 3
-- @treturn table a new sprocket
function Lattice:new_sprocket(args)
  self.sprocket_id_counter = self.sprocket_id_counter + 1
  args = args == nil and {} or args
  args.id = self.sprocket_id_counter
  args.order = args.order == nil and 3 or util.clamp(args.order, 1, 5)
  args.action = args.action == nil and function(t) return end or args.action
  args.division = args.division == nil and 1/4 or args.division
  args.enabled = args.enabled == nil and true or args.enabled
  args.phase = args.division * self.ppqn * 4 -- "4" because in music a "quarter note" == "1/4"
  args.delay = args.delay == nil and 0 or util.clamp(args.delay,0,1)
  args.swing = args.swing == nil and 0 or util.clamp(args.swing,-50,50)
  args.shuffle_basis = args.shuffle_basis or 0
  args.shuffle_feel = args.shuffle_feel or 0
  
  args.ppqn = self.ppqn or 96
  local sprocket = Sprocket:new(args)
  sprocket:update_swing()
  self.sprockets[self.sprocket_id_counter] = sprocket
  self:order_sprockets()
  return sprocket
end

--- new_pattern is deprecated
function Lattice:new_pattern(args)
  print("'new_pattern' is deprecated; use 'new_sprocket' instead.")
  return self:new_sprocket(args)
end

--- "private" method to keep numerical order of the sprocket ids
-- for use when pulsing
function Lattice:order_sprockets()
  self.sprocket_ordering = {{}, {}, {}, {}, {}}
  for id, sprocket in pairs(self.sprockets) do
    table.insert(self.sprocket_ordering[sprocket.order],id)
  end
  for i = 1, 5 do
    table.sort(self.sprocket_ordering[i])
  end
end

--- "private" method to instantiate a new sprocket, only called by Lattice:new_sprocket()
-- @treturn table a new sprocket
function Sprocket:new(args)
  local p = setmetatable({}, { __index = Sprocket })
  p.id = args.id
  p.order = args.order
  p.division = args.division
  p.action = args.action
  p.enabled = args.enabled
  p.flag = false
  p.swing = args.swing
  p.delay = args.delay
  p.phase = args.phase * (1-args.delay)
  p.ppqn = args.ppqn or 96
  p.swing_mode = args.swing_mode or "simple"
  p.shuffle_basis = args.shuffle_basis
  p.shuffle_feel = args.shuffle_feel
  return p
end

--- start the sprocket
function Sprocket:start()
  self.enabled = true
end

--- stop the sprocket
function Sprocket:stop()
  self.enabled = false
end

--- toggle the sprocket
function Sprocket:toggle()
  self.enabled = not self.enabled
end

--- flag the sprocket to be destroyed
function Sprocket:destroy()
  self.enabled = false
  self.flag = true
end

--- set the division of the sprocket
-- @tparam number n the division of the sprocket
function Sprocket:set_division(n)
   self.division = n
end

--- set the action for this sprocket
-- @tparam function the action
function Sprocket:set_action(fn)
  self.action = fn
end

--- set the delay for this sprocket
-- @tparam fraction of the time between beats to delay (0-1)
function Sprocket:set_delay(delay)
  self.delay_new = util.clamp(delay,0,1)
end

function Sprocket:set_swing(swing)
  -- swing is expected to be a value between 0 (no swing) and 100 (maximum swing)
  self.swing = util.clamp(swing or 0, -100, 100)
  self:update_swing()
end

local function convert_basis_to_swing(basis_fraction)
  -- Convert basis fraction (like 5/9 for a 9-tuplet feel) to a swing value between 0 and 1
  local base_swing = ((basis_fraction - 0.5) * 2) 
  return util.clamp(base_swing, 0, 1) -- Ensure it stays within the valid range
end

-- Update basis_to_swing_amt to use your swing model values
local basis_to_swing_amt = {
  0, -- No swing (straight)
  convert_basis_to_swing(5/9),  -- Swing for 9-tuplets
  convert_basis_to_swing(4/7),  -- Swing for 7-tuplets
  convert_basis_to_swing(3/5),  -- Swing for 5-tuplets
  convert_basis_to_swing(4/6),  -- Swing for 6-tuplets
  convert_basis_to_swing(5/8),  -- Swing for "Weird 8s"
  convert_basis_to_swing(6/9),  -- Swing for "Weird 9s"
}


function Sprocket:update_swing()
  local swing_factor = self.swing / 100

  if self.shuffle_basis > 0 and self.shuffle_basis < 8 then 
    swing_factor = basis_to_swing_amt[self.shuffle_basis]
  end


  self.even_swing = 1 + swing_factor
  self.odd_swing = 1 - swing_factor


end

function Sprocket:update_shuffle_feel(feel_map, transport)
  local swing_factor = self.swing / 100

  -- Determine if we are on an "even" or "odd" beat
  local transport_mod = (transport % 8) + 1

  if feel_map and self.shuffle_basis > 0 and self.shuffle_basis < 8 then
    -- Select the correct row in the shuffle map based on the swing factor
    local map_entry = feel_map[self.shuffle_basis]

    -- Apply shuffle feel based on even/odd transport
      self.even_swing = 1 + map_entry[transport_mod]
      self.odd_swing = 1 - map_entry[transport_mod]

  else
    -- Reset swing values if no map entry found
    self.even_swing = 1
    self.odd_swing = 1
  end
end

return Lattice