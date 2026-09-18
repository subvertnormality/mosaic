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




local onset_projection = include("mosaic/lib/clock/onset_projection")

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
  l.sync_to_external = args.sync_to_external == true
  l.external_clock_active = args.external_clock_active
  l.step = 1
  l.enabled = false
  l.transport = 1
  l.superclock_id = nil
  l.sprocket_id_counter = 100
  l.sprockets = {}
  l.sprocket_ordering = {{}, {}, {}, {}, {}}
  l.sprocket_pulse_order = {{}, {}, {}, {}, {}}
  l.deferred_notes = {}
  l.deferred_followers = {}
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
  self.sprocket_pulse_order = {{}, {}, {}, {}, {}}
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
  if s.sync_to_external then
    -- MIDI transport defines beat zero independently of callback latency.
    -- Count each elapsed pulse once, including acquisition/callback catch-up.
    -- Never reuse the callback's fractional phase as a permanent offset.
    local next_pulse = 0
    while not s.external_clock_active or s.external_clock_active() do
      local due = math.floor(clock.get_beats() * s.ppqn + 1e-9)
      -- A blocked Lua event thread can resume after native MIDI has already
      -- received transport Stop. Give queued input callbacks priority before
      -- replaying a musically stale pulse backlog, then bound each catch-up
      -- slice so transport remains responsive throughout reconciliation.
      local backlog = due - next_pulse + 1
      if backlog > s.ppqn / 2 then
        clock.sleep(0)
        if not s.enabled then return end
      end
      local reconciled = 0
      while next_pulse <= due do
        s:pulse()
        if not s.enabled then return end
        next_pulse = next_pulse + 1
        reconciled = reconciled + 1
        if reconciled >= s.ppqn / 2 and next_pulse <= due then
          clock.sleep(0)
          if not s.enabled then return end
          due = math.floor(clock.get_beats() * s.ppqn + 1e-9)
          reconciled = 0
        end
      end
      clock.sync(interval, 0)
    end
  end
  -- Preserve the immediate first pulse, then keep full intervals from its phase.
  -- A negative equivalent offset avoids skipping a pulse at a sync boundary.
  local origin = clock.get_beats()
  local offset = (origin % interval) - interval
  -- norns counts a coroutine's first sync from the current beat (later syncs
  -- count from their previous target), so replay whole intervals a slow first
  -- pulse overran instead of dropping them from the grid. The tolerance stays
  -- below norns' FLT_EPSILON sync margin so no pulse can run twice.
  local pulses = 0
  repeat
    s:pulse()
    pulses = pulses + 1
  until not s.enabled or clock.get_beats() + 1e-7 < origin + pulses * interval
  while true do
    clock.sync(interval, offset)
    s:pulse()
  end
end


-- Run the before-onset releases that are already due for every sprocket
-- reaching an onset on this pulse, keeping the order a single pass would have
-- used. Releases created later in the pulse are still run by the pulse itself.
function Lattice:release_due_onset_actions()
  for i = 1, 5 do
    local ordering = self.sprocket_pulse_order[i]
    for index = 1, #ordering do
      local sprocket = ordering[index]
      local phase = sprocket.phase
      if sprocket.enabled and phase >= 1 and phase < 2 then
        local pending_ids = sprocket.delayed_action_order
        for order_index = 1, #pending_ids do
          local pending_id = pending_ids[order_index]
          local pending = sprocket.delayed_actions[pending_id]
          if pending and pending.before_onset and pending.length == 0 then
            sprocket.delayed_actions[pending_id] = nil
            sprocket.released_before_onset = true
            sprocket:run_pending_action(pending)
            if not self.enabled then return end
            if sprocket.cleanup_delayed_action then
              sprocket.cleanup_delayed_action(pending_id)
            end
          end
        end
      end
    end
  end
end

-- Run one sprocket's pulse: pending releases, its onset action, then its
-- advance. Returns false when an action stopped the lattice; otherwise true,
-- and whether the onset left a note for the group's note stage, in which case
-- the sprocket advances after that note.
function Lattice:pulse_sprocket(sprocket)
    -- Set when this pulse removes a delayed action, so the order list is compacted.
    local removed = false
    local note_deferred = false
    if not sprocket.shuffle_updated then
      sprocket:begin_cycle()
    end
    if sprocket._pending_clocks then
      sprocket:prepare_pending_clocks()
    end
    if sprocket._pending_clocks then
      for _, pending_id in ipairs(sprocket.delayed_action_order) do
        local pending = sprocket.delayed_actions[pending_id]
        local timing = pending and pending.timing
        if timing and pending.before_onset and (pending.length == 0 or
            (pending.length < 1 and timing.phase - 1 >= pending_deadline(timing.current_ppqn, pending.length))) then
          sprocket.delayed_actions[pending_id] = nil
          removed = true
          sprocket:run_pending_action(pending)
          if not self.enabled then return false end
          if sprocket.cleanup_delayed_action then sprocket.cleanup_delayed_action(pending_id) end
        end
      end
    end
    if sprocket.released_before_onset then
      sprocket.released_before_onset = nil
      removed = true
    end
    if sprocket.phase >= 1 and sprocket.phase < 2 then
      -- Releases due when the pulse began have already run; this catches
      -- any a preceding sprocket's onset created during this pulse.
      -- New zero-delay actions created by this onset still run below.
      for index = 1, #sprocket.delayed_action_order do
        local pending_id = sprocket.delayed_action_order[index]
        local pending = sprocket.delayed_actions[pending_id]
        if pending and pending.before_onset and pending.length == 0 then
          sprocket.delayed_actions[pending_id] = nil
          removed = true
          sprocket:run_pending_action(pending)
          if not self.enabled then return false end
          if sprocket.cleanup_delayed_action then
            sprocket.cleanup_delayed_action(pending_id)
          end
        end
      end
      sprocket.onset_count = (sprocket.onset_count or 0) + 1
      sprocket.last_onset_transport = self.transport
      sprocket.action(self.transport)
      if not self.enabled then return false end
      if sprocket.note_pending ~= nil then
        -- This onset's note waits until the rest of the order group has
        -- sent its parameter locks; the sprocket advances after the note.
        note_deferred = true
      end
    end

    if not note_deferred and not self:advance_sprocket(sprocket, removed) then return false end
    return true, note_deferred
end

-- An output sink may gather what a pulse sends and write it at the pulse's
-- marks: after its releases, before its notes, and when the pulse ends.
function Lattice:pulse()
  local probe = _G.mosaic_pulse_probe
  if probe then
    probe.pulse = self.transport
    probe:record(1, self.transport, 0, 0, 1)
  end
  local output = self.output
  if output == nil then
    self:pulse_all()
  else
    output.begin()
    self:pulse_all()
    output.flush(true)
  end
  if probe then probe:record(1, probe.pulse, 0, 0, 2) end
end

function Lattice:pulse_all()
  if self.enabled then
    -- Parameter values resolved ahead of their own step leave here, inside a
    -- pulse the sequencer was already running and before this pulse's own work.
    -- No timer is involved, so nothing is dispatched part way through a step.
    local advance = self.advance
    if advance then advance(self.transport) end
    -- A step's note-offs and its note-ons are two bursts down one MIDI port. If
    -- each sprocket released and then sounded in turn, every channel's note-on
    -- would wait behind another channel's note-off, doubling how long a step's
    -- notes take to leave. Run the releases that are due at this pulse's onsets
    -- first, in the order those sprockets would have run them, so the onsets
    -- that follow are consecutive. The same releases still happen before any
    -- onset that could retrigger the pitch they belong to.
    self:release_due_onset_actions()
    if self.output then self.output.flush() end
    if not self.enabled then return end
    -- The seams of a pulse's work. A step holding the only thread for
    -- milliseconds is what puts a delayed note off the beat, so between the
    -- channels of that step anything whose deadline has arrived is sent, rather
    -- than waiting for the pulse after the work, which the work has itself
    -- delayed. A seam with nothing due costs a comparison.
    local serve = self.output and self.output.serve
    local flagged = false
    local deferred, deferred_count = self.deferred_notes, 0
    local followers, follower_count = self.deferred_followers, 0
    for i = 1, 5 do
      local ordering = self.sprocket_pulse_order[i]
      for index = 1, #ordering do
        if not self.enabled then return end
        -- The order holds the sprockets themselves, so no entry is ever nil.
        local sprocket = ordering[index]
        local phase = sprocket.phase
        if sprocket.enabled and sprocket.delayed_action_order[1] == nil
            and sprocket._pending_clocks == nil and sprocket.shuffle_updated
            and (phase < 1 or phase >= 2)
            and phase + 1 <= sprocket.current_ppqn then
          -- A sprocket between onsets with nothing pending only advances. Most
          -- sprockets are in this state on most pulses, and every branch the
          -- full path below would take is excluded by the conditions above.
          sprocket.phase = phase + 1
          sprocket.last_processed_transport = self.transport
          sprocket.transport = sprocket.transport + 1
        elseif sprocket.enabled and sprocket.follows ~= nil and sprocket.follows.note_pending ~= nil then
          -- A sprocket that belongs to a channel (an arp) runs after that
          -- channel's step, as it did when notes were sent inside the channel
          -- action: the step's note may cancel it before this pulse's onset.
          follower_count = follower_count + 1
          followers[follower_count] = sprocket
        elseif sprocket.enabled then
          local running, note_deferred = self:pulse_sprocket(sprocket)
          if not running then return end
          if note_deferred then
            deferred_count = deferred_count + 1
            deferred[deferred_count] = sprocket
          end
          if serve then serve() end
        elseif sprocket.flag then
          self.sprockets[sprocket.id] = nil
          flagged = true
        end
      end
      if deferred_count > 0 then
        -- Last seam before this group's notes: a deadline already passed is
        -- served here rather than behind the notes that follow it.
        if serve then serve() end
        if self.output then self.output.flush() end
        -- The group's notes leave back to back, then each sprocket finishes its
        -- step and moves past the onset. Every note is still sent before its
        -- own sprocket advances, so its releases keep the phase they had.
        for index = 1, deferred_count do
          local sprocket = deferred[index]
          -- An earlier note in this group may have created a release that is
          -- due before this onset; it must still precede this sprocket's note.
          local removed = false
          local pending_ids = sprocket.delayed_action_order
          for order_index = 1, #pending_ids do
            local pending_id = pending_ids[order_index]
            local pending = sprocket.delayed_actions[pending_id]
            if pending and pending.before_onset and pending.length == 0 then
              sprocket.delayed_actions[pending_id] = nil
              removed = true
              sprocket:run_pending_action(pending)
              if not self.enabled then return end
              if sprocket.cleanup_delayed_action then sprocket.cleanup_delayed_action(pending_id) end
            end
          end
          sprocket.released_before_note = removed
          local probe = _G.mosaic_pulse_probe
          if probe then probe:record(3, self.transport, sprocket.id, 0, 1) end
          sprocket:note_action(self.transport)
          if probe then probe:record(3, self.transport, sprocket.id, 0, 2) end
          if not self.enabled then return end
        end
        for index = 1, deferred_count do
          local sprocket = deferred[index]
          deferred[index] = nil
          sprocket:after_note_action(self.transport)
          if not self.enabled then return end
          if not self:advance_sprocket(sprocket, sprocket.released_before_note) then return end
        end
        deferred_count = 0
      end
      for index = 1, follower_count do
        local sprocket = followers[index]
        followers[index] = nil
        if sprocket.enabled then
          if not self:pulse_sprocket(sprocket) then return end
        elseif sprocket.flag then
          self.sprockets[sprocket.id] = nil
          flagged = true
        end
      end
      follower_count = 0
    end
    if flagged then
      self:order_sprockets()
    end
    -- A step resolves the next step's values as it finishes, and one of them can
    -- be owed in this very pulse. Serve again before the transport moves on, so
    -- that value leaves in the pulse it belongs to rather than a pulse later
    -- with less lead than was asked for. It follows this step's note, and still
    -- precedes the step it was resolved for.
    if advance then advance(self.transport) end
    self.transport = self.transport + 1
    if self.transport % (self.ppqn / 4) == 0 then
      self.step = self.step + 1
    end
  end
end

-- Move a sprocket past this pulse: advance its phase, run or age its delayed
-- actions and close its cycle. Returns false when an action stopped the lattice.
function Lattice:advance_sprocket(sprocket, removed)
  sprocket.phase = sprocket.phase + 1
  if sprocket._pending_clocks then
    for _, timing in ipairs(sprocket._pending_clocks) do timing.phase = timing.phase + 1 end
  end

  -- Equal-deadline actions retain insertion order across Lua processes.
  -- Most sprockets hold none on most pulses; skip the bookkeeping then.
  local pending_ids = sprocket.delayed_action_order
  local pending_count = #pending_ids
  if pending_count > 0 then
    local to_remove
    -- Set when an id's action is already gone, cancelled outside the pulse.
    local stale = false
    local delayed_actions = sprocket.delayed_actions
    for index = 1, pending_count do
      local id = pending_ids[index]
      local delayed_action = delayed_actions[id]
      if not delayed_action then
        stale = true
      else
        local timing = delayed_action.timing or sprocket
        local length = delayed_action.length
        if length == 0 then
            sprocket:run_pending_action(delayed_action)
            if not self.enabled then return false end
            to_remove = to_remove or {}
            table.insert(to_remove, id)
            if sprocket.cleanup_delayed_action then
              sprocket.cleanup_delayed_action(id)
            end
        elseif length < 1 then
            -- Phase is1 at onset and was incremented above: elapsed ticks = phase-2.
            if timing.phase - 2 >= pending_deadline(timing.current_ppqn, length) then
                sprocket:run_pending_action(delayed_action)
                if not self.enabled then return false end
                to_remove = to_remove or {}
                table.insert(to_remove, id)
                if sprocket.cleanup_delayed_action then
                  sprocket.cleanup_delayed_action(id)
                end
            elseif timing.phase > timing.current_ppqn then
                -- Fractions rounding to a full cycle fire at its next onset.
                delayed_action.length = 0
            end
        elseif timing.phase > timing.current_ppqn then
            delayed_action.length = length - 1
        end
      end
    end
  
    if to_remove then
      removed = true
      for _, id in ipairs(to_remove) do
          sprocket.delayed_actions[id] = nil
      end
    end
    -- Compact cancelled/completed entries without sorting or shifting.
    -- Every reader skips ids without an action, but each one left in the
    -- list is walked again on every pulse, and a list holding only such ids
    -- keeps the sprocket off the idle path. A note's releases are usually
    -- cancelled rather than run, so compact as soon as a walk meets one.
    if removed or stale then
      local retained = 0
      for index = 1, #pending_ids do
        local id = pending_ids[index]
        if sprocket.delayed_actions[id] then
          retained = retained + 1
          pending_ids[retained] = id
        end
      end
      for index = #pending_ids, retained + 1, -1 do pending_ids[index] = nil end
    end
  end

  if sprocket._pending_clocks then
    for _, timing in ipairs(sprocket._pending_clocks) do
      timing:finish_cycle()
      timing.transport = timing.transport + 1
    end
  end
  -- finish_cycle only acts at the end of a cycle; skip the call otherwise.
  if sprocket.phase > sprocket.current_ppqn then sprocket:finish_cycle() end
  sprocket.last_processed_transport = self.transport
  sprocket.transport = sprocket.transport + 1
  return true
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
  -- The pulse walks the sprockets themselves; the ids stay for every other
  -- reader, and both lists are rebuilt together whenever the set changes.
  local pulse_order = {{}, {}, {}, {}, {}}
  for i = 1, 5 do
    local ids = self.sprocket_ordering[i]
    table.sort(ids)
    local ordered = pulse_order[i]
    for index = 1, #ids do ordered[index] = self.sprockets[ids[index]] end
  end
  self.sprocket_pulse_order = pulse_order
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
  -- The channel sprocket whose step this one waits for (see Lattice:pulse).
  p.follows = args.follows
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
  return onset_projection.calculate(self, self.lattice.pattern_length, step)
end

function Sprocket:update_shuffle(step)
  -- A positive swung interval must consume at least one native pulse.
  -- Clamp before carry accumulation so sub-pulse gaps cannot create zero cycles.
  local original_ppqn = self.current_ppqn
  local original_phase = self.phase
  self.current_ppqn, self.ppqn_error = onset_projection.interval(self, self.lattice.pattern_length, step, self.ppqn_error)

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
  return onset_projection.project_pulses(self, self.lattice.pattern_length,
    self.current_ppqn, self.ppqn_error, self.step, distance)
end

-- Predict an identified future onset from the current phase, including the
-- boundary between pulses where the next onset has not executed yet.
function Sprocket:project_onset_occurrence(occurrence)
  local remaining = occurrence - (self.onset_count or 0)
  assert(remaining >= 1 and remaining <= 64 and remaining == math.floor(remaining), "Invalid future onset occurrence")
  assert(not self.division_for_cycle and self.delay == 0 and not self.delay_new, "Unsupported variable or delayed projection")
  -- Later callbacks in this lattice pulse see phase already advanced for
  -- the next pulse. Their projection origin needs that one-pulse offset.
  return onset_projection.project_occurrence(self, self.lattice.pattern_length, self.lattice.transport, occurrence)
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
        -- Restarted step 1 is resolved by begin_cycle, as at a step boundary,
        -- also when the reset lands mid-step (defect realign-mid-step-length).
        sprocket.shuffle_updated = false
      end
    end
  end
end

-- Normalize a stopped lattice as freshly constructed, while retaining its
-- sprockets and callbacks. Unlike an in-song realignment, delayed processors
-- must keep their constructor offset so they cannot fire at the first onset.
function Lattice:prepare_for_start()
  for order = 1, 5 do
    for _, id in ipairs(self.sprocket_ordering[order]) do
      local sprocket = self.sprockets[id]
      if sprocket.realign then
        local delay = sprocket.delay_new ~= nil and sprocket.delay_new or sprocket.delay
        sprocket.delay = delay
        sprocket.delay_new = nil
        sprocket.ppqn_error = 0.5
        sprocket.step = 1
        sprocket.transport = 1
        sprocket:update_swing()
        sprocket:update_shuffle(1)
        sprocket.phase = 1 - (sprocket.current_ppqn * delay)
        sprocket.shuffle_updated = false
      end
    end
  end
  self.transport = 1
end

return Lattice
