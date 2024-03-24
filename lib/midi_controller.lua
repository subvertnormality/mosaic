local fn = include("mosaic/lib/functions")
local step_handler = include("mosaic/lib/step_handler")
local quantiser = include("mosaic/lib/quantiser")

local midi_controller = {}

midi_devices = {}

local midi_note_mappings = {
  [1] = 1, [2] = 0, [3] = 2, [4] = 0, [5] = 3,
  [6] = 4, [7] = 0, [8] = 5, [9] = 0, [10] = 6,
  [11] = 0, [12] = 7
}

local midi_tables = {}
local midi_off_store = {}

for i = 0, 127 do
  local noteValue = midi_note_mappings[(i % 12) + 1] or 0
  local octaveValue = math.floor(i / 12) - 5
  midi_tables[i + 1] = {noteValue, octaveValue}
end

function flush_midi_off_store()
  for i = 1, #midi_off_store do
    midi_controller:note_off(midi_off_store[i].note, 0, midi_off_store[i].channel, midi_off_store[i].device)
  end
  midi_off_store = {}
end

function handle_midi_event_data(data)

  local channel = program.get_selected_channel()

  if channel.number == 17 then 
    return 
  end

  local transpose = step_handler.calculate_step_transpose(program.get().current_step, channel.number)

  local note = quantiser.process(midi_tables[data[2] + 1][1], midi_tables[data[2] + 1][2], transpose, channel.step_scale_number)
  local device = program.get().devices[channel.number]
  local midi_channel = device.midi_channel
  local velocity = data[3]

  if data[1] == 144 then -- note
    flush_midi_off_store()
    midi_controller:note_on(note, velocity, midi_channel, device.midi_device)
    table.insert(midi_off_store, {note = note, channel = midi_channel, device = device.midi_device})

  elseif data[1] == 128 then
    midi_controller:note_off(note, 0, midi_channel, device.midi_device)
    table.insert(midi_off_store, {note = note, channel = midi_channel, device = device.midi_device})
  elseif data[1] == 176 then -- modulation
    
  end 
end

function midi_controller.init()
  for i = 1, #midi.vports do
    midi_devices[i] = midi.connect(i)
    midi_devices[i].event = handle_midi_event_data
  end
end

function midi_controller.get_midi_outs()
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


function midi_controller.send_to_sinfonion(command, value)
  for id = 1, #midi_devices do

    if midi_devices[id] and midi_devices[id].name == "Norns2sinfonion" then
      midi_devices[id]:program_change(value, command)
    end
  end
end

function midi_controller.all_off(id)
  for note = 0, 127 do
    for channel = 1, 16 do
      midi_devices[id]:note_off(note, 0, channel)
    end
  end
end

function midi_controller:note_off(note, velocity, channel, device)
  if midi_devices[device] ~= nil then
    midi_devices[device]:note_off(note, velocity, channel)
  end
end

function midi_controller:note_on(note, velocity, channel, device)
  if midi_devices[device] ~= nil then
    midi_devices[device]:note_on(note, velocity, channel)
  end
end

function midi_controller.cc(cc_msb, cc_lsb, value, channel, device)
  if midi_devices[device] ~= nil then
    midi_devices[device]:cc(cc_msb, value, channel)
  end
end

function midi_controller.nrpn(nrpn_msb, nrpn_lsb, value, channel, device)
  -- Select NRPN (LSB and MSB)
  midi_controller.cc(99, nrpn_msb, channel, device)
  midi_controller.cc(98, nrpn_lsb, channel, device)

  local v1 = value / 128
  local v2 = value % 128

  midi_controller.cc(6, math.floor(v1), channel, device)
  midi_controller.cc(38, math.floor(v2), channel, device)
end

function midi_controller.start()
  for id = 1, #midi.vports do
    if midi_devices[id].device ~= nil then
      midi_devices[id]:start()
    end
  end
end

function midi_controller.stop()
  for id = 1, #midi.vports do
    if midi_devices[id].device ~= nil then
      midi_devices[id]:stop()
    end
  end
end

function midi_controller.panic()
  for id = 1, #midi.vports do
    if midi_devices[id].device ~= nil then
      midi_controller.all_off(id)
    end
  end
end

return midi_controller
