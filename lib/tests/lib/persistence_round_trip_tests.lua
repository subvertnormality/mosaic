-- README 1052-1054: saved and autosaved projects load again. These tests use the real
-- program model, memory and norns tabutil serialiser (no stubs) so a refactor of the
-- data model or its serialisation cannot silently change what a saved project restores.
local tab = require("tabutil")
local divisions = include("mosaic/lib/clock/divisions")
local project_validation = include("mosaic/lib/project_validation")
local quantiser = include("mosaic/lib/quantiser")

local function close(a, b)
  return math.abs(a - b) <= 1e-12 * math.max(1, math.abs(a), math.abs(b))
end

local function differences(a, b, path, out)
  out = out or {}
  if type(a) == "number" and type(b) == "number" then
    if not close(a, b) then out[#out + 1] = path .. ": " .. tostring(a) .. " ~= " .. tostring(b) end
  elseif type(a) == "table" and type(b) == "table" then
    for k, v in pairs(a) do
      if type(v) ~= "function" then differences(v, b[k], path .. "." .. tostring(k), out) end
    end
    for k, v in pairs(b) do
      if a[k] == nil and type(v) ~= "function" then out[#out + 1] = path .. "." .. tostring(k) .. ": added" end
    end
  elseif a ~= b then
    out[#out + 1] = path .. ": " .. tostring(a) .. " ~= " .. tostring(b)
  end
  return out
end

local function build_project()
  program.init()
  memory.init()
  local major = quantiser.get_scales()[1]
  program.set_scale(2, {number = 3, scale = quantiser.get_scales()[3].scale,
    pentatonic_scale = quantiser.get_scales()[3].pentatonic_scale, chord = 2, root_note = 4, transpose = -3, chord_degree_rotation = 1})
  program.get().selected_channel = 1
  local channel = program.get_selected_channel()
  channel.length_mask = 1/3
  channel.clock_mods = divisions.clock_divisions[18]
  program.add_step_param_trig_lock(5, 1, 99)
  program.add_step_scale_trig_lock(3, 2)
  memory.record_event(1, "note_mask", {step = 1, note = 72, velocity = 90, length = 5/6, song_pattern = 1})
  memory.record_event(1, "note_mask", {step = 2, note = 76, velocity = 80, chord_degrees = {1, 3, 5}, song_pattern = 1})
  program.get_song_pattern(2).repeats = 3
end

local function save_and_load(path)
  tab.save({"round-trip", program.prepare_for_save()}, path)
  local saved = tab.load(path)
  local valid, reason = project_validation.check(saved)
  luaunit.assert_true(valid, tostring(reason))
  program.init()
  program.set(saved[2])
  return saved
end

function test_saved_project_round_trip_is_stable()
  build_project()
  local first_path, second_path = os.tmpname(), os.tmpname()
  local first = save_and_load(first_path)
  local second = save_and_load(second_path)
  os.remove(first_path); os.remove(second_path)
  luaunit.assert_equals(differences(first[2], second[2], "project"), {})
end

function test_saved_project_restores_locks_masks_scales_and_memory()
  build_project()
  local path = os.tmpname()
  save_and_load(path)
  os.remove(path)
  local channel = program.get_channel(1, 1)
  luaunit.assert_equals(program.get_step_param_trig_lock(channel, 5, 1), 99)
  luaunit.assert_equals(program.get_step_scale_trig_lock(channel, 3), 2)
  luaunit.assert_equals(divisions.note_division_index(channel.length_mask), 6)
  luaunit.assert_equals(channel.clock_mods.name, divisions.clock_divisions[18].name)
  local scale = program.get_scale(2)
  luaunit.assert_equals({scale.number, scale.root_note, scale.chord, scale.transpose, scale.chord_degree_rotation}, {3, 4, 2, -3, 1})
  luaunit.assert_equals(program.get_song_pattern(2).repeats, 3)
  luaunit.assert_equals(channel.step_note_masks[1], 72)
  luaunit.assert_equals(divisions.note_division_index(channel.step_length_masks[1]), 12)
  luaunit.assert_equals(channel.step_note_masks[2], 76)
  luaunit.assert_equals(memory.get_event_count(1), 2)
  memory.undo(1)
  luaunit.assert_nil(channel.step_note_masks[2])
  luaunit.assert_equals(channel.step_note_masks[1], 72)
end
