
local step = include("mosaic/lib/step")
local quantiser = include("mosaic/lib/quantiser")
local divisions = include("mosaic/lib/clock/divisions")

local m_midi = {}

midi_devices = {}
m_midi.note_counts = {}  -- Initialize note counts table

local chord_number = 0
local midi_input = include("mosaic/lib/devices/midi_input")
local midi_ingress = midi_input.new(m_midi, step, quantiser, divisions)

handle_midi_event_data = function(data, midi_device)
  return midi_ingress.handle(data, midi_device)
end


function m_midi.init()
  for i = 1, #midi.vports do
    midi_devices[i] = midi.connect(i)
    midi_devices[i].event = function(data) 
      handle_midi_event_data(data, midi_devices[i])
    end
  end

end

function m_midi.get_midi_outs()
  local midi_outs = {}
  for i = 1, #midi.vports do
    if midi_devices[i] and midi_devices[i].name ~= "none" and midi_devices[i].name ~= "Norns2sinfonion" then
      table.insert(
        midi_outs,
        {name = "OUT " .. i, value = i, long_name = util.trim_string_to_width(midi_devices[i].name, 80)}
      )
    end
  end

  return midi_outs
end


function m_midi.send_to_sinfonion(command, value)
  for id = 1, #midi_devices do

    if midi_devices[id] and midi_devices[id].name == "Norns2sinfonion" then
      midi_devices[id]:program_change(value, command)
    end
  end
end

function m_midi:reset_note_counts()
  for device = 1, #midi_devices do
    self.note_counts[device] = nil
  end
end


function m_midi:note_on(note, velocity, channel, device)
  if midi_devices[device] ~= nil then
    -- Composed scale/chord/merge/octave operations may exceed MIDI's
    -- seven-bit note domain. Normalize at the final MIDI-only boundary.
    note = fn.constrain(0, 127, note)
    -- Initialize tables if necessary
    if not self.note_counts[device] then
      self.note_counts[device] = {}
    end
    if not self.note_counts[device][channel] then
      self.note_counts[device][channel] = {}
    end
    if not self.note_counts[device][channel][note] then
      self.note_counts[device][channel][note] = 0
    end

    -- Increment the note count
    self.note_counts[device][channel][note] = self.note_counts[device][channel][note] + 1

    -- Send the Note On message
    midi_devices[device]:note_on(note, velocity, channel)
  end
end

function m_midi:note_off(note, velocity, channel, device)
  if midi_devices[device] ~= nil then
    -- Use the same normalized key as note_on so ownership cannot strand.
    note = fn.constrain(0, 127, note)
    -- Check if the note is currently on
    if self.note_counts[device] and self.note_counts[device][channel] and self.note_counts[device][channel][note] then
      -- Decrement the note count
      self.note_counts[device][channel][note] = self.note_counts[device][channel][note] - 1
      -- Every emitted Note On owns a Note Off, including overlapping pitches.
      -- Retain counts for bookkeeping without collapsing receiver releases.
      midi_devices[device]:note_off(note, velocity, channel)
      if self.note_counts[device][channel][note] <= 0 then
        -- Remove the note from the table
        self.note_counts[device][channel][note] = nil
      end
    else
      -- Note is not currently on, but we received a Note Off.
      -- For safety, send Note Off anyway
      midi_devices[device]:note_off(note, velocity, channel)
    end
  end
end

m_midi.cc, m_midi.nrpn = include("mosaic/lib/devices/midi_wire_output").new(m_midi)

function m_midi:program_change(program_id, channel, device)
  if midi_devices[device] ~= nil then
    midi_devices[device]:program_change(program_id, channel)
  end
end

function m_midi.start()

  for id = 1, #midi.vports do
    if midi_devices[id].device ~= nil then
      midi_devices[id]:start()
    end
  end

end

function m_midi:all_notes_off()
  for device, channels in pairs(self.note_counts) do
    if midi_devices[device] ~= nil then
      for channel, notes in pairs(channels) do
        for note, count in pairs(notes) do
          if count > 0 then
            -- Preserve one release for every owned onset, including distinct
            -- internal notes that clamp to the same MIDI endpoint.
            for _ = 1, count do
              midi_devices[device]:note_off(note, 0, channel)
            end
            self.note_counts[device][channel][note] = nil
          end
        end
        -- Clean up empty channel tables
        if next(self.note_counts[device][channel]) == nil then
          self.note_counts[device][channel] = nil
        end
      end
      -- Clean up empty device tables
      if next(self.note_counts[device]) == nil then
        self.note_counts[device] = nil
      end
    end
  end
end

-- Modify the stop function
function m_midi.stop(send_transport)
  -- Turn off all active notes
  m_midi:all_notes_off()

  -- Restart cleanup releases voices without sending Stop back to the clock
  -- source. Ordinary Stop retains its transport output on every device.
  if send_transport ~= false then
    for id = 1, #midi.vports do
      if midi_devices[id] and midi_devices[id].device ~= nil then
        midi_devices[id]:stop()
      end
    end
  end

  -- Reset note counts
  m_midi.note_counts = {}
  -- Transport Stop also resets keyboard chord state, so a key whose Note Off
  -- never arrived cannot keep a step's chord open.
  midi_ingress.reset_chords()
end


local all_off_by_device = {}
function m_midi.all_off(id)
  if not all_off_by_device[id] then
    all_off_by_device[id] = scheduler.debounce(function()
      for note = 0, 127 do
        for channel = 1, 16 do
          midi_devices[id]:note_off(note, 0, channel)
          -- Forget only notes actually cleared by this sweep position.
          -- Notes played behind it still need ownership for transport Stop.
          local channels = m_midi.note_counts[id]
          if channels and channels[channel] then
            channels[channel][note] = nil
          end
        end
        coroutine.yield()
      end
      chord_number = 0
    end)
  end
  all_off_by_device[id]()
end

function m_midi.panic()
  for id = 1, #midi.vports do
    if midi_devices[id].device ~= nil then
      m_midi.all_off(id)
    end
  end
  -- Clear all note counts
  m_midi.note_counts = {}
  chord_number = 0
end

function m_midi.midi_devices_connected() 
  for id = 1, #midi.vports do
    if midi_devices[id].device ~= nil then
      return true
    end
  end
  return false
end


function m_midi.set_up_midi_mapping_params()
  return include("mosaic/lib/devices/midi_mapping_params").setup()
end

return m_midi