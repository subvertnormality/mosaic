local math = require("math")
local floor = math.floor

local sinfonion = {}


function sinfonion.set_root_note(root)
  midi_controller.send_to_sinfonion(1, root)
end

function sinfonion.set_degree_nr(degree_nr)
  midi_controller.send_to_sinfonion(2, degree_nr)
end

function sinfonion.set_mode_nr(mode_nr)
  midi_controller.send_to_sinfonion(3, mode_nr)
end

function sinfonion.set_clock(clock)
  midi_controller.send_to_sinfonion(5, clock)
end

-- Transposition
function sinfonion.set_transposition(trans)
  trans = math.max(-64, math.min(63, trans))
  midi_controller.send_to_sinfonion(4, trans)
end

-- chaotic_detune
function sinfonion.set_chaotic_detune(detune)
  detune = math.max(-1.0, math.min(1.0, detune))
  local detune_int = floor(detune * 63.0) + 63
  midi_controller.send_to_sinfonion(9, detune_int)
end

-- harmonic_shift
function sinfonion.set_harmonic_shift(shift)
  midi_controller.send_to_sinfonion(10, shift)
end

-- Beat
function sinfonion.set_beat(beat)
  midi_controller.send_to_sinfonion(6, beat)
end

-- Step
function sinfonion.set_step(step)
  midi_controller.send_to_sinfonion(7, step)
end

-- Reset
function sinfonion.set_reset(reset_value)
  midi_controller.send_to_sinfonion(8, reset_value)
end

return sinfonion
