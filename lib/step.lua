local param_slots = include("mosaic/lib/devices/param_slots")
local parameter_preview = include("mosaic/lib/clock/parameter_preview")
local nrpn_codec = include("mosaic/lib/devices/nrpn_codec")
local chord_timing = include("mosaic/lib/clock/chord_timing")
local chord_order = include("mosaic/lib/musical_resolution/chord_order")
local stock_parameter = include("mosaic/lib/musical_resolution/stock_parameter")
local pitch_resolution = include("mosaic/lib/musical_resolution/pitch_resolution")
local arp_descriptor = include("mosaic/lib/musical_resolution/arp_descriptor")
local strum_descriptor = include("mosaic/lib/musical_resolution/strum_descriptor")
local quantiser = include("mosaic/lib/quantiser")
local harmony_state = include("mosaic/lib/harmony/state")
local harmony_config = include("mosaic/lib/harmony/config")
local harmony_config_state = include("mosaic/lib/harmony/config_state")
local harmony_context = include("mosaic/lib/harmony/context")
local pattern_harmony = include("mosaic/lib/harmony/pattern")
local harmony_inspection = include("mosaic/lib/harmony/inspection")
local merge_pitch_target = include("mosaic/lib/musical_merge/pitch_target")
local musical_merge_state = include("mosaic/lib/musical_merge/state")
local musical_merge_config = include("mosaic/lib/musical_merge/config")
local m_clock = include("mosaic/lib/clock/m_clock")
local play_note, play_arp_note = include("mosaic/lib/clock/voice_lifetime").new(m_clock)

local divisions = include("mosaic/lib/clock/divisions")

local step = {}
local persistent_channel_step_scale_numbers = {
    nil, nil, nil, nil, nil, nil, nil, nil,
    nil, nil, nil, nil, nil, nil, nil, nil
}
local persistent_global_step_scale_number = nil
local persistent_step_transpose = nil

local arp_note = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0}

local step_scale_number = 0



local note_divisions = divisions.note_divisions

random = math.random

-- performance optimisation
local program = program
local ipairs = ipairs
local table = table
local song_transition = include("mosaic/lib/song_transition").new(program, m_clock, step)

local quantiser_process = quantiser.process
local quantiser_process_chord_note_for_mask = quantiser.process_chord_note_for_mask
local fn_constrain = fn.constrain

local resolve_pitch = pitch_resolution.new(
  quantiser.translate_note_mask_to_relative_scale_position,
  quantiser.process,
  quantiser.snap_to_scale,
  function()
    return params:get("quantiser_fully_act_on_note_masks") == 2
  end,
  function()
    return params:get("quantiser_act_on_note_masks") == 2
  end
)
local build_arp_sequence = arp_descriptor.new(chord_order.index)
local play_strum_root_now, resolve_strum_chord, resolve_strum_root_later =
  strum_descriptor.new(chord_order.index, chord_timing.delay)

local function read_stock_step_lock(i, channel, current_step)
  return program.get_step_param_trig_lock(channel, current_step, i)
end

-- Per-note stock reads go straight through the paramset's id index. An id the
-- index does not hold falls back to the public calls, which behave as before.
local function indexed_param(param_id)
  local lookup = params.lookup
  local index = lookup and lookup[param_id]
  return index and params.params[index]
end

-- Mapping a norns control parameter rounds and warps its raw value on every
-- read, and step playback reads about ten of them for each note. The mapped
-- value is a function of the raw value and the controlspec only while norns'
-- own getter, value mapping and controlspec map are the ones in use. A mod may
-- replace any of them (matrix replaces Control:get so the value follows a
-- modulation source while raw stands still), so a parameter whose functions do
-- not come from norns core is read every time.
local core_sources = {
  get = "core/params/control.lua",
  map_value = "core/params/control.lua",
  map = "core/controlspec.lua",
}
local core_function_verdicts = setmetatable({}, {__mode = "k"})

local function is_core_function(fn_value, source)
  local verdict = core_function_verdicts[fn_value]
  if verdict == nil then
    verdict = false
    if type(fn_value) == "function" then
      local info = debug.getinfo(fn_value, "S")
      local defined = info and info.source or ""
      verdict = defined:sub(-#source) == source
    end
    core_function_verdicts[fn_value] = verdict
  end
  return verdict
end

local mapped_control_values = setmetatable({}, {__mode = "k"})

local function control_value(param)
  local spec = param.controlspec
  local raw = param.raw
  local cached = mapped_control_values[param]
  -- The entry holds the functions it was mapped with, so a hit needs no
  -- verdict lookups: any replaced getter, mapping or controlspec misses.
  if cached and cached.raw == raw and cached.spec == spec and cached.get == param.get
      and cached.map_value == param.map_value and cached.map == spec.map and cached.minval == spec.minval
      and cached.maxval == spec.maxval and cached.warp == spec.warp and cached.step == spec.step then
    return cached.value
  end
  if param.t ~= 3 or spec == nil or raw == nil
      or not is_core_function(param.get, core_sources.get)
      or not is_core_function(param.map_value, core_sources.map_value)
      or not is_core_function(spec.map, core_sources.map) then
    return param:get()
  end
  local value = param:get()
  if not cached then
    cached = {}
    mapped_control_values[param] = cached
  end
  cached.raw, cached.spec, cached.get, cached.map_value, cached.map = raw, spec, param.get, param.map_value, spec.map
  cached.minval, cached.maxval, cached.warp, cached.step, cached.value = spec.minval, spec.maxval, spec.warp, spec.step, value
  return value
end

local function read_stock_assigned(param_id)
  local param = indexed_param(param_id)
  if param then return control_value(param) end
  return params:get(param_id)
end

local function read_stock_default(param)
  return param.default
end

local function read_stock_fallback(kind, channel)
  local param_id = fn.get_param_id_from_stock_id(kind, channel.number)
  if param_id then
    local param = indexed_param(param_id)
    if param then return control_value(param), read_stock_default, param end
    local value = params:get(param_id)
    param = params:lookup_param(param_id)
    return value, read_stock_default, param
  end
  return nil, nil
end

function step.process_stock_params(c, current_step, kind)
  local channel = program.get_channel(program.get().selected_song_pattern, c)
  return stock_parameter.resolve(channel.trig_lock_params, kind,
    read_stock_step_lock, read_stock_assigned, read_stock_fallback, channel, current_step)
end

-- Stock kinds resolved by step handling rather than sent as parameter locks.
-- The list and the eligibility test live with the read-only preview so playback
-- and a lock preview cannot disagree about which slots are parameter sends.
local should_process_param = parameter_preview.should_process_param

local function process_midi_param(param, step_trig_lock, midi_channel, midi_device, mode)

  if param.nrpn_min_value and param.nrpn_max_value and param.nrpn_lsb and param.nrpn_msb then
      m_midi.nrpn(
          param.nrpn_msb,
          param.nrpn_lsb, 
          step_trig_lock or value,
          midi_channel,
          midi_device,
          mode
      )
  elseif param.cc_min_value and param.cc_max_value and param.cc_msb then
      m_midi.cc(
          param.cc_msb,
          param.cc_lsb,
          step_trig_lock or value, 
          midi_channel,
          midi_device
      )
  end
end

-- README "Default Parameter Values": an unlocked step sends the channel's
-- assigned value, so a parameter that is not being locked repeats the same
-- message on every step. A sixteen-channel step can carry a hundred of them,
-- and they all queue in front of that step's notes. When the player turns the
-- repeat off, a value that has not changed since this slot last sent one is
-- not sent again; the receiving device is already holding it.
local last_sent_lock_values = {}

function step.forget_sent_lock_values()
  last_sent_lock_values = {}
end

-- Something else has written this slot's address since it last sent. The
-- receiver no longer holds what the cache says, so the next send must go even
-- when its value is the one last sent from here.
function step.forget_sent_lock_value(channel_number, slot)
  local per_channel = last_sent_lock_values[channel_number]
  if per_channel then per_channel[slot] = nil end
end

-- Lock lookahead installs its scheduler here. Declared before the send path
-- because that path checks it; the installer below assigns this same local.
local lock_lookahead_scheduler = nil

-- The last value each slot actually put on the wire, kept only while lock
-- lookahead is installed. The resend cache above cannot serve this: it is only
-- written when the player turns the repeat off, and the value a withdrawn early
-- send has to put back is needed whatever that setting says.
local in_force_lock_values = {}

function step.forget_in_force_lock_values()
  in_force_lock_values = {}
end

function step.last_sent_lock_value(channel_number, slot)
  local per_channel = in_force_lock_values[channel_number]
  return per_channel and per_channel[slot]
end

local function send_midi_param(channel_number, slot, param, value, midi_channel, midi_device, mode)
  -- Absent or On means resend, so the documented default behaviour is kept.
  if fn.param_value("repeat_unchanged_locks") == 1 then
    local per_channel = last_sent_lock_values[channel_number]
    if per_channel == nil then
      per_channel = {}
      last_sent_lock_values[channel_number] = per_channel
    end
    if per_channel[slot] == value then return end
    per_channel[slot] = value
  end
  if lock_lookahead_scheduler then
    local held = in_force_lock_values[channel_number]
    if held == nil then
      held = {}
      in_force_lock_values[channel_number] = held
    end
    held[slot] = value
  end
  process_midi_param(param, value, midi_channel, midi_device, mode)
end


-- Emit the value that this eligible step will record, not a stale playback
-- lock. Repeating it also restores sound after selection or mute pauses.
function step.process_recording_params(channel)
  local data = program.get()
  if channel.mute or fn.param_value("record") ~= 2 or data.selected_channel ~= channel.number then return end
  for i, param in ipairs(channel.trig_lock_params) do
    local dirty = recorder.trig_lock_is_dirty(channel.number, i)
    if dirty ~= nil and dirty ~= false and param.type == "midi" and param.param_id and
        (param.cc_msb ~= nil or (param.nrpn_msb ~= nil and param.nrpn_lsb ~= nil)) then
      local off = param.off_value == nil and -1 or param.off_value
      -- Off sends nothing and does not cancel a running slide (user contract).
      if dirty ~= off then
        m_clock.cancel_spread_actions_for_channel_trig_lock(channel.number, i)
        local p = params:lookup_param(param.param_id)
        assert(p and type(p.action) == "function", "Missing MIDI parameter recording action")
        p.action(dirty)
      end
    end
  end
end

-- Two slots can hold the same device parameter: a device map can assign Filter
-- frequency automatically and a player can assign it again by hand. Both write
-- one MIDI address, and the device keeps whichever arrives last. A slot that is
-- locked or sliding on this step claims its address, and other slots then do not
-- send their assigned value to it. The claims are stamped with a per-call number
-- rather than cleared, so a step without locks or slides allocates nothing.
local claimed_addresses = {}
local claim_stamp = 0

-- Shared with the read-only preview so a claim means the same address in both.
local midi_address = parameter_preview.midi_address

local function claim_addresses(channel, step, trig_lock_params, device_midi_channel)
  local bank = channel.step_trig_lock_banks[step]
  local claimed = false
  for i, param in ipairs(trig_lock_params) do
    if param.param_id and param.type == "midi" then
      local lock_value = bank and bank[i]
      local off = param.off_value == nil and -1 or param.off_value
      if (lock_value ~= nil and lock_value ~= off) or m_clock.channel_is_sliding(channel, i) then
        local address = midi_address(param, param.channel or device_midi_channel)
        if address then
          if not claimed then claim_stamp = claim_stamp + 1; claimed = true end
          claimed_addresses[address] = claim_stamp
        end
      end
    end
  end
  return claimed
end

-- Lock lookahead installs its scheduler here. With none installed, playback is
-- exactly as it was: every value is resolved and sent at its own step.
function step.set_lock_lookahead(scheduler)
  lock_lookahead_scheduler = scheduler
end

function step.get_lock_lookahead()
  return lock_lookahead_scheduler
end

-- Build the read-only view the pure preview needs out of live project state.
-- Every field is a read; nothing here can send, claim or cancel anything.
function step.preview_view(channel)
  local program_data = program.get()
  local devices = program_data.devices
  local device = device_map.get_device(devices[channel.number].device_map)
  local channel_number = channel.number
  return {
    channel = channel_number,
    params = channel.trig_lock_params,
    mute = channel.mute,
    midi_channel = devices[channel_number].midi_channel,
    midi_device = devices[channel_number].midi_device,
    recording_selected = fn.param_value("record") == 2 and
      program_data.selected_channel == channel_number,
    recording_dirty = function(slot) return recorder.trig_lock_is_dirty(channel_number, slot) end,
    step_lock = function(slot, step_number)
      return program.get_step_param_trig_lock(channel, step_number, slot)
    end,
    assigned = function(param_id) return read_stock_assigned(param_id) end,
    is_sliding = function(slot) return m_clock.channel_is_sliding(channel, slot) end,
    would_handoff = function(slot, step_number, value)
      return m_clock.spread_lock_would_handoff(channel_number, slot, step_number, value)
    end,
    next_lock = function(slot, step_number, off)
      return program.get_next_trig_lock_step(channel, step_number, slot, off)
    end,
    channel_slide = function(slot) return program.get_channel_param_slide(channel, slot) end,
    step_slide = function(slot, step_number)
      return program.get_step_param_slide(channel, step_number, slot)
    end,
    nrpn_mode = function(param)
      return param.nrpn_lsb_mode or nrpn_codec.stored_mode(program_data, channel_number, param, device)
    end,
    resend_unchanged = fn.param_value("repeat_unchanged_locks") ~= 1,
    last_sent = function(slot)
      local per_channel = last_sent_lock_values[channel_number]
      return per_channel and per_channel[slot]
    end,
  }
end

-- Send a previewed value down the same path playback uses, so the resend cache
-- is committed here and in no other place.
--
-- The value was resolved at the previous onset, and the player can act in the
-- interval: muting the channel, or turning the assigned control, or recording
-- over the slot. Those are decided again here, against the state as it is now,
-- because sending a value the player has since overruled is worse than sending
-- it late. Returning false leaves the slot uncommitted, so its own step sends
-- whatever is then in force.
-- Put back the value a withdrawn early send displaced. Sent through the same
-- path as any other parameter write, so the resend cache and the lookahead's
-- own write observer both see it.
function step.restore_lock_value(channel_number, slot, value)
  if value == nil then return end
  local program_data = program.get()
  local channel = program.get_channel(program_data.selected_song_pattern, channel_number)
  local param = channel and channel.trig_lock_params[slot]
  if param == nil or param.param_id == nil or param.type ~= "midi" then return end
  local devices = program_data.devices
  local midi_channel = param.channel or devices[channel_number].midi_channel
  local nrpn_mode
  if param.nrpn_msb ~= nil then
    nrpn_mode = param.nrpn_lsb_mode or nrpn_codec.stored_mode(program_data, channel_number, param, device_map.get_device(devices[channel_number].device_map))
  end
  send_midi_param(channel_number, slot, param, value, midi_channel, devices[channel_number].midi_device, nrpn_mode)
end

function step.send_preview_bundle(bundle)
  local program_data = program.get()
  local channel = program.get_channel(program_data.selected_song_pattern, bundle.channel)
  if channel == nil or channel.mute then return false end
  if fn.param_value("record") == 2 and program_data.selected_channel == bundle.channel
      and recorder.trig_lock_is_dirty(bundle.channel, bundle.slot) then
    return false
  end
  -- An assigned value that the player has since changed is not resent from a
  -- stale preview; only a step's own lock is fixed at the time it was resolved.
  if bundle.kind == "assigned" and read_stock_assigned(bundle.param.param_id) ~= bundle.value then
    return false
  end
  -- The slot may have been reassigned to a different parameter since. Sending
  -- the old one would address a control this slot no longer holds.
  local assigned_now = channel.trig_lock_params[bundle.slot]
  if assigned_now == nil or assigned_now.param_id ~= bundle.param.param_id then return false end
  bundle.displaced = step.last_sent_lock_value(bundle.channel, bundle.slot)
  send_midi_param(bundle.channel, bundle.slot, bundle.param, bundle.value,
                  bundle.midi_channel, bundle.midi_device, bundle.nrpn_mode)
  return true
end

function step.process_params(channel, step)
  local program_data = program.get()

  local device = device_map.get_device(program_data.devices[channel.number].device_map)
  local trig_lock_params = channel.trig_lock_params

  local value
  local devices = program_data.devices

  if channel.mute then
    return
  end 

  local recording_selected_channel = fn.param_value("record") == 2 and program_data.selected_channel == channel.number
  local any_claimed = claim_addresses(channel, step, trig_lock_params, devices[channel.number].midi_channel)

  local scheduler = lock_lookahead_scheduler
  for i, param in ipairs(trig_lock_params) do
    -- Unassigned slots are the common case; test the cheapest condition first.
    if param.param_id and should_process_param(param) then
      local off = param.off_value == nil and -1 or param.off_value

      -- Under lock lookahead this slot's value may already have left in an
      -- earlier pulse. Only the identical value to the identical address is
      -- suppressed: anything that changed what this step resolves, or where it
      -- goes, is sent here and corrects the receiver, and a value that never
      -- left is never suppressed. Everything else the step does still happens,
      -- because a slide starts here and skipping the branch outright would
      -- leave it never running.
      local sent_slot = i
      local function already_sent_value(value, destination)
        return scheduler ~= nil and scheduler:was_sent(channel.number, step, sent_slot, value, destination)
      end

      if recording_selected_channel and recorder.trig_lock_is_dirty(channel.number, i) then
        goto continue
      end

      local step_trig_lock = program.get_step_param_trig_lock(channel, step, i)

      -- A locked MIDI step sends its lock; only other paths use the assigned value.
      if step_trig_lock == nil or param.type ~= "midi" then
        value = read_stock_assigned(param.param_id)
      else
        value = nil
      end

      local next_lock
      
      -- The next lock only feeds a slide. Once both slide tables exist, reading
      -- them has no side effects, so skip the search for locks that cannot slide.
      local channel_slides, step_slides = channel.trig_lock_slides, channel.step_trig_lock_slides
      if step_trig_lock and (not channel_slides or not step_slides or channel_slides[i] or
          (step_slides[step] and step_slides[step][i])) then
        next_lock = program.get_next_trig_lock_step(channel, step, i, off)
      end

      if param.type == "midi" and (param.cc_msb or param.nrpn_msb) then

        local midi_channel = param.channel or devices[channel.number].midi_channel
        local nrpn_mode
        if param.nrpn_msb ~= nil then
          nrpn_mode = param.nrpn_lsb_mode or nrpn_codec.stored_mode(program_data, channel.number, param, device)
        end

        -- The assigned value was read above; param_id is always present here.
        local p_value = value

        if param.channel then
          midi_channel = param.channel
        end
        -- Where this slot's value lands, for the lookahead's record of what it
        -- already sent there. Nothing is looked up without a scheduler.
        local destination
        if scheduler ~= nil then
          destination = parameter_preview.destination(devices[channel.number].midi_device,
                                                      midi_address(param, midi_channel))
        end
        if step_trig_lock then
          if step_trig_lock == off then
            goto continue
          end

          -- The handoff still runs when the value has already gone: it retires
          -- the slide that owned this slot, which is not a send.
          local already_sent = already_sent_value(step_trig_lock, destination)
          local handed = m_clock.handoff_spread_lock(channel.number, i, step, step_trig_lock, already_sent)
          if not handed and not already_sent then
            send_midi_param(channel.number, i, param, step_trig_lock, midi_channel, devices[channel.number].midi_device, nrpn_mode)
          end

          if next_lock and (program.get_channel_param_slide(channel, i) or program.get_step_param_slide(channel, step, i)) then
            m_clock.execute_action_across_steps_by_pulses({
              channel_number = channel.number,
              trig_lock = i,
              start_step = step,
              end_step = next_lock.step,
              distance = next_lock.distance,
              start_value = step_trig_lock,
              end_value = next_lock.value,
              should_wrap = next_lock.should_wrap,
              quant = 1,
              func = function(value, last_value)
                if last_value ~= value then
                  process_midi_param(param, value, midi_channel, devices[channel.number].midi_device, nrpn_mode)
                end
              end
            })
          end

        elseif p_value and param.type == "midi" and (param.cc_msb or param.nrpn_msb) and not m_clock.channel_is_sliding(channel, i) then
          if p_value == off then
            goto continue
          end
          if any_claimed and claimed_addresses[midi_address(param, midi_channel)] == claim_stamp then
            goto continue
          end

          if not already_sent_value(p_value, destination) then
            send_midi_param(channel.number, i, param, p_value, midi_channel, devices[channel.number].midi_device, nrpn_mode)
          end
        elseif not m_clock.channel_is_sliding(channel, i) then
          if value == off then
            goto continue
          end
          if any_claimed and claimed_addresses[midi_address(param, midi_channel)] == claim_stamp then
            goto continue
          end

          if not already_sent_value(value, destination) then
            send_midi_param(channel.number, i, param, value, midi_channel, devices[channel.number].midi_device, nrpn_mode)
          end
        end
      elseif param.type == "norns" and param.id == "nb_slew" then

        if step_trig_lock then
          if step_trig_lock == off then
            goto continue
          end
          device.player:set_slew(step_trig_lock)
        elseif value then
          device.player:set_slew(value)
        end
      elseif param.type == "norns" and param.id then
        if step_trig_lock then

          if step_trig_lock == off then
            goto continue
          end

          if not norns_param_state_handler.get_original_param_state(channel.number, i).value then
            norns_param_state_handler.set_original_param_state(channel.number, i, value, param.id)
          end

          if not m_clock.handoff_spread_lock(channel.number, i, step, step_trig_lock) then
            params:set(param.id, step_trig_lock)
          end
          if next_lock and (program.get_channel_param_slide(channel, i) or program.get_step_param_slide(channel, step, i)) then
            m_clock.execute_action_across_steps_by_pulses({
              channel_number = channel.number,
              trig_lock = i,
              start_step = step,
              end_step = next_lock.step,
              distance = next_lock.distance,
              start_value = step_trig_lock,
              end_value = next_lock.value,
              should_wrap = next_lock.should_wrap,
              func = function(value, last_value)
                if last_value ~= value then 
                  params:set(param.id, value)
                end
              end
            })
          end
        elseif program.step_has_trig(channel, step) and not m_clock.channel_is_sliding(channel, i) then
          if norns_param_state_handler.get_original_param_state(channel.number, i) and norns_param_state_handler.get_original_param_state(channel.number, i).value then 
            params:set(param.id, norns_param_state_handler.get_original_param_state(channel.number, i).value)
            norns_param_state_handler.clear_original_param_state(channel.number, i)
          end
        end
      end
    end

    ::continue::
  end
end


step.calculate_next_selected_song_pattern = song_transition.calculate_next_selected_song_pattern

function step.calculate_step_scale_number(c, s)
  local program_data = program.get()
  local channel = program.get_channel(program_data.selected_song_pattern, c)
  local channel_step_scale_number = program.get_step_scale_trig_lock(channel, s)
  local persistent_numbers = persistent_channel_step_scale_numbers

  if c == 17 then
    channel_step_scale_number = nil
    persistent_numbers[17] = nil
  end

  local current_step_17 = program.get_current_step_for_channel(17)
  local channel_17 = program.get_channel(program_data.selected_song_pattern, 17)
  local global_step_scale_number = program.get_step_scale_trig_lock(channel_17, current_step_17)
  local global_default_scale = program_data.default_scale

  local start_trig_c = fn.calc_grid_count(channel.start_trig[1], channel.start_trig[2])
  if s == start_trig_c then
    persistent_numbers[c] = nil
  end

  if c == 17 and current_step_17 == fn.calc_grid_count(channel_17.start_trig[1], channel_17.start_trig[2]) then
    persistent_global_step_scale_number = nil
  end

  -- Scale Precedence : channel_step_scale > global_step_scale > global_default_scale
  if channel_step_scale_number and channel_step_scale_number > 0 and program.get_scale(channel_step_scale_number).scale then
    persistent_numbers[c] = channel_step_scale_number
    return channel_step_scale_number
  end

  local persistent_channel_scale = persistent_numbers[c]
  if persistent_channel_scale and program.get_scale(persistent_channel_scale).scale then
    return persistent_channel_scale
  end

  if global_step_scale_number and global_step_scale_number > 0 then
    persistent_global_step_scale_number = global_step_scale_number
    return global_step_scale_number
  end

  if persistent_global_step_scale_number and persistent_global_step_scale_number > 0 then
    return persistent_global_step_scale_number
  end

  if global_default_scale and global_default_scale > 0 and program.get_scale(global_default_scale).scale then
    return global_default_scale
  end

  return 0
end

function step.manually_calculate_step_scale_number(c, step)
  local program_data = program.get()
  local channel = program.get_channel(program.get().selected_song_pattern, c)
  local clock_division_17 = m_clock.get_channel_division(17)
  local channel_division = m_clock.get_channel_division(c)
  
  -- Calculate the relative speed between the two sequencers
  local speed_ratio = channel_division / clock_division_17
  
  -- Calculate what step channel 17 would be on
  local global_scale_step

  if step == 1 then
    global_scale_step = 1
  elseif speed_ratio > 16 then
    global_scale_step = 1 
  else
    global_scale_step = math.ceil(step * speed_ratio)
  end
  
  local global_default_scale = program_data.default_scale      
  
  local global_step_scale_number = nil   
  for i = 1, global_scale_step do     
    global_step_scale_number = program.get_step_scale_trig_lock(program.get_channel(program.get().selected_song_pattern, 17), i) or global_step_scale_number   
  end    
  
  local channel_step_scale_number = nil   
  if c ~= 17 then     
    for i = 1, step do       
      channel_step_scale_number = program.get_step_scale_trig_lock(channel, i) or channel_step_scale_number     
    end   
  end    
  
  if channel_step_scale_number and channel_step_scale_number > 0 and program.get_scale(channel_step_scale_number).scale then     
    return channel_step_scale_number   
  elseif global_step_scale_number and global_step_scale_number > 0 then     
    return global_step_scale_number   
  elseif global_default_scale and global_default_scale > 0 and program.get_scale(global_default_scale).scale then     
    return global_default_scale   
  else     
    return 0   
  end 
end


-- The caller may already hold this channel; it is the same table this fetches.
function step.calculate_step_transpose(c, known_channel)
  local channel = known_channel or program.get_channel(program.get().selected_song_pattern, c)
  local current_scale_number = program.get_channel_step_scale_number(c)
  if not current_scale_number then
    current_scale_number = program.get_channel_step_scale_number(17)
  end
  local scale = program.get_scale(current_scale_number)
  local current_step = program.get_current_step_for_channel(c)
  local step_transpose = program.get_step_transpose_trig_lock(current_step)
  local global_transpose = program.get_transpose()
  local scale_transpose = scale.transpose or 0

  local transpose = 0
  local end_trig_1, end_trig_2 = channel.end_trig[1], channel.end_trig[2]
  local scale_channel_end_step = fn.calc_grid_count(end_trig_1, end_trig_2)
  
  if current_step and current_step % scale_channel_end_step == 1 then
    persistent_step_transpose = nil
  end

  if program.get_step_scale_trig_lock(channel, current_step) then
    persistent_step_transpose = nil
  end

  -- First determine base transpose from step/persistent/global
  if step_transpose then
    transpose = step_transpose
    persistent_step_transpose = step_transpose
  elseif persistent_step_transpose then
    transpose = persistent_step_transpose
  else
    transpose = global_transpose or 0
  end

  -- Add scale transpose to whatever base transpose was selected
  transpose = transpose + (scale_transpose or 0)

  return transpose
end



local function handle_arp(note_container, unprocessed_note_container, chord_notes, arp_division, chord_strum_pattern, chord_velocity_mod, chord_spread, chord_acceleration, mute_root, note_on_func, process_func, frozen_pitches, consume_harmony)
  local c = note_container.channel
  local channel = program.get_channel(program.get().selected_song_pattern, c)
  local release_ids = {}
  local note_dashboard_values = {chords = {}}
  local sequenced_chord_notes = build_arp_sequence(
    chord_notes,
    chord_strum_pattern,
    mute_root,
    unprocessed_note_container.note_value,
    unprocessed_note_container.octave_mod,
    unprocessed_note_container.transpose,
    unprocessed_note_container.random_shift
  )
  if not sequenced_chord_notes then
    m_clock.cancel_arp_onsets(c)
    if c == program.get().selected_channel then
      channel_edit_page_ui.set_note_dashboard_values(note_dashboard_values)
    end
    return
  end
  local total_notes = #sequenced_chord_notes
  local frozen_sequence
  if frozen_pitches then
    frozen_sequence = {}
    for index,descriptor in ipairs(sequenced_chord_notes) do
      frozen_sequence[index] = descriptor and frozen_pitches[descriptor.source_id] or false
    end
  end
  local initial = sequenced_chord_notes[1]
  if initial then
    local note
    if frozen_sequence~=nil then note=frozen_sequence[1]else
      note=process_func(initial.note_value,initial.octave_mod,initial.transpose,channel.step_scale_number)
    end
    if note then
      local release_id = play_arp_note(note, note_container, note_container.velocity, arp_division, note_on_func)
      if release_id and consume_harmony then consume_harmony() end
      if release_id then table.insert(release_ids, release_id) end
    end
    note_dashboard_values.note = note
    note_dashboard_values.velocity = note_container.velocity
    note_dashboard_values.length = arp_division
  end
  arp_note[c] = total_notes == 1 and 1 or 2
  local number_of_executions = 1
  if c == program.get().selected_channel then
    channel_edit_page_ui.set_note_dashboard_values(note_dashboard_values)
  end
  m_clock.new_arp_sprocket(c, arp_division, chord_spread, chord_acceleration, note_container.length, function(div, onset_offset)
    local velocity = fn.constrain(0, 127, note_container.velocity + ((chord_velocity_mod or 0) * number_of_executions))
    local note_to_play = sequenced_chord_notes[arp_note[c]]
    -- Every slot consumes time and acceleration, including trailing rests.
    if note_to_play then
      local note
      if frozen_sequence~=nil then note=frozen_sequence[arp_note[c]]else
        note=process_func(note_to_play.note_value,note_to_play.octave_mod,note_to_play.transpose,channel.step_scale_number)
      end
      if note then
        local release_id=play_arp_note(note,note_container,velocity,arp_division,note_on_func,onset_offset)
        if release_id and consume_harmony then consume_harmony()end
        if release_id then table.insert(release_ids,release_id)end
      end
      table.insert(note_dashboard_values.chords, note and fn_constrain(0, 127, note)) -- as sent (dashboard-chord-slots)
    end
    arp_note[c] = arp_note[c] % total_notes + 1
    number_of_executions = number_of_executions + 1
    if c == program.get().selected_channel then
      channel_edit_page_ui.set_note_dashboard_values(note_dashboard_values)
    end
  end, release_ids)
end

local function harmony_revision(prefix, channel, unprocessed, sources)
  local scale = program.get_scale(channel.step_scale_number)
  local parts = {prefix, channel.step_scale_number, scale and scale.version or 0,
    unprocessed.octave_mod, unprocessed.transpose, unprocessed.do_pentatonic and 1 or 0}
  for _, source in ipairs(sources or {}) do
    parts[#parts + 1], parts[#parts + 1] = source.id, source.pitch
  end
  return table.concat(parts, "|")
end

-- Ensemble solving is a pulse-level operation. Freeze each participating
-- group's source material before any member callback can mutate playback state.
local active_group_frames

function step.prepare_harmony_group_frames(deferred, count)
  local prepared = setmetatable({}, {__mode="k"})
  active_group_frames = prepared
  for index = 1, count do
    local sprocket = deferred[index]
    local channel = sprocket and sprocket.pending_channel
    local song_number = sprocket and sprocket.pending_song_pattern
    if channel and song_number then
      local song = program.get_song_pattern(song_number)
      local config = harmony_config_state.effective_channel(song, channel.number,
        channel.voicing or harmony_config.new_channel())
      local group_id = config and config.mode == "ensemble" and config.group_id
      prepared[song] = prepared[song] or {}
      if group_id and not prepared[song][group_id] then
        local song_config = harmony_config_state.effective_song(song,
          song.voicing or {schema_version=1, groups={}})
        local group = song_config and song_config.groups[group_id]
        if group and group.enabled then
          local source_scale = group.source.kind == "scale_slot" and group.source.scale_slot or
            (program.get_channel_step_scale_number(17) or program.get().default_scale or 1)
          local global_channel = program.get_channel(song_number, 17)
          local transpose = step.calculate_step_transpose(17, global_channel)
          local context = harmony_context.group_material(group, source_scale, transpose)
          prepared[song][group_id] = harmony_state.prepare_group(song, group_id,
            context.revision, context.material, group)
        end
      end
    end
  end
end

function step.finish_harmony_group_frames()
  active_group_frames = nil
end

local function prepare_harmony(current_step, note_container, unprocessed, channel,
                               chord_notes, process_func)
  local song = program.get_selected_song_pattern()
  local config = harmony_config_state.effective_channel(song, channel.number,
    channel.voicing or harmony_config.new_channel())
  if not config or config.mode == "off" then return nil end
  local legacy = {root=note_container.note}
  local sources = {{id="root", pitch=note_container.note}}
  for index = 1, 4 do
    local offset = chord_notes and chord_notes[index]
    if offset and offset ~= 0 then
      local pitch = process_func(unprocessed.note_value + offset + unprocessed.random_shift,
        unprocessed.octave_mod, unprocessed.transpose, channel.step_scale_number)
      if pitch then
        legacy["chord" .. index] = pitch
        sources[#sources + 1] = {id="chord" .. index, pitch=pitch}
      end
    end
  end

  local frame, pitches, consume
  if config.mode == "revoice" then
    local material = {}
    for _, source in ipairs(sources) do
      material[#material + 1] = {id=source.id, pc=source.pitch % 12, required=true}
    end
    local pins = unprocessed.absolute_pitch and config.absolute_pitch_policy=="pin"and{root=note_container.note}or nil
    frame = harmony_state.prepare_revoice(song, channel.number,
      harmony_revision("revoice", channel, unprocessed, sources), material, config, pins)
    if frame.status == "ok" then pitches = frame.source_pitches end
    consume = function() harmony_state.consume_revoice(song, channel.number, frame) end
  elseif config.mode == "pattern" then
    if chord_notes or unprocessed.pattern_bypass then
      return {pitches=legacy, status=unprocessed.pattern_bypass or "chord_mask"}
    end
    local resolved = {}
    for _, raw in ipairs(channel.working_pattern.note_values or {}) do
      if resolved[raw] == nil then
        resolved[raw] = quantiser.process(raw, unprocessed.octave_mod, unprocessed.transpose,
          channel.step_scale_number, unprocessed.do_pentatonic)
      end
    end
    -- The current event already passed masks, fixed notes and Foundation's
    -- structural target.  Non-bypassed structural output is authoritative for
    -- this raw identity and must not be reconstructed from upstream inputs.
    resolved[unprocessed.note_value]=note_container.note
    local resolved_sources={};for raw,pitch in pairs(resolved)do resolved_sources[#resolved_sources+1]={id=tostring(raw),pitch=pitch}end
    table.sort(resolved_sources,function(a,b)return a.id<b.id end)
    local active_merge=musical_merge_state.effective(song,channel.number,
      channel.musical_merge or musical_merge_config.new()).config
    local binding = pattern_harmony.binding_key(channel,active_merge)
    frame = pattern_harmony.prepare(song, channel.number,
      harmony_revision("pattern", channel, unprocessed,resolved_sources), binding, resolved, config)
    pitches = {root=pattern_harmony.pitch_for(frame, unprocessed.note_value, note_container.note)}
    consume = function() harmony_state.consume_revoice(song, channel.number, frame) end
  elseif config.mode == "ensemble" then
    local has_local_chord=false;for _,offset in ipairs(chord_notes or{})do if offset and offset~=0 then has_local_chord=true break end end
    if has_local_chord or unprocessed.pattern_bypass or unprocessed.ensemble_bypass then
      return {pitches=legacy,status=unprocessed.pattern_bypass or unprocessed.ensemble_bypass or"chord_mask"}
    end
    local active_song_voicing = harmony_config_state.effective_song(song,
      song.voicing or {schema_version=1, groups={}})
    local groups = active_song_voicing and active_song_voicing.groups or {}
    local group = groups[config.group_id]
    if not group or not group.enabled then
      return {pitches=config.fallback=="legacy"and legacy or{},status="group_missing"}
    end
    local source_scale = group.source.kind == "scale_slot" and group.source.scale_slot or
      (program.get_channel_step_scale_number(17) or program.get().default_scale or 1)
    if source_scale ~= channel.step_scale_number then
      return {pitches=legacy,status="local_scale_bypass"}
    end
    local global_channel=program.get_channel(program.get().selected_song_pattern,17)
    local global_transpose=step.calculate_step_transpose(17,global_channel)
    local context = harmony_context.group_material(group, source_scale, global_transpose)
    frame = active_group_frames and active_group_frames[song] and
      active_group_frames[song][config.group_id] or harmony_state.prepare_group(song,
        config.group_id, context.revision, context.material, group)
    local role
    for _, member in ipairs(group.members) do
      if member.channel == channel.number then role = member.role break end
    end
    if frame.status == "ok" and role then pitches = {root=frame.role_pitches[role]} end
    if not pitches and group.fallback=="legacy"then pitches=legacy end
    consume = function() harmony_state.consume_group(song, config.group_id, frame) end
  end
  if not pitches and config.fallback == "legacy" then pitches = legacy end
  local consumed = false
  return {
    pitches=pitches or {}, frame=frame, status=frame and frame.status or "no_solution",
    consume=function()
      if not consumed and frame and frame.status == "ok" then consumed=true consume() end
    end
  }
end

local function handle_note(device, current_step, note_container, unprocessed_note_container, note_on_func, stock, channel)
  local c = note_container.channel
  local event_song = program.get_selected_song_pattern()
  
  -- Check if root note should be muted
  local mute_root = stock("mute_root_note") == 1

  -- Cache frequently accessed values
  local step_chord_masks = channel.step_chord_masks[current_step]
  local chord_one = step_chord_masks and step_chord_masks[1] or channel.chord_one_mask
  local chord_two = step_chord_masks and step_chord_masks[2] or channel.chord_two_mask
  local chord_three = step_chord_masks and step_chord_masks[3] or channel.chord_three_mask
  local chord_four = step_chord_masks and step_chord_masks[4] or channel.chord_four_mask
  -- A chord slot sounds only with a non-zero note (see strum_descriptor).
  local has_chord_notes = (chord_one and chord_one ~= 0) or (chord_two and chord_two ~= 0) or
    (chord_three and chord_three ~= 0) or (chord_four and chord_four ~= 0)
  
  -- Cache params early
  local chord_strum_pattern = stock("chord_strum_pattern")
  local chord_arp = note_divisions[stock("chord_arp")]
  local arp_division = chord_arp and chord_arp.value
  -- Strum timing and chord velocity only shape arps, sounding chord notes and a
  -- delayed root; a plain single note never reads them.
  local chord_division, chord_velocity_mod, chord_spread, chord_acceleration = nil, nil, 0, 0
  if arp_division or has_chord_notes or
      (not mute_root and (chord_strum_pattern == 2 or chord_strum_pattern == 4)) then
    local chord_strum = note_divisions[stock("chord_strum")]
    chord_division = chord_strum and chord_strum.value
    chord_velocity_mod = stock("chord_velocity_modifier")
    chord_spread = stock("chord_spread") or 0
    chord_acceleration = stock("chord_acceleration") or 0
  end
  
  -- Cache note processing values
  local note_value = unprocessed_note_container.note_value
  local octave_mod = unprocessed_note_container.octave_mod
  local transpose = unprocessed_note_container.transpose
  local random_shift = unprocessed_note_container.random_shift
  local step_scale_number = channel.step_scale_number
  local velocity = note_container.velocity
  local length = note_container.length

  local process_func
  if unprocessed_note_container.is_mask then
    process_func = function (note_number, octave_mod, transpose, scale_number) 
      return quantiser.process_with_mask_params(note_number, octave_mod, transpose, scale_number, unprocessed_note_container.fully_quantise_mask) 
    end
  else
    process_func = quantiser.process
  end

  if chord_spread ~= 0 then
    chord_spread = divisions.note_division_values[chord_spread]
  end

  -- Plain single notes need no chord table or chord dashboard values.
  local chord_notes = (arp_division or has_chord_notes) and {chord_one, chord_two, chord_three, chord_four} or nil
  local harmony = prepare_harmony(current_step, note_container, unprocessed_note_container,
    channel, chord_notes, process_func)
  local harmony_pitches = harmony and harmony.pitches
  local consume_harmony = harmony and harmony.consume
  local planned_root = harmony_pitches and harmony_pitches.root
  if harmony_pitches == nil then planned_root = note_container.note end
  local inspection_context={
    step=current_step,
    source=unprocessed_note_container.note_value,
    merge=unprocessed_note_container.note_value,
    scale=note_container.note,
    harmony=planned_root,
    output=planned_root,
    status=harmony and harmony.status or "off",
    structural_status=unprocessed_note_container.structural_status,
    bypass=harmony and harmony.status~="ok"and harmony.status or nil
  }
  harmony_inspection.plan(event_song, c, inspection_context)
  local emit_note_on = note_on_func
  note_on_func = function(pitch, velocity, midi_channel, midi_device)
    local accepted = emit_note_on(pitch, velocity, midi_channel, midi_device)
    if accepted == false then return false end
    harmony_inspection.scheduled(event_song, c, pitch, "voice",inspection_context)
    harmony_inspection.emitted(event_song, c, pitch, "voice",inspection_context)
    return true
  end

  if arp_division then
    handle_arp(note_container, unprocessed_note_container, chord_notes, arp_division, 
              chord_strum_pattern, chord_velocity_mod, chord_spread, chord_acceleration, mute_root,
              note_on_func, process_func, harmony_pitches, consume_harmony)
    return
  end

  -- The dashboard table is shared with the chord callbacks below; build it when
  -- the root sounds now or a chord can sound. Nothing reads it for an unshown
  -- channel that sounds no chord, so that note builds none.
  local note_dashboard_values

  local selected_channel = program.get().selected_channel
  if play_strum_root_now(chord_strum_pattern, mute_root) then
    local root_pitch = harmony_pitches and harmony_pitches.root
    if harmony_pitches == nil then root_pitch = note_container.note end
    if root_pitch then
      local accepted = play_note(root_pitch, note_container, note_container.velocity, note_container.length, note_on_func)
      if accepted and consume_harmony then consume_harmony() end
    end
    if c == selected_channel or has_chord_notes then
      note_dashboard_values = {
        note = root_pitch,
        velocity = note_container.velocity,
        length = note_container.length
      }
      if c == selected_channel then
        channel_edit_page_ui.set_note_dashboard_values(note_dashboard_values)
      end
    end
  end


  local chord_note_dashboard_values
  -- The latest voice this strum schedules, announced once below so the lock
  -- lookahead keeps the next step's values behind it.
  local latest_voice

  for i = 1, has_chord_notes and 4 or 0 do
    local chord_number, delay, delay_multiplier = resolve_strum_chord(
      i,
      chord_notes,
      chord_strum_pattern,
      chord_division,
      chord_spread,
      chord_acceleration
    )
    if chord_number then
      chord_note_dashboard_values = chord_note_dashboard_values or {chords = {}}
      if latest_voice == nil or delay > latest_voice then latest_voice = delay end
      m_clock.delay_action(
        c,
        delay,
        false,
        function()
          local processed_chord_note = harmony_pitches and harmony_pitches["chord" .. chord_number]
          if not harmony_pitches then
            local note_value = unprocessed_note_container.note_value + chord_notes[chord_number] + random_shift
            processed_chord_note = process_func(note_value, unprocessed_note_container.octave_mod,
              unprocessed_note_container.transpose, channel.step_scale_number)
          end

          local velocity = fn.constrain(0, 127, note_container.velocity + ((chord_velocity_mod or 0) * delay_multiplier))

          if processed_chord_note then
            local accepted = play_note(processed_chord_note, note_container, velocity, note_container.length, note_on_func)
            if accepted and consume_harmony then consume_harmony() end

            if note_dashboard_values and not note_dashboard_values.chords then
              note_dashboard_values.chords = {}
            end
            -- Show the voice as sent: MIDI clamps it to 0..127 (bugs.json dashboard-chord-slots).
            chord_note_dashboard_values.chords[chord_number] = fn_constrain(0, 127, processed_chord_note)

            if c == program.get().selected_channel then
              channel_edit_page_ui.set_note_dashboard_values(chord_note_dashboard_values)
            end
          end
        end
      )

    end

  end

  local delayed_root_delay = resolve_strum_root_later(
    chord_strum_pattern,
    mute_root,
    chord_division,
    chord_spread,
    chord_acceleration
  )
  if delayed_root_delay ~= nil then
    if latest_voice == nil or delayed_root_delay > latest_voice then latest_voice = delayed_root_delay end
    m_clock.delay_action(
      c,
      delayed_root_delay,
      false,
      function()

        local processed_note
        if harmony_pitches ~= nil then
          processed_note = harmony_pitches.root
        else
          processed_note = process_func(unprocessed_note_container.note_value + random_shift,
            unprocessed_note_container.octave_mod, unprocessed_note_container.transpose,
            channel.step_scale_number)
        end

        if processed_note then
          local velocity = fn.constrain(0, 127, note_container.velocity + ((chord_velocity_mod or 0) * 4))
          local accepted = play_note(processed_note, note_container, velocity, note_container.length, note_on_func)
          if accepted and consume_harmony then consume_harmony() end

          if c == program.get().selected_channel then
            channel_edit_page_ui.set_note_dashboard_values({
              note = processed_note,
              velocity = velocity,
              length = note_container.length
            })
          end
        end
      end
    )
  end

  if latest_voice and latest_voice > 0 and m_clock.hold_voice_onset then
    m_clock.hold_voice_onset(c, latest_voice)
  end
end

-- The stock kinds every sounding step reads, whatever its chord settings.
local note_stock_kinds = {
  "trig_probability", "bipolar_random_note", "twos_random_note", "random_velocity",
  "quantised_fixed_note", "fixed_note", "mute_root_note", "chord_strum_pattern", "chord_arp",
}

-- Reading a step's stock parameters is most of what a note costs before it is
-- sent, and a mod such as matrix makes each read dearer. The clock resolves
-- them while it sends the step's parameter locks, so the step's notes can then
-- leave back to back. Pass the result to step.handle for the same channel and
-- step in the same clock pulse, so nothing read can change in between; the
-- next prepare for the channel reuses it. c is the channel number, which is
-- also the one handle reads the slots for.
-- A fixed note with no stock value set falls back to the channel's own slot;
-- remember that read, with false standing for a slot that holds nothing.
local function prepare_note_slot(prepared, c, kind, slot)
  prepared.slots[slot] = nil
  local value, read = prepared.stock(kind)
  if value or read ~= nil then return end
  local slot_value = read_stock_assigned(param_slots.control_id(c, slot))
  if slot_value == nil then slot_value = false end
  prepared.slots[slot] = slot_value
end

-- One prepared note per channel, reused on every step.
local prepared_notes = {}

function step.prepare_note(c, current_step)
  local channel = program.get_channel(program.get().selected_song_pattern, c)
  local prepared = prepared_notes[c]
  if not prepared then
    local resolver = stock_parameter.new_remembering_resolver(read_stock_step_lock, read_stock_assigned,
      read_stock_fallback)
    prepared = {resolver = resolver, stock = resolver.stock, slots = {}}
    prepared_notes[c] = prepared
  end
  prepared.resolver.reset(channel.trig_lock_params, channel, current_step)
  local stock = prepared.stock
  for i = 1, #note_stock_kinds do stock(note_stock_kinds[i]) end
  prepare_note_slot(prepared, c, "quantised_fixed_note", param_slots.QUANTISED_FIXED_NOTE_SLOT)
  prepare_note_slot(prepared, c, "fixed_note", param_slots.FIXED_NOTE_SLOT)
  return prepared
end

-- A slot value prepare_note already read, or a read now when it did not.
local function read_note_slot(prepared, c, slot)
  local value = prepared and prepared.slots[slot]
  if value == false then return nil end
  if value ~= nil then return value end
  return read_stock_assigned(param_slots.control_id(c, slot))
end

function step.handle(c, current_step, prepared)
  local program_data = program.get()
  local channel = program.get_channel(program.get().selected_song_pattern, c)
  local working_pattern = channel.working_pattern
  local devices = program_data.devices[channel.number]

  local note_value = working_pattern.note_values[current_step]
  local note_mask_value = working_pattern.note_mask_values[current_step]
  local velocity_value = working_pattern.velocity_values[current_step]
  local length_value = working_pattern.lengths[current_step]
  local midi_channel = devices.midi_channel
  local midi_device = devices.midi_device
  local octave_mod = channel.octave

  local step_octave_trig_lock = program.get_step_octave_trig_lock(channel, current_step)
  if step_octave_trig_lock then
    octave_mod = step_octave_trig_lock
  end

  if c == 17 and current_step == fn.calc_grid_count(program.get_channel(program.get().selected_song_pattern, 17).start_trig[1], program.get_channel(program.get().selected_song_pattern, 17).start_trig[2]) then
    persistent_global_step_scale_number = nil
  end

  -- One assignment scan answers every stock kind this step reads.
  local stock = prepared and prepared.stock or stock_parameter.resolver(channel.trig_lock_params,
    read_stock_step_lock, read_stock_assigned, read_stock_fallback, channel, current_step)
  local trig_probability = stock("trig_probability")
  local trig_prob = (trig_probability == -1) and 100 or (trig_probability or 100)

  local random_outcome = true
  if trig_prob < 100 then
    random_outcome = random(0, 99) < trig_prob
  end

  if random_outcome then
    if fn.param_value("quantiser_trig_lock_hold") == 1 then
      persistent_channel_step_scale_numbers[c] = nil
    end
  end

  program.set_channel_step_scale_number(c, step.calculate_step_scale_number(c, current_step))

  local transpose = step.calculate_step_transpose(c, channel)

  if random_outcome then

    local foundation = working_pattern.foundation
    local foundation_role = foundation and foundation.roles and foundation.roles[current_step]
    local merge_config = foundation and foundation.config
    if foundation_role == "anchor" and merge_config and merge_config.keep_anchor_pitch and
      foundation.anchor_notes and foundation.anchor_notes[current_step] ~= nil then
      note_value = foundation.anchor_notes[current_step]
    end

    local random_shift = fn.transform_random_value(stock("bipolar_random_note") or 0) +
                         fn.transform_twos_random_value(stock("twos_random_note") or 0)
                  
    local structural_target = foundation_role == "addition" and merge_config and merge_config.target and
      merge_config.target.kind ~= "legacy"
    local do_pentatonic = fn.param_value("all_scales_lock_to_pentatonic") == 2 or 
                         (not structural_target and fn.param_value("merged_lock_to_pentatonic") == 2 and working_pattern.merged_notes[current_step]) or
                         (fn.param_value("random_lock_to_pentatonic") == 2 and random_shift ~= 0)            

    -- Only note masks read the fully-quantise setting (see pitch_resolution).
    local fully_quantise_mask = nil
    if note_mask_value and note_mask_value > -1 then
      fully_quantise_mask = stock("fully_quantise_mask")
    end
    local note, relative_note_mask_value, octave_mod_offset, is_mask
    note, relative_note_mask_value, octave_mod_offset, is_mask, fully_quantise_mask = resolve_pitch(
      note_value,
      note_mask_value,
      octave_mod,
      transpose,
      channel.step_scale_number,
      random_shift,
      do_pentatonic,
      fully_quantise_mask
    )

    local velocity_random_shift = fn.transform_random_value(stock("random_velocity") or 0)
    velocity_value = fn.constrain(0, 127, velocity_value + velocity_random_shift)

    -- An unset stock value falls back to the channel parameter, which the
    -- resolver may already have read; reuse that read when it did.
    local quantised_fixed_note, quantised_fixed_note_read = stock("quantised_fixed_note")

    if not quantised_fixed_note then
      quantised_fixed_note = quantised_fixed_note_read
      if quantised_fixed_note == nil then
        quantised_fixed_note = read_note_slot(prepared, channel.number, param_slots.QUANTISED_FIXED_NOTE_SLOT)
      end
    end

    local used_quantised_fixed = quantised_fixed_note and quantised_fixed_note > -1 and quantised_fixed_note <= 127
    if used_quantised_fixed then
      note = quantiser.snap_to_scale(quantised_fixed_note, channel.step_scale_number, nil, true)
    end

    local fixed_note, fixed_note_read = stock("fixed_note")

    if not fixed_note then
      fixed_note = fixed_note_read
      if fixed_note == nil then
        fixed_note = read_note_slot(prepared, channel.number, param_slots.FIXED_NOTE_SLOT)
      end
    end

    local used_fixed = fixed_note and fixed_note > -1 and fixed_note <= 127
    if used_fixed then
      note = fixed_note
    end

    local structural_status
    if merge_config and foundation_role == "addition" then
      local bypass = is_mask and "note_mask" or random_shift ~= 0 and "random" or
        used_quantised_fixed and "quantised_fixed" or used_fixed and "fixed" or nil
      local chord_material
      if merge_config.target and merge_config.target.kind == "chord" then
        local song=program.get_selected_song_pattern()
        local active_song_voicing=harmony_config_state.effective_song(song,
          song.voicing or {schema_version=1,groups={}})
        local group = active_song_voicing and active_song_voicing.groups[merge_config.target.group_id]
        if group and group.enabled then
          local source_scale=group.source.kind=="scale_slot"and group.source.scale_slot or
            (program.get_channel_step_scale_number(17)or program.get().default_scale or 1)
          chord_material = harmony_context.group_material(group,source_scale,transpose).pitch_classes
        end
      end
      note, structural_status = merge_pitch_target.resolve(note, {
        eligible=true,
        bypass=bypass,
        config=merge_config.target,
        scale_pitch_classes=harmony_context.scale_pitch_classes(channel.step_scale_number, transpose),
        chord_material=chord_material
      })
    end


    local device = device_map.get_device(devices.device_map)
    if device.id == "none" then
      harmony_inspection.plan(program.get_selected_song_pattern(),c,{step=current_step,source=note_value,status="missing_output",bypass="missing_output"})
      return
    end

    if not channel.mute and note then
      local note_container = {
        note = note,
        velocity = velocity_value,
        length = length_value,
        midi_channel = midi_channel,
        midi_device = midi_device,
        steps_remaining = length_value,
        player = device.player or m_midi,
        lead_time_ms = m_midi.get_lead_time and m_midi.get_lead_time() or 0,
        channel = c
      }

      handle_note(
        device,
        current_step,
        note_container,
        {note_value = relative_note_mask_value or note_value, octave_mod = octave_mod + octave_mod_offset,
          transpose = transpose, random_shift = random_shift, is_mask = is_mask,
          fully_quantise_mask = fully_quantise_mask, do_pentatonic = do_pentatonic,
          structural_status = structural_status,
          pattern_bypass = is_mask and "note_mask" or random_shift ~= 0 and "random" or
            used_quantised_fixed and "quantised_fixed" or used_fixed and "fixed" or nil,
          ensemble_bypass = octave_mod ~= 0 and "local_octave" or nil,
          absolute_pitch = is_mask or used_quantised_fixed or used_fixed},
        function(chord_note, velocity, midi_channel, midi_device)
          if device.player then
            device.player:note_on(chord_note, (127 > 1) and ((velocity - 1) / 126) or 0)
            return true
          elseif m_midi then
            return m_midi:note_on(chord_note, velocity, midi_channel, midi_device, note_container.lead_time_ms)
          end
          return false
        end,
        stock,
        channel
      )
    elseif channel.mute or not note then
      harmony_inspection.plan(program.get_selected_song_pattern(),c,{step=current_step,source=note_value,
        status=channel.mute and"muted"or"rest",bypass=channel.mute and"muted"or"rest"})
    end
  end

end

function step.process_global_step_scale_trig_lock(current_step)
  program.set_global_step_scale_number(step.calculate_step_scale_number(17, current_step))
end

step.process_elektron_program_change = song_transition.process_elektron_program_change

step.queue_next_song_pattern = song_transition.queue_next_song_pattern

step.queue_for_pattern_change = song_transition.queue_for_pattern_change

step.at_end_of_current_song_pattern = song_transition.at_end_of_current_song_pattern

step.process_song_song_patterns = song_transition.process_song_song_patterns

function step.sinfonian_sync(s)
  local global_step_scale_number = program.get_step_scale_trig_lock(program.get_channel(program.get().selected_song_pattern, 17), step)
  local global_default_scale = program.get().default_scale

  local sinfonion_scale_number = 1

  if global_step_scale_number and global_step_scale_number > 0 then
    sinfonion_scale_number = global_step_scale_number
  elseif persistent_global_step_scale_number and persistent_global_step_scale_number > 0 then
    sinfonion_scale_number = persistent_global_step_scale_number
  elseif global_default_scale and global_default_scale > 0 and program.get_scale(global_default_scale).scale then
    sinfonion_scale_number = global_default_scale
  end

  local scale_container = program.get_scale(sinfonion_scale_number)
  local transpose = step.calculate_step_transpose(17)
  local degree = quantiser.get_scales()[scale_container.number].sinf_degrees[scale_container.chord]
  local root = scale_container.root_note + quantiser.get_scales()[scale_container.number].sinf_root_mod
  local sinf_mode = quantiser.get_scales()[scale_container.number].sinf_mode

  -- This is a hack to get around the "feature" of the sinfonion where the fifth degree of the minor key has a flattened note
  if sinf_mode == 4 and degree == 7 then
    root = root + 3
    degree = 4
    sinf_mode = 3
  end

  if scale_container and scale_container.root_note then
    sinfonion.set_root_note(root)
    sinfonion.set_degree_nr(degree)
    sinfonion.set_mode_nr(sinf_mode)
    sinfonion.set_transposition(transpose)

  -- Could do something with these later
  -- sinfonion.set_clock(0)
  -- sinfonion.set_beat(0)
  -- sinfonion.set_step(0)
  -- sinfonion.set_reset(0)
  -- sinfonion.set_chaotic_detune(0)
  -- sinfonion.set_harmonic_shift(0)
  end
end


step.queue_switch_to_next_song_pattern_func = song_transition.queue_switch_to_next_song_pattern_func

step.queue_switch_to_next_song_pattern_blink_cancel_func = song_transition.queue_switch_to_next_song_pattern_blink_cancel_func

step.execute_blink_cancel_func = song_transition.execute_blink_cancel_func

function step.reset()
  program.get().global_step_accumulator = 0
  persistent_global_step_scale_number = nil
  persistent_channel_step_scale_numbers = {
    nil,
    nil,
    nil,
    nil,
    nil,
    nil,
    nil,
    nil,
    nil,
    nil,
    nil,
    nil,
    nil,
    nil,
    nil,
    nil
  }
  arp_note = {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0}
  persistent_step_transpose = nil
  -- Stop discards song commands queued for a boundary that was never reached
  -- (arbitrated 2026-09-11, discard-on-stop); the next Play follows song mode.
  song_transition.clear_pending()
  if song_edit_page and song_edit_page.refresh_faders then song_edit_page.refresh_faders() end -- show the length that will play
  step.execute_blink_cancel_func()
  local c = program.get_selected_channel().number
  program.set_channel_step_scale_number(
    c, step.calculate_step_scale_number(c, 1)
  )
  norns_param_state_handler.flush_norns_original_param_trig_lock_store()
end

function step.reset_pattern()
  for i = 1, 17 do
    program.set_current_step_for_channel(i, 99)
    program.get().global_step_accumulator = 0
  end

end

return step
