-- Own the emission/release boundary for the captured note container.
-- Future onset cancellation belongs to the clock; an emitted voice still owes Off.
local voice_lifetime = {}

function voice_lifetime.new(m_clock)
  local function play_note_internal(note, note_container, velocity, division, note_on_func, action_flag, onset_offset)
    local c = note_container.channel

    local accepted=note_on_func(note,velocity,note_container.midi_channel,note_container.midi_device)
    if accepted==false then return nil end

    local release_id=m_clock.delay_action(c, division + (onset_offset or 0), action_flag, function()
      note_container.player:note_off(note, velocity, note_container.midi_channel, note_container.midi_device, note_container.lead_time_ms)
    end, true, onset_offset ~= nil) -- Off-phase arp releases always queue to the parent.
    return release_id or true

  end

  -- Ordinary gates owe a release even when transport stops.
  -- A strummed voice sounds from inside its own delayed action, and a delay
  -- queued there counts whole steps from the cycle that action began in, not
  -- from the moment it ran. onset_fraction is that fraction of a step the voice
  -- sounds after its cycle began; adding it makes the gate last its selected
  -- length from the voice's own onset (README#chord-spread). Nil for a voice
  -- that sounds on a whole step, and ignored for a gate that releases at once.
  local function play_note(note, note_container, velocity, division, note_on_func, onset_fraction)
    -- Nonpositive ordinary gates release immediately, including nested strum callbacks.
    division = math.max(0, division)
    if onset_fraction and division > 0 then
      return play_note_internal(note, note_container, velocity, division + onset_fraction, note_on_func, "must_execute")
    end
    return play_note_internal(note, note_container, velocity, division, note_on_func, "must_execute")
  end

  -- Arp releases may also be flushed at the owning note end.
  local function play_arp_note(note, note_container, velocity, division, note_on_func, onset_offset)
    return play_note_internal(note, note_container, velocity, division, note_on_func, "execute_at_note_end", onset_offset)
  end

  return play_note, play_arp_note
end

return voice_lifetime
