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
local chord_number = 0
local chord_one_note = nil

for i = 0, 127 do
  local noteValue = midi_note_mappings[(i % 12) + 1] or 0
  local octaveValue = math.floor(i / 12) - 5

  midi_tables[i + 1] = {noteValue-1, octaveValue}
end

function handle_midi_event_data(data, midi_device)


  local channel = program.get_selected_channel()

  if channel.number == 17 then 
    return 
  end

  local transpose = step_handler.calculate_step_transpose(program.get().current_step, channel.number)
  local device = program.get().devices[channel.number]
  local midi_channel = device.midi_channel
  local velocity = data[3]

  if data[1] == 144 then -- note on
    if midi_tables[data[2]] == nil then
      return
    end


    local step_scale_number = channel.step_scale_number

    local pressed_keys = grid_controller.get_pressed_keys()
    local channel = program.get_selected_channel()
    if #pressed_keys > 0 then
      if (pressed_keys[1][2] > 3 and pressed_keys[1][2] < 8) then
        local step = fn.calc_grid_count(pressed_keys[1][1], pressed_keys[1][2])
        step_scale_number = step_handler.manually_calculate_step_scale_number(channel.number, step)
      end
    end

    midi_off_store[data[2]] = step_scale_number
    
    local note = quantiser.process_with_global_params(midi_tables[data[2] + 1][1], midi_tables[data[2] + 1][2], transpose, step_scale_number)
    if params:get("midi_scale_mapped_to_white_keys") == 1 then
      note = data[2]
    end
    midi_controller:note_on(note, velocity, midi_channel, device.midi_device)
    if chord_number == 0 then 
      chord_one_note = note 
    end
    chord_number = chord_number + 1

    local chord_degree = nil

    chord_degree = fn.find_index_by_value(program.get_scale(step_scale_number).scale, quantiser.snap_to_scale(note, step_scale_number)) - fn.find_index_by_value(program.get_scale(step_scale_number).scale, quantiser.snap_to_scale(chord_one_note, step_scale_number))

    if chord_degree < -14 then
      chord_degree = nil
    end

    channel_edit_page_controller.handle_note_on_midi_controller_message(note, velocity, chord_number, chord_degree)
  elseif data[1] == 128 then -- note off
    if midi_tables[data[2]] == nil then
      return
    end
    local note = quantiser.process_with_global_params(midi_tables[data[2] + 1][1], midi_tables[data[2] + 1][2], transpose, midi_off_store[data[2]])
    midi_controller:note_off(note, 0, midi_channel, device.midi_device)
    chord_number = chord_number - 1
    if chord_number == 0 then 
      chord_one_note = nil 
    end
  elseif data[1] == 176 then -- cc change
    if data[2] >= 15 and (data[2] - 14) <= 10 then
      channel_edit_page_ui_controller.handle_trig_lock_param_change_by_direction(data[3] - 64, channel, data[2] - 14)
    end
  end 
end

function midi_controller.init()
  for i = 1, #midi.vports do
    midi_devices[i] = midi.connect(i)
    midi_devices[i].event = function(data) 
      handle_midi_event_data(data, midi_devices[i])
    end
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
  chord_number = 0
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

function midi_controller:program_change(program_id, channel, device)
  if midi_devices[device] ~= nil then
    midi_devices[device]:program_change(program_id, channel)
  end
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
  chord_number = 0
end

function midi_controller.panic()
  for id = 1, #midi.vports do
    if midi_devices[id].device ~= nil then
      midi_controller.all_off(id)
    end
  end
  chord_number = 0
end

function midi_controller.midi_devices_connected() 
  for id = 1, #midi.vports do
    if midi_devices[id].device ~= nil then
      return true
    end
  end
  return false
end

return midi_controller
