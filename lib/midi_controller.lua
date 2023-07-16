local midi_controller = {}

local midi_clock
local midi_out_devices = {}

function midi_controller.init()
  for i = 1, 4 do
    midi_out_devices[i] = midi.connect(i)
    midi_out_devices[i].event = midi_event
  end 

end

return midi_controller