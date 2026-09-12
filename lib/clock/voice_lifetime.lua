-- Own the emission/release boundary for the captured note container.
-- Future onset cancellation belongs to the clock; an emitted voice still owes Off.
local voice_lifetime = {}

function voice_lifetime.new(m_clock)
  local function play_note_internal(note, note_container, velocity, division, note_on_func, action_flag, onset_offset)
    local c = note_container.channel

    note_on_func(note, velocity, note_container.midi_channel, note_container.midi_device)

    return m_clock.delay_action(c, division + (onset_offset or 0), action_flag, function()
      note_container.player:note_off(note, velocity, note_container.midi_channel, note_container.midi_device)
    end, true, onset_offset ~= nil) -- Off-phase arp releases always queue to the parent.

  end

  -- Ordinary gates owe a release even when transport stops.
  local function play_note(note, note_container, velocity, division, note_on_func)
    -- Nonpositive ordinary gates release immediately, including nested strum callbacks.
    play_note_internal(note, note_container, velocity, math.max(0, division), note_on_func, "must_execute")
  end

  -- Arp releases may also be flushed at the owning note end.
  local function play_arp_note(note, note_container, velocity, division, note_on_func, onset_offset)
    return play_note_internal(note, note_container, velocity, division, note_on_func, "execute_at_note_end", onset_offset)
  end

  return play_note, play_arp_note
end

return voice_lifetime
