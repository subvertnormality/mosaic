-- Owned slide storage, interpolation and callback retirement.
-- Preserve slot references and traversal boundaries during reentrant callbacks.
local slide_lifetime = {}

function slide_lifetime.new(m_clock, program, get_lattice)
  local slides = {}
  local quantize_value = m_clock.quantize_value
  local active_spread_actions = {}

  local RING_BUFFER_SIZE = 1024 -- Power of 2 for efficient modulo
  local spread_ring = {}
  local ring_start = 1
  local ring_end = 1

  -- The ring owns execution order; this index owns channel/parameter lookup.
  -- Store slot references so compaction can move slots without rebuilding owners.
  local function register_spread_action(action)
    local owners = active_spread_actions[action.channel]
    if not owners then
      owners = {}
      active_spread_actions[action.channel] = owners
    end
    owners[action.trig_lock] = action
  end

  local function retire_spread_action(action)
    action.active = false
    local owners = active_spread_actions[action.channel]
    if owners and owners[action.trig_lock] == action then
      owners[action.trig_lock] = nil
      if next(owners) == nil then active_spread_actions[action.channel] = nil end
    end
  end

  -- Initialize ring buffer
  local function init_ring_buffer()
    for i = 1, RING_BUFFER_SIZE do
      spread_ring[i] = {
        channel = 0,
        trig_lock = 0,
        pulse_count = 0,
        total_pulses = 0,
        start_value = 0,
        end_value = 0,
        quant = 0,
        func = nil,
        active = false
      }
    end
  end

  -- Replaced and finished actions are only reclaimed from the front. When a long
  -- action sits there, move the active actions (in order) to the front so the
  -- retired slots behind it can be reused.
  local function compact_ring()
    local active, retired = {}, {}
    local i = ring_start
    repeat
      local slot = spread_ring[i]
      if slot.active then active[#active + 1] = slot else retired[#retired + 1] = slot end
      i = (i % RING_BUFFER_SIZE) + 1
    until i == ring_start
    for index, slot in ipairs(active) do spread_ring[index] = slot end
    for index, slot in ipairs(retired) do spread_ring[#active + index] = slot end
    ring_start = 1
    ring_end = #active + 1
  end

  -- Add action to ring buffer
  local function ring_push(action)
    local next_end = (ring_end % RING_BUFFER_SIZE) + 1
    if next_end == ring_start then
      compact_ring()
      next_end = (ring_end % RING_BUFFER_SIZE) + 1
      if next_end == ring_start then return false end -- Every slot holds an active action
    end
  
    local slot = spread_ring[ring_end]
    slot.channel = action.channel
    slot.trig_lock = action.trig_lock
    slot.pulse_count = action.pulse_count
    slot.total_pulses = action.total_pulses
    slot.start_pulse = action.start_pulse
    slot.end_occurrence = action.end_occurrence
    slot.end_step = action.end_step
    slot.start_value = action.start_value
    slot.last_value = action.last_value
    slot.end_value = action.end_value
    slot.quant = action.quant
    slot.func = action.func
    slot.active = true
    register_spread_action(slot)
  
    ring_end = next_end
    return true
  end

  -- Process ring buffer in execute_spread_actions
  local function process_ring_buffer()
    local i = ring_start
    while i ~= ring_end do
      local action = spread_ring[i]
      if action.active then
        local pulse_count = get_lattice().transport - action.start_pulse
        local total_pulses = action.total_pulses
  
        if pulse_count >= total_pulses then
          retire_spread_action(action)
          action.func(action.end_value, action.last_value)
          action.last_value = action.end_value
        else
          -- Calculate value based on position
          local current_value
          if pulse_count == 0 then
            current_value = action.start_value
          else
            local progress = pulse_count / total_pulses
            current_value = action.start_value +
              (action.end_value - action.start_value) * progress
          end
  
          -- Apply quantization if needed
          if action.quant and action.quant > 0 then
            current_value = quantize_value(current_value, action.quant)
          end
  
          action.func(current_value, action.last_value)
          action.last_value = current_value
          action.pulse_count = pulse_count
        end
      end
      i = (i % RING_BUFFER_SIZE) + 1
    end
  
    -- Compact buffer by moving start pointer past inactive entries
    while ring_start ~= ring_end and not spread_ring[ring_start].active do
      ring_start = (ring_start % RING_BUFFER_SIZE) + 1
    end
  end

  function slides.retime(channel_number, channel_clock)
    local now = get_lattice().transport
    local i = ring_start
    while i ~= ring_end do
      local action = spread_ring[i]
      if action.active and action.channel == channel_number and action.end_occurrence and
          action.end_occurrence > (channel_clock.onset_count or 0) then
        local progress = action.total_pulses > 0 and math.min(1,math.max(0,(now-action.start_pulse)/action.total_pulses)) or 1
        local value = action.start_value + (action.end_value-action.start_value)*progress
        action.total_pulses = channel_clock:project_onset_occurrence(action.end_occurrence)
        action.start_pulse = now
        action.start_value = value
        -- Retain last_value: rebasing alone must not send a MIDI message.
      end
      i = (i % RING_BUFFER_SIZE) + 1
    end
  end

  function slides.realign()
    local now = get_lattice().transport
    local i = ring_start
    while i ~= ring_end do
      local action = spread_ring[i]
      local clock = m_clock["channel_" .. action.channel .. "_clock"]
      if action.active and clock and clock.realign then
        local channel = program.get_channel(program.get().selected_song_pattern, action.channel)
        local first, last = program.get_channel_step_bounds(channel)
        if action.end_step < first or action.end_step > last then
          retire_spread_action(action)
        else
          -- Reset makes the next onset the channel's first step. Retain the
          -- destination's step identity, not its old occurrence ordinal.
          local progress = action.total_pulses > 0 and math.min(1,math.max(0,(now-action.start_pulse)/action.total_pulses)) or 1
          local value = action.start_value + (action.end_value-action.start_value)*progress
          action.end_occurrence = (clock.onset_count or 0) + 1 + action.end_step - first
          action.total_pulses = clock:project_onset_occurrence(action.end_occurrence)
          action.start_pulse = now
          action.start_value = value
        end
      end
      i = (i % RING_BUFFER_SIZE) + 1
    end
  end

  function slides.cancel_all()
    local i = ring_start
    while i ~= ring_end do
      retire_spread_action(spread_ring[i])
      i = (i % RING_BUFFER_SIZE) + 1
    end
  end

  -- Resolve incoming ownership before a non-Off lock and its note are sent.
  -- A matching scheduled endpoint shares one write with that destination lock.
  function slides.handoff(channel_number, trig_lock, step_number, value)
    local applied = false
    local i, stop = ring_start, ring_end
    while i ~= stop do
      local action = spread_ring[i]
      if action.active and action.channel == channel_number and action.trig_lock == trig_lock then
        retire_spread_action(action)
        if action.end_step == step_number and action.end_value == value and
            get_lattice().transport >= action.start_pulse + action.total_pulses then
          -- This is the explicit destination lock, not an intermediate sample.
          -- Retain its write even if earlier interpolation rounded to the target.
          action.func(action.end_value)
          action.last_value = action.end_value
          applied = true
        end
      end
      i = (i % RING_BUFFER_SIZE) + 1
    end
    return applied
  end

  function slides.cancel(channel_number, trig_lock, use_end_value)
    local i, stop = ring_start, ring_end
    while i ~= stop do
      local action = spread_ring[i]
      if action.active and action.channel == channel_number then
        if not trig_lock or action.trig_lock == trig_lock then
          -- Replacement is silent. Retire ownership before invoking an explicit
          -- finish callback, which may itself cancel or schedule another action.
          retire_spread_action(action)
          if use_end_value then
            action.func(action.end_value, action.last_value)
            action.last_value = action.end_value
          end
        end
      end
      i = (i % RING_BUFFER_SIZE) + 1
    end
  end

  function slides.is_active(channel, trig_param)
    local owners = active_spread_actions[channel.number]
    local action = owners and owners[trig_param]
    return action ~= nil and action.active
  end

  function slides.reset()
    active_spread_actions = {}
    init_ring_buffer()
    ring_start = 1
    ring_end = 1
  end
  slides.push = ring_push
  slides.process = process_ring_buffer
  return slides
end

return slide_lifetime
