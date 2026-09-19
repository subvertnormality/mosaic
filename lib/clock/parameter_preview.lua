-- Pure MIDI parameter preview shared by playback and future lock lookahead.
--
-- This is the read-only half of step.process_params: given a read-only view of
-- one channel at one step, it reports which MIDI values that step would send and
-- why the others would not. It performs no output, claims no shared state,
-- consumes no RNG or conditions, touches neither the recording nor the resend
-- cache, and neither starts nor cancels a slide. A slide is described by its
-- trajectory endpoints rather than expanded into samples, so a preview costs the
-- same whatever the slide length.
--
-- The view supplies reads only. Every side effect that process_params performs is
-- absent from it by construction, so a preview cannot take one by accident.
local preview = {}

-- Stock kinds resolved by step handling rather than sent as parameter locks.
-- step.lua reads this table so playback and preview cannot disagree. It is held
-- as a local as well, because the eligibility test runs for every slot of every
-- eligible step and playback reached it through an upvalue before the split.
local skipped_lock_params = {
  trig_probability = true,
  quantised_fixed_note = true,
  bipolar_random_note = true,
  twos_random_note = true,
  random_velocity = true,
  chord_strum = true,
  chord_arp = true,
  chord_velocity_modifier = true,
  chord_spread = true,
  chord_acceleration = true,
  chord_strum_pattern = true,
  fixed_note = true,
  mute_root_note = true,
  fully_quantise_mask = true
}

preview.skipped_lock_params = skipped_lock_params

function preview.should_process_param(param)
  if not param then return false end
  return not skipped_lock_params[param.id]
end

-- Two slots can address one device parameter. The address identifies where a
-- value lands, so a claim by a locked or sliding slot suppresses another slot's
-- assigned value for the same address. The MIDI write path names its writes
-- with the same numbers, so what it wrote and what a slot claims compare equal.
function preview.cc_address(midi_channel, cc_msb)
  return midi_channel * 2 * 16384 + cc_msb
end

function preview.nrpn_address(midi_channel, nrpn_msb, nrpn_lsb)
  return (midi_channel * 2 + 1) * 16384 + nrpn_msb * 128 + nrpn_lsb
end

function preview.midi_address(param, midi_channel)
  if param.nrpn_min_value and param.nrpn_max_value and param.nrpn_lsb and param.nrpn_msb then
    return preview.nrpn_address(midi_channel, param.nrpn_msb, param.nrpn_lsb)
  elseif param.cc_min_value and param.cc_max_value and param.cc_msb then
    return preview.cc_address(midi_channel, param.cc_msb)
  end
end

-- One physical destination: an address on a port. The receiver behind it holds
-- one value, whichever track or control wrote it. An address is below 2^20, so
-- the port index above it keeps the key a plain integer with no string built
-- per write.
function preview.destination(midi_device, address)
  if address == nil then return nil end
  return (tonumber(midi_device) or 0) * 1048576 + address
end

local function is_midi_slot(param)
  return param.type == "midi" and (param.cc_msb or param.nrpn_msb)
end

-- Mirrors claim_addresses: a slot that is locked away from Off, or sliding,
-- claims its address before any slot reports a value.
local function claimed_addresses(view, step)
  local claims, any = {}, false
  for slot, param in ipairs(view.params) do
    if param.param_id and param.type == "midi" then
      local lock_value = view.step_lock(slot, step)
      local off = param.off_value == nil and -1 or param.off_value
      if (lock_value ~= nil and lock_value ~= off) or view.is_sliding(slot) then
        local address = preview.midi_address(param, param.channel or view.midi_channel)
        if address then
          claims[address] = true
          any = true
        end
      end
    end
  end
  return claims, any
end

local function bundle_for(view, step, slot, param, claims, any_claimed)
  local off = param.off_value == nil and -1 or param.off_value
  local midi_channel = param.channel or view.midi_channel
  local address = preview.midi_address(param, midi_channel)
  local bundle = {slot = slot, param = param, step = step, channel = view.channel,
                  midi_channel = midi_channel, midi_device = view.midi_device,
                  address = address, destination = preview.destination(view.midi_device, address),
                  send = false}
  if param.nrpn_msb ~= nil then bundle.nrpn_mode = view.nrpn_mode(param) end

  -- A dirty recording lock owns the slot on the selected channel; playback does
  -- not speak over the value the player is recording.
  if view.recording_selected and view.recording_dirty(slot) then
    bundle.reason = "recording-dirty"
    return bundle
  end

  local step_lock = view.step_lock(slot, step)
  local assigned
  if step_lock == nil then assigned = view.assigned(param.param_id) end

  if step_lock ~= nil then
    bundle.kind, bundle.value = "lock", step_lock
    if step_lock == off then
      bundle.reason = "off"
      return bundle
    end
    -- A running slide owns this slot's wire until its destination step. Sending
    -- the destination early would land it before the samples still gliding
    -- toward it, so the receiver would jump to the target and then back. The
    -- lock leaves at its own step instead, where the handoff gives it one write.
    if view.is_sliding(slot) then
      bundle.reason = "sliding"
    elseif view.would_handoff(slot, step, step_lock) then
      -- A slide whose explicit destination is this lock consumes it. The
      -- predicate only reports that; retiring the slide stays with playback.
      bundle.reason = "handoff"
    else
      bundle.send = true
    end
    -- The trajectory is attached whether or not the lock itself is sent, because
    -- the handoff retires the old slide and this lock still starts the next one.
    -- The slide flags are tested first: they are cheap, and a slot that is not
    -- sliding never needs the search for its next lock.
    if view.channel_slide(slot) or view.step_slide(slot, step) then
      local next_lock = view.next_lock(slot, step, off)
      if next_lock then
        bundle.slide = {start_step = step, end_step = next_lock.step, distance = next_lock.distance,
                        start_value = step_lock, end_value = next_lock.value,
                        should_wrap = next_lock.should_wrap}
      end
    end
  else
    bundle.kind, bundle.value = "assigned", assigned
    if view.is_sliding(slot) then
      bundle.reason = "sliding"
      return bundle
    end
    if assigned == off then
      bundle.reason = "off"
      return bundle
    end
    if any_claimed and address and claims[address] then
      bundle.reason = "claimed"
      return bundle
    end
    bundle.send = true
  end

  -- The resend cache is consulted last, exactly where send_midi_param consults
  -- it, so a value suppressed earlier never counts as sent. Reading it here
  -- cannot commit it; committing belongs to the send.
  if bundle.send and not view.resend_unchanged and view.last_sent(slot) == bundle.value then
    bundle.send = false
    bundle.reason = "unchanged"
  end
  return bundle
end

-- Report every eligible MIDI slot for this step. Order follows slot order, which
-- is the order playback would send them in.
function preview.midi_bundles(view, step)
  local bundles = {}
  if view.mute then return bundles end
  local claims, any_claimed = claimed_addresses(view, step)
  for slot, param in ipairs(view.params) do
    if param.param_id and preview.should_process_param(param) and is_midi_slot(param) then
      bundles[#bundles + 1] = bundle_for(view, step, slot, param, claims, any_claimed)
    end
  end
  return bundles
end

return preview
