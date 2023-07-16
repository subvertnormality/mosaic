local midi_controller = {}

midi_devices = {}
midi_device_names = {}

function midi_controller:init()
  for i = 1, #midi.vports do
    midi_devices[i] = midi.connect(i)
    table.insert( -- register its name:
      midi_device_names, -- table to insert to
      "port "..i..": "..util.trim_string_to_width(midi_devices[i].name,80) -- value to insert
    )

  end 

end

function midi_controller:kill_all_midi()
  for id = 1, #midi.vports do
    for ch = 1, 16 do
      for note = 0, 127 do
        if midi_devices[id] ~= nil then
          midi_devices[id]:note_off(note, 0, ch)
        end
      end
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

function midi_controller:cc(cc, value, channel, device)

  if midi_devices[device] ~= nil then
    midi_devices[device]:cc(cc, value, channel, device)
  end

end

function midi_controller:clock_send()
  for id = 1, #midi.vports do
    if midi_devices[id] ~= nil then
      midi_devices[id]:clock()
    end
  end
end

function midi_controller:start()
  for id = 1, #midi.vports do
    if midi_devices[id] ~= nil then
      midi_devices[id]:start()
    end
  end
end

function midi_controller:stop()
  for id = 1, #midi.vports do
    if midi_devices[id] ~= nil then
      midi_devices[id]:stop()
    end
  end
  midi_controller:kill_all_midi()
end

return midi_controller