local midi_controller = {}

midi_devices = {}
midi_device_names = {}

function midi_controller.init()
  for i = 1, #midi.vports do
    midi_devices[i] = midi.connect(i)
    table.insert( -- register its name:
      midi_device_names, -- table to insert to
      "port "..i..": "..util.trim_string_to_width(midi_devices[i].name,80) -- value to insert
    )
  end 
end

function midi_controller.get_midi_outs()
  local midi_outs = {}
  for i = 1, #midi.vports do
    if midi_devices[i] and midi_devices[i].name ~= "none" then
      table.insert( 
        midi_outs, 
        {name = "OUT "..i, value = i, long_name = util.trim_string_to_width(midi_devices[i].name,80)}
      )
    end
  end 

  return midi_outs
end

function midi_controller.all_off(id)

  for note = 0, 127 do
    midi_devices[id]:note_off(note)
  end

end


function midi_controller.note_off(note, velocity, channel, device)

  if midi_devices[device] ~= nil then
    midi_devices[device]:note_off(note, velocity, channel)
  end

end

function midi_controller.note_on(note, velocity, channel, device)
  if midi_devices[device] ~= nil then
    midi_devices[device]:note_on(note, velocity, channel)
  end
end

function midi_controller.cc(cc, value, channel, device)

  if midi_devices[device] ~= nil then
    midi_devices[device]:cc(cc, value, channel, device)
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
    if midi_devices[id] ~= nil then
      midi_devices[id]:start()
    end
  end
end

function midi_controller.continue()
  for id = 1, #midi.vports do
    if midi_devices[id] ~= nil then
      midi_devices[id]:continue()
    end
  end
end

function midi_controller.stop()
  for id = 1, #midi.vports do
    if midi_devices[id] ~= nil then
      midi_devices[id]:stop()
      midi_controller.all_off(id)
    end
  end
end

return midi_controller