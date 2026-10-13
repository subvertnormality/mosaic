-- The per-note scale pitch-class lookup (harmony/context.scale_pitch_classes,
-- read by step.handle's structural target context on every note) is served
-- from a content-validated memo. Compared here, over seeded random programs,
-- scales and in-place edits, with the pre-change computation kept verbatim.

local harmony_context = include("mosaic/lib/harmony/context")
local quantiser = include("mosaic/lib/quantiser")

local function pitch_class(value)
  return value and ((value % 12) + 12) % 12 or nil
end

-- The pre-change context.scale_pitch_classes, verbatim.
local function reference(scale_number, transpose)
  local scale = program.get_scale(scale_number)
  if not scale then return {} end
  local result, seen = {}, {}
  for degree = 0, math.max(0, #(scale.scale or {}) - 1) do
    local value = pitch_class(quantiser.process(degree, 0, transpose or 0, scale_number, false))
    if value == nil then break end
    if seen[value] then break end
    seen[value] = true
    result[#result + 1] = value
    if #result == 12 then break end
  end
  return result
end

local function same(left, right)
  if #left ~= #right then return false end
  for index = 1, #left do
    if left[index] ~= right[index] or math.type(left[index]) ~= math.type(right[index]) then return false end
  end
  return true
end

function test_harmony_scale_pitch_classes_memo_matches_the_computation_across_edits()
  program.init()
  local random = math.random
  math.randomseed(9091)
  local scales = quantiser.get_scales()
  local song = program.get_selected_song_pattern()
  local checks = 0
  for case = 1, 1500 do
    local scale_number = random(0, 4)
    local container = scale_number > 0 and song.scales[scale_number]
    local draw = random(10)
    if container and draw == 1 then
      local chosen = scales[random(#scales)]
      container.scale, container.pentatonic_scale = chosen.scale, chosen.pentatonic_scale    -- replaced arrays
    elseif container and draw == 2 then
      local copy = {table.unpack(container.scale)}
      copy[random(#copy)] = copy[1] + random(0, 11)                                          -- a changed value
      container.scale = copy
    elseif container and draw == 3 then
      local copy = {table.unpack(container.scale)}
      copy[1] = copy[1] + 0.0                                                                -- same value, float
      container.scale = copy
    elseif container and draw == 4 then
      program.set_chord_degree_rotation_for_scale(scale_number, random(0, 6))                -- in place
    elseif container and draw == 5 then
      container.root_note, container.chord = random(-1, 11), random(-1, 7)
    elseif draw == 6 then
      program.get().root_note, program.get().chord = random(0, 11), random(1, 7)
      -- The program's root and chord apply where the scale has none.
      if container and random(2) == 1 then container.root_note, container.chord = -1, -1 end
    elseif container and draw == 7 then
      container.version = (container.version or 0) + 1
    end
    local transpose = ({0, 0, 0, 1, -3, 7, 0.0, 2.0})[random(8)]
    local actual = harmony_context.scale_pitch_classes(scale_number, transpose)
    luaunit.assert_true(same(actual, reference(scale_number, transpose)), "case " .. case)
    -- Each caller owns its list.
    actual[1] = -1
    luaunit.assert_true(same(harmony_context.scale_pitch_classes(scale_number, transpose), reference(scale_number, transpose)),
      "case " .. case .. " after writing a returned list")
    checks = checks + 1
  end
  luaunit.assert_equals(checks, 1500)
end
