mosaic_midi = {}
mosaic_midi.start = function() end

function mosaic_midi:note_on(note, velocity, channel, device)
  table.insert(midi_note_on_events, {note, velocity, channel, device})
end

function mosaic_midi:note_off(note, velocity, channel, device)
  table.insert(midi_note_off_events, {note, velocity, channel, device})
end

function mosaic_midi.cc(cc_msb, cc_lsb, value, channel, device)
  table.insert(midi_cc_events, {cc_msb, value, channel})
end