local midi_controller = {}

local midi_clock
local midi_out_devices = {}

function midi_controller:init()
  for i = 1, #midi.vports do
    midi_out_devices[i] = midi.connect(i)
  end 

end

function midi_controller:kill_all_midi()
  for id = 1, #midi.vports do
    for ch = 1, 16 do
      for note = 0, 127 do
        midi.devices[id]:note_off(note, 0, ch)
      end
    end
  end
end

function midi_controller:note_off(note, velocity, channel, device)

  if midi.devices[device] ~= nil then
    midi.devices[device]:note_off(note, velocity, channel)
  end

end

function midi_controller:note_on(note, velocity, channel, device)
  if midi.devices[device] ~= nil then
    midi.devices[device]:note_on(note, velocity, channel)
  end
end

function midi_controller:cc(cc, value, channel, device)

  if midi.devices[device] ~= nil then
    midi.devices[device]:cc(cc, value, channel, device)
  end

end

function midi_controller:clock_send()
  for id = 1, #midi.vports do
    if midi.devices[id] ~= nil then
      midi.devices[id]:clock()
    end
  end
end

function midi_controller:start()
  for id = 1, #midi.vports do
    if midi.devices[id] ~= nil then
      midi.devices[id]:start()
    end
  end
end

function midi_controller:stop()
  for id = 1, #midi.vports do
    if midi.devices[id] ~= nil then
      midi.devices[id]:stop()
    end
  end
end

return midi_controller