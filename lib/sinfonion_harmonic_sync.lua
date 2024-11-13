local math = require("math")
local floor = math.floor

local sinfonion = {}


function sinfonion.set_root_note(root)
  mosaic_midi.send_to_sinfonion(1, root)
end

function sinfonion.set_degree_nr(degree_nr)
  mosaic_midi.send_to_sinfonion(2, degree_nr)
end

function sinfonion.set_mode_nr(mode_nr)
  mosaic_midi.send_to_sinfonion(3, mode_nr)
end

function sinfonion.set_clock(clock)
  mosaic_midi.send_to_sinfonion(5, clock)
end

-- Transposition takes a value of -64 to 63
function sinfonion.set_transposition(trans)
  trans = math.max(-64, math.min(63, trans))
  mosaic_midi.send_to_sinfonion(4, trans + 64)
end

-- chaotic_detune takes a value of -1.0 to 1.0
function sinfonion.set_chaotic_detune(detune)
  -- Ensure the input is within the expected range
  if detune > 1.0 then
    detune = 1.0
  elseif detune < -1.0 then
    detune = -1.0
  end

  -- First, scale and offset the floatValue to the range -64 to 63
  local adjusted_value = math.floor(detune * 64 + 0.5)

  -- Now, adjust the range to 0 to 127 by adding 64
  local midi_value = adjusted_value + 64

  mosaic_midi.send_to_sinfonion(9, midi_value)
end

-- harmonic_shift takes a value of -11 to +11
function sinfonion.set_harmonic_shift(shift)
  mosaic_midi.send_to_sinfonion(10, shift + 11)
end

-- Beat
function sinfonion.set_beat(beat)
  mosaic_midi.send_to_sinfonion(6, beat)
end

-- Step
function sinfonion.set_step(step)
  mosaic_midi.send_to_sinfonion(7, step)
end

-- Reset
function sinfonion.set_reset(reset_value)
  mosaic_midi.send_to_sinfonion(8, reset_value)
end

return sinfonion
