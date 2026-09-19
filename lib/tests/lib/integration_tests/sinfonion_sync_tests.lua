-- README "Sinfonion": Mosaic sends the active global scale's root, degree and mode to
-- the Sinfonion. Pins the global scale-lock path (and the default scale around it)
-- through the clock, independent of how step.sinfonian_sync finds the step's lock.
step = include("mosaic/lib/step")
pattern = include("mosaic/lib/pattern")

local m_clock = include("mosaic/lib/clock/m_clock")
local quantiser = include("mosaic/lib/quantiser")

include("mosaic/lib/tests/helpers/mocks/sinfonion_mock")
include("mosaic/lib/tests/helpers/mocks/params_mock")
include("mosaic/lib/tests/helpers/mocks/m_midi_mock")
include("mosaic/lib/tests/helpers/mocks/channel_edit_page_ui_mock")
include("mosaic/lib/tests/helpers/mocks/device_map_mock")
include("mosaic/lib/tests/helpers/mocks/norns_mock")
include("mosaic/lib/tests/helpers/mocks/channel_sequence_page_mock")
include("mosaic/lib/tests/helpers/mocks/channel_edit_page_mock")

function test_sinfonion_follows_a_global_scale_lock_and_its_persistence()
  program.init()
  globals.reset()
  params.reset()
  local sent = {}
  sinfonion.set_root_note = function(root) table.insert(sent, root) end
  local major = quantiser.get_scales()[1]
  program.set_scale(1, {number = 1, scale = major.scale, pentatonic_scale = major.pentatonic_scale, chord = 1, root_note = 0})
  program.set_scale(2, {number = 1, scale = major.scale, pentatonic_scale = major.pentatonic_scale, chord = 1, root_note = 2})
  program.get().default_scale = 1
  program.get().selected_channel = 17
  program.add_step_scale_trig_lock(3, 2)
  m_clock.init()
  m_clock:start()
  for _ = 1, 24 * 4 do m_clock.get_clock_lattice():pulse() end
  -- Steps 1-2 use the default scale (root C); the step-3 global lock (root D)
  -- persists until another global lock or the global scale track wraps.
  luaunit.assert_equals({sent[1], sent[2], sent[3], sent[4]}, {0 + major.sinf_root_mod, 0 + major.sinf_root_mod, 2 + major.sinf_root_mod, 2 + major.sinf_root_mod})
end
