midi_controller = {}
midi_controller.start = function() end

function midi_controller:note_on(note, velocity, channel, device)
  table.insert(midi_note_on_events, {note, velocity, channel, device})
end

function midi_controller:note_off(note, velocity, channel, device)
  table.insert(midi_note_off_events, {note, velocity, channel, device})
end


function midi_controller.cc(cc_msb, cc_lsb, value, channel, device)
  table.insert(midi_cc_events, {cc_msb, value, channel})
end