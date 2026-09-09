-- Arithmetic on rational step fractions can land infinitesimally above an
-- integer pulse. Normalize only floating-point residue, never musical offsets.
local function normalize_integer(value, epsilon)
  local nearest = math.floor(value + 0.5)
  if math.abs(value - nearest) <= epsilon then return nearest end
  return value
end

local function pending_deadline(period, length)
  return normalize_integer(period * length, 1e-9)
end

-- @module Mosaic Lattice++
-- @release v2.1
-- @author byzero
-- @lattice_by tyleretters & ezra & zack & robbie
-- @shuffle_by 21echoes and sixolet https://github.com/21echoes/cyrene

local Lattice, Sprocket = {}, {}




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
  l.step = 1
  l.enabled = false
  l.transport = 1
  l.superclock_id = nil
  l.sprocket_id_counter = 100
  l.sprockets = {}
  l.sprocket_ordering = {{}, {}, {}, {}, {}}
  l.pattern_length = args.pattern_length or 64
  return l
end

function Lattice:set_pattern_length(pattern_length) 
  self.pattern_length = pattern_length
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
    -- sprocket.phase = sprocket.division * self.ppqn * 4 * (1 - sprocket.delay) -- "4" because in music a "quarter note" == "1/4"
    sprocket.phase = 1 - (sprocket.current_ppqn * (sprocket.delay - sprocket.delay_new))
  end



  self.transport = 1
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
  self.start_synced_actioned = false
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

function Lattice:get_ppqn()
  return self.ppqn
end

--- use the norns clock to pulse
-- @tparam table s this lattice
function Lattice.auto_pulse(s)
  local interval = 1 / s.ppqn
  -- Preserve the immediate first pulse, then keep full intervals from its phase.
  -- A negative equivalent offset avoids skipping a pulse at a sync boundary.
  local offset = (clock.get_beats() % interval) - interval
  while true do
    s:pulse()
    clock.sync(interval, offset)
  end
end


function Lattice:pulse()
  if self.enabled then
    local flagged = false
    for i = 1, 5 do
      for _, id in ipairs(self.sprocket_ordering[i]) do
        if not self.enabled then return end
        local sprocket = self.sprockets[id]
        if sprocket and sprocket.enabled then
          if not sprocket.shuffle_updated then
            sprocket:begin_cycle()
          end
          sprocket:prepare_pending_clocks()
          if sprocket._pending_clocks then
            for _, pending_id in ipairs(sprocket.delayed_action_order) do
              local pending = sprocket.delayed_actions[pending_id]
              local timing = pending and pending.timing
              if timing and pending.before_onset and (pending.length == 0 or
                  (pending.length < 1 and timing.phase - 1 >= pending_deadline(timing.current_ppqn, pending.length))) then
                sprocket.delayed_actions[pending_id] = nil
                sprocket:run_pending_action(pending)
                if not self.enabled then return end
                if sprocket.cleanup_delayed_action then sprocket.cleanup_delayed_action(pending_id) end
              end
            end
          end
          if sprocket.phase >= 1 and sprocket.phase < 2 then
            -- Finish due note releases before a new step can retrigger
            -- the same MIDI pitch. A late previous note-off cuts the new voice.
            -- New zero-delay actions created by this onset still run below.
            for index = 1, #sprocket.delayed_action_order do
              local pending_id = sprocket.delayed_action_order[index]
              local pending = sprocket.delayed_actions[pending_id]
              if pending and pending.before_onset and pending.length == 0 then
                sprocket.delayed_actions[pending_id] = nil
                sprocket:run_pending_action(pending)
                if not self.enabled then return end
                if sprocket.cleanup_delayed_action then
                  sprocket.cleanup_delayed_action(pending_id)
                end
              end
            end
            sprocket.onset_count = (sprocket.onset_count or 0) + 1
            sprocket.last_onset_transport = self.transport
            sprocket.action(self.transport)
            if not self.enabled then return end
          end

          sprocket.phase = sprocket.phase + 1
          if sprocket._pending_clocks then
            for _, timing in ipairs(sprocket._pending_clocks) do timing.phase = timing.phase + 1 end
          end

          local to_remove = {}
    
          -- Equal-deadline actions retain insertion order across Lua processes.
          local pending_ids = sprocket.delayed_action_order
          for index = 1, #pending_ids do
            local id = pending_ids[index]
            local delayed_action = sprocket.delayed_actions[id]
            if delayed_action then
              local timing = delayed_action.timing or sprocket
              if delayed_action.length == 0 then
                  sprocket:run_pending_action(delayed_action)
                  if not self.enabled then return end
                  table.insert(to_remove, id)
                  if sprocket.cleanup_delayed_action then
                    sprocket.cleanup_delayed_action(id)
                  end
              elseif delayed_action.length < 1 then
                  -- Phase is1 at onset and was incremented above: elapsed ticks = phase-2.
                  if timing.phase - 2 >= pending_deadline(timing.current_ppqn, delayed_action.length) then
                      sprocket:run_pending_action(delayed_action)
                      if not self.enabled then return end
                      table.insert(to_remove, id)
                      if sprocket.cleanup_delayed_action then
                        sprocket.cleanup_delayed_action(id)
                      end
                  elseif timing.phase > timing.current_ppqn then
                      -- Fractions rounding to a full cycle fire at its next onset.
                      delayed_action.length = 0
                  end
              elseif timing.phase > timing.current_ppqn then
                  delayed_action.length = delayed_action.length - 1
              end
            end
          end
          
          for _, id in ipairs(to_remove) do
              sprocket.delayed_actions[id] = nil
          end
          -- Compact cancelled/completed entries without sorting or shifting.
          local retained = 0
          for index = 1, #pending_ids do
            local id = pending_ids[index]
            if sprocket.delayed_actions[id] then
              retained = retained + 1
              pending_ids[retained] = id
            end
          end
          for index = #pending_ids, retained + 1, -1 do pending_ids[index] = nil end

          if sprocket._pending_clocks then
            for _, timing in ipairs(sprocket._pending_clocks) do
              timing:finish_cycle()
              timing.transport = timing.transport + 1
            end
          end
          sprocket:finish_cycle()
          sprocket.last_processed_transport = self.transport
          sprocket.transport = sprocket.transport + 1
        elseif sprocket and sprocket.flag then
          self.sprockets[sprocket.id] = nil
          flagged = true
        end
      end
    end
    if flagged then
      self:order_sprockets()
    end
    self.transport = self.transport + 1
    if self.transport % (self.ppqn / 4) == 0 then
      self.step = self.step + 1
    end
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
  args.ppqn = self.ppqn
  args.division = args.division == nil and 1/4 or math.max(args.division, 1 / (self.ppqn * 4))
  args.enabled = args.enabled == nil and true or args.enabled
  args.phase = 1
  args.delay = args.delay == nil and 0 or util.clamp(args.delay,0,1)
  args.swing = args.swing == nil and 0 or util.clamp(args.swing,-50,50)
  args.swing_or_shuffle = args.swing_or_shuffle == nil and 1 or util.clamp(args.swing_or_shuffle,1,2)
  args.shuffle_basis = args.shuffle_basis and util.clamp(args.shuffle_basis, 1, 6) or 0
  args.shuffle_feel = args.shuffle_feel and util.clamp(args.shuffle_feel, 1, 4) or 0
  args.shuffle_amount = args.shuffle_amount and util.clamp(args.shuffle_amount, 0, 100) or 0
  args.step = 1
  args.lattice = self
  args.realign = args.realign or false
  args.delayed_actions = {}
  args.cleanup_delayed_action = args.cleanup_delayed_action or nil
  local sprocket = Sprocket:new(args)
  sprocket:update_swing()
  sprocket:update_shuffle(1, 1)
  sprocket.phase = (args.phase) - ((sprocket.current_ppqn) * (args.delay)) - (args.delay_offset or 0)
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
  p.phase = args.phase or 1
  p.ppqn = args.ppqn
  p.swing_or_shuffle = args.swing_or_shuffle
  p.shuffle_basis = util.clamp(args.shuffle_basis, 1, 6)
  p.shuffle_feel = util.clamp(args.shuffle_feel, 1, 4)
  p.shuffle_amount = (args.shuffle_amount == nil) and 1.0 or util.clamp(args.shuffle_amount, 0, 100) / 100
  p.current_ppqn = args.ppqn
  p.ppqn_error = 0.5
  p.step = 1
  p.transport = 1
  p.lattice = args.lattice
  p.realign = args.realign
  p.delayed_actions = args.delayed_actions
  p.delayed_action_order = {}
  p.cleanup_delayed_action = args.cleanup_delayed_action
  p.division_for_cycle = args.division_for_cycle
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

function Sprocket:get_step()
  return self.step
end

--- set the division of the sprocket
-- @tparam number n the division of the sprocket
function Sprocket:set_division(n)
  self:forward_pending_setting("set_division", n)
  if self.division == n then return end
  local old_ppqn = self.current_ppqn
  local old_phase = self.phase

  self.division = n
  self:update_swing()
  self:update_shuffle(self.step)

  -- Adjust phase proportionally
  if self.current_ppqn ~= old_ppqn then
    local cycle_progress = (old_phase - 1) / old_ppqn
    local new_phase = cycle_progress * self.current_ppqn + 1
    self.phase = math.max(1, math.min(self.current_ppqn, math.floor(new_phase + 0.5)))
  end
end

--- set the action for this sprocket
-- @tparam function the action
function Sprocket:set_action(fn)
  self.action = fn
end

function Sprocket:set_delayed_action(length, action, before_onset)
  length = normalize_integer(length, 1e-12)
  local id = fn.generate_id()
  local timing = self._executing_pending_action and self._executing_pending_action.timing
  self.delayed_actions[id] = {length = length, action = action, before_onset = before_onset, timing = timing}
  table.insert(self.delayed_action_order, id)
  return id
end

--- set the delay for this sprocket
-- @tparam fraction of the time between beats to delay (0-1)
function Sprocket:set_delay(delay)
  self:forward_pending_setting("set_delay", delay)
  self.delay_new = util.clamp(delay,0,1)
end

function Sprocket:set_swing_or_shuffle(swing_or_shuffle)
  self:forward_pending_setting("set_swing_or_shuffle", swing_or_shuffle)
  local value = util.clamp(swing_or_shuffle, 1, 2)
  if self.swing_or_shuffle == value then return end
  self.swing_or_shuffle = value
  self:update_swing()
  self:update_shuffle(self.step)
end

function Sprocket:set_swing(swing)
  self:forward_pending_setting("set_swing", swing)
  -- swing is expected to be a value between 0 (no swing) and 100 (maximum swing)
  self.swing = util.clamp(swing or 0, -50, 50)
  self:update_swing()
end

function Sprocket:set_shuffle_amount(shuffle_amount)
  self:forward_pending_setting("set_shuffle_amount", shuffle_amount)
  self.shuffle_amount = util.clamp(shuffle_amount, 0, 100) / 100
end

function Sprocket:set_shuffle_basis(basis)
  self:forward_pending_setting("set_shuffle_basis", basis)
  local value = util.clamp(basis, 1, 6)
  if self.shuffle_basis == value then return end
  self.shuffle_basis = value
  -- Store inactive shuffle preferences without consuming Swing rounding phase.
  if self.swing_or_shuffle == 2 then self:update_shuffle(self.step) end
end

function Sprocket:set_shuffle_feel(feel)
  self:forward_pending_setting("set_shuffle_feel", feel)
  local value = util.clamp(feel, 1, 4)
  if self.shuffle_feel == value then return end
  self.shuffle_feel = value
  -- Store inactive shuffle preferences without consuming Swing rounding phase.
  if self.swing_or_shuffle == 2 then self:update_shuffle(self.step) end
end

function Sprocket:update_swing()
  local swing_factor = math.abs(self.swing) / 100
  if self.swing >= 0 then
    self.even_swing = 1 + swing_factor
    self.odd_swing = 1 - swing_factor
  else
    self.even_swing = 1 - swing_factor
    self.odd_swing = 1 + swing_factor
  end
end

function Sprocket:calculate_shuffle_ppqn(step)
  local ppc = self.ppqn * 4
  local pattern_length = self.lattice.pattern_length
  local step_mod = ((step - 1) % pattern_length) + 1
  
  if self.swing_or_shuffle == 2 and self.shuffle_feel > 0 and self.shuffle_basis > 0 then
    local feel_map = shuffle_feels[self.shuffle_feel]
    local playpos_mod = (step_mod % 8) + 1
    local base_multiplier = 0.25 
    local multiplier = feel_map[self.shuffle_basis][playpos_mod]
    local adjusted_multiplier = base_multiplier + self.shuffle_amount * (multiplier - base_multiplier)
    return ((self.division * 4) * ppc) * adjusted_multiplier
  else
    if (pattern_length % 2 == 1) and step_mod % pattern_length == 0 then
      return self.division * ppc
    else
      return (self.division * ppc) * (step_mod % 2 == 1 and self.even_swing or self.odd_swing)
    end
  end
end

function Sprocket:update_shuffle(step)
  -- A positive swung interval must consume at least one native pulse.
  -- Clamp before carry accumulation so sub-pulse gaps cannot create zero cycles.
  local calculated_ppqn = math.max(1, self:calculate_shuffle_ppqn(step))
  local original_ppqn = self.current_ppqn
  local original_phase = self.phase
  
  local rounded_ppqn = math.floor(calculated_ppqn + self.ppqn_error - 0.01)
  self.ppqn_error = (calculated_ppqn + self.ppqn_error) - rounded_ppqn
  self.current_ppqn = rounded_ppqn

  if self.current_ppqn ~= original_ppqn then
    local cycle_progress = (original_phase - 1) / original_ppqn
    self.phase = math.floor(cycle_progress * self.current_ppqn + 1)
    self.phase = math.max(1, math.min(self.current_ppqn, self.phase))
  end
end

function Sprocket:run_pending_action(pending)
  local previous = self._executing_pending_action
  self._executing_pending_action = pending
  local ok, err = pcall(pending.action)
  self._executing_pending_action = previous
  if not ok then error(err, 0) end
end

-- Select a varying interval before consuming this cycle's rounding carry.
-- Changing it after update_shuffle would round the same cycle twice.
function Sprocket:begin_cycle()
  if self.division_for_cycle then
    local division = self.division_for_cycle()
    assert(type(division) == "number" and division > 0 and division < math.huge,
      "Invalid cycle division")
    self.division = math.max(division, 1 / (self.ppqn * 4))
  end
  self:update_shuffle(self.step)
  self.shuffle_updated = true
end

function Sprocket:finish_cycle()
  if self.phase > self.current_ppqn then
    self.phase = 1
    self.shuffle_updated = false
    if self.delay_new ~= nil then
      self.phase = self.phase - (self.current_ppqn * (self.delay - self.delay_new))
      self.delay = self.delay_new
      self.delay_new = nil
    end
    self.step = self.step + 1
    if self.step > self.lattice.pattern_length then
      self.step = 1
    end
  end
end

-- Project future onsets from the current channel onset without consuming live
-- fractional carry or changing phase. Call after begin_cycle, inside action.
-- Variable-division callbacks are not channel clocks and may have side effects.
function Sprocket:project_onset_pulses(distance)
  assert(type(distance) == "number" and distance >= 1 and distance <= 64 and distance == math.floor(distance), "Invalid onset distance")
  assert(self.phase >= 1 and self.phase < 2 and self.shuffle_updated, "Projection requires a resolved channel onset")
  assert(not self.division_for_cycle and self.delay == 0 and not self.delay_new, "Unsupported variable or delayed projection")
  -- An integer straight interval preserves its carry on every future cycle.
  -- This common case needs no per-step simulation. Fractional and modulated
  -- clocks retain the exact recurrence below.
  local base = self.division * self.ppqn * 4
  local shuffle_active = self.swing_or_shuffle == 2 and self.shuffle_feel > 0 and self.shuffle_basis > 0
  if not shuffle_active and self.even_swing == 1 and self.odd_swing == 1 and
      base >= 1 and base == math.floor(base) and
      self.ppqn_error >= 0.01 and self.ppqn_error < 1.01 then
    return self.current_ppqn + (distance - 1) * base
  end
  -- Only interval length and rounding carry affect future onset deadlines.
  -- Advance those scalars without copying clocks or updating irrelevant phase
  -- fields for every parameter. Keep update_shuffle's rounding recurrence.
  local elapsed, carry, step = self.current_ppqn, self.ppqn_error, self.step
  for interval = 2, distance do
    step = step + 1
    if step > self.lattice.pattern_length then step = 1 end
    local calculated = math.max(1, self:calculate_shuffle_ppqn(step))
    local rounded = math.floor(calculated + carry - 0.01)
    carry = calculated + carry - rounded
    elapsed = elapsed + rounded
  end
  return elapsed
end

-- Predict an identified future onset from the current phase, including the
-- boundary between pulses where the next onset has not executed yet.
function Sprocket:project_onset_occurrence(occurrence)
  local remaining = occurrence - (self.onset_count or 0)
  assert(remaining >= 1 and remaining <= 64 and remaining == math.floor(remaining), "Invalid future onset occurrence")
  assert(not self.division_for_cycle and self.delay == 0 and not self.delay_new, "Unsupported variable or delayed projection")
  -- Later callbacks in this lattice pulse see phase already advanced for
  -- the next pulse. Their projection origin needs that one-pulse offset.
  local offset = self.last_processed_transport == self.lattice.transport and 1 or 0
  local projected = setmetatable({}, getmetatable(self))
  for key,value in pairs(self) do projected[key] = value end
  if not projected.shuffle_updated then projected:begin_cycle() end
  if projected.phase >= 1 and projected.phase < 2 and (offset == 1 or self.last_onset_transport ~= self.lattice.transport) then
    remaining = remaining - 1
    if remaining == 0 then return offset end
  end
  local elapsed = projected.current_ppqn - (projected.phase - 1)
  for interval = 2, remaining do
    projected.phase = projected.current_ppqn + 1
    projected:finish_cycle();projected:begin_cycle()
    elapsed = elapsed + projected.current_ppqn
  end
  return elapsed + offset
end

function Sprocket:forward_pending_setting(method, value)
  for _, timing in ipairs(self._pending_clocks or {}) do timing[method](timing, value) end
end

function Sprocket:prepare_pending_clocks()
  if not self._pending_clocks then return end
  local live = {}
  for _, pending in pairs(self.delayed_actions) do
    if pending.length == math.huge then pending.timing = nil end
    if pending.timing then live[pending.timing] = true end
  end
  local retained = {}
  for _, timing in ipairs(self._pending_clocks or {}) do
    if live[timing] then
      if not timing.shuffle_updated then timing:update_shuffle(timing.step);timing.shuffle_updated = true end
      retained[#retained + 1] = timing
    end
  end
  self._pending_clocks = #retained > 0 and retained or nil
end

function Sprocket:preserve_pending_timing()
  local timing
  local function preserve(pending)
    if not pending.timing and pending.length < math.huge and
        (pending.length > 0 or pending == self._executing_pending_action) then
      if not timing then
        timing = setmetatable({}, getmetatable(self))
        for key, value in pairs(self) do timing[key] = value end
        timing.delayed_actions = {};timing.delayed_action_order = {};timing._pending_clocks = nil
        self._pending_clocks = self._pending_clocks or {}
        self._pending_clocks[#self._pending_clocks + 1] = timing
      end
      pending.timing = timing
    end
  end
  for _, pending in pairs(self.delayed_actions) do preserve(pending) end
  if self._executing_pending_action then preserve(self._executing_pending_action) end
end

function Lattice:realign_eligable_sprockets()

  for i = 1, 5 do
    for _, id in ipairs(self.sprocket_ordering[i]) do
      local sprocket = self.sprockets[id]
      if sprocket.realign then
        sprocket:preserve_pending_timing()
        sprocket.ppqn_error = 0.5
        sprocket.phase = 1
        sprocket.step = 1
        sprocket.transport = 1
        sprocket:update_swing()
        sprocket:update_shuffle(1)  -- Passing 1 as we've reset to step 1
        sprocket.current_ppqn = sprocket.division * self.ppqn * 4
      end
    end
  end
end

return Lattice
