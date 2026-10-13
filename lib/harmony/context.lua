local quantiser = include("mosaic/lib/quantiser")

local context = {}

local function pitch_class(value)
  return value and ((value % 12) + 12) % 12 or nil
end

local function append(parts, value)
  parts[#parts + 1] = tostring(value)
end

local function source_revision(group, scale_number, transpose, scale, pentatonic)
  local parts = {"harmony-context-v1"}
  append(parts, scale_number)
  append(parts, transpose)
  append(parts, scale and scale.version or 0)
  append(parts, scale and scale.root_note or -1)
  append(parts, scale and scale.chord or -1)
  append(parts, scale and scale.chord_degree_rotation or 0)
  append(parts, pentatonic == true)
  for _, value in ipairs(scale and scale.scale or {}) do append(parts, value) end
  for index, offset in ipairs(group.template.offsets) do
    append(parts, offset)
    append(parts, group.template.required[index] == true)
  end
  return table.concat(parts, ":")
end

function context.group_material(group, scale_number, transpose, pentatonic)
  local scale = program.get_scale(scale_number)
  local result = {
    material = {},
    pitch_classes = {},
    revision = source_revision(group, scale_number, transpose, scale, pentatonic)
  }
  if not scale then return result end
  for index, offset in ipairs(group.template.offsets) do
    local pitch = quantiser.process(offset, 0, transpose or 0, scale_number, pentatonic == true)
    local pc = pitch_class(pitch)
    if pc ~= nil then
      result.pitch_classes[#result.pitch_classes + 1] = pc
      result.material[#result.material + 1] = {
        id = "tone" .. index,
        pc = pc,
        required = group.template.required[index] == true
      }
    end
  end
  return result
end

local function compute_scale_pitch_classes(scale_number, transpose)
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
context.compute_scale_pitch_classes = compute_scale_pitch_classes

-- The pitch classes of a scale are asked for on every note (step.handle's
-- structural target context). They are a pure function of what
-- quantiser.process(degree, 0, transpose, scale_number, false) reads: the
-- program's root note and chord, and the scale container's root note, chord,
-- chord-degree rotation, version, scale array and the presence of its
-- pentatonic array; and of transpose. An entry per (scale number, transpose)
-- holds a copy of all of them and is used only when every one is equal
-- (numbers also by subtype), so an in-place edit (for example
-- program.set_chord_degree_rotation_for_scale) or a replaced container misses.
-- Callers get their own copy of the list.
local math_type = math.type
local pitch_class_memo = {}

local function same_value(left, right)
  return left == right and math_type(left) == math_type(right)
end

function context.scale_pitch_classes(scale_number, transpose)
  if transpose ~= transpose then return compute_scale_pitch_classes(scale_number, transpose) end
  local scale = program.get_scale(scale_number)
  if not scale then return {} end
  local program_data = program.get()
  local notes = scale.scale
  local by_transpose = pitch_class_memo[scale_number]
  local entry = by_transpose and by_transpose[transpose or 0]
  if entry and same_value(entry.transpose, transpose) and same_value(entry.root, program_data.root_note) and
    same_value(entry.chord, program_data.chord) and same_value(entry.scale_root, scale.root_note) and
    same_value(entry.scale_chord, scale.chord) and same_value(entry.rotation, scale.chord_degree_rotation) and
    same_value(entry.version, scale.version) and entry.has_pentatonic == (type(scale.pentatonic_scale) == "table") and
    type(notes) == "table" and #notes == #entry.notes then
    local copy, same = entry.notes, true
    for index = 1, #copy do
      if not same_value(notes[index], copy[index]) then same = false; break end
    end
    if same then return {table.unpack(entry.result)} end
  end
  local result = compute_scale_pitch_classes(scale_number, transpose)
  if type(notes) == "table" then
    if not by_transpose then by_transpose = {}; pitch_class_memo[scale_number] = by_transpose end
    by_transpose[transpose or 0] = {transpose = transpose, root = program_data.root_note, chord = program_data.chord,
      scale_root = scale.root_note, scale_chord = scale.chord, rotation = scale.chord_degree_rotation,
      version = scale.version, has_pentatonic = type(scale.pentatonic_scale) == "table",
      notes = {table.unpack(notes, 1, #notes)}, result = {table.unpack(result)}}
  end
  return result
end

function context.selected_degree_pitch_classes(scale_number, transpose, selected)
  local inventory = context.scale_pitch_classes(scale_number, transpose)
  local result = {}
  for _, index in ipairs(selected or {}) do
    if inventory[index] ~= nil then result[#result + 1] = inventory[index] end
  end
  return result
end

function context.nearest_pitch(source, pitch_classes)
  local allowed = {}
  for _, value in ipairs(pitch_classes or {}) do allowed[pitch_class(value)] = true end
  local best, distance
  for pitch = 0, 127 do
    if allowed[pitch_class(pitch)] then
      local candidate_distance = math.abs(pitch - source)
      if distance == nil or candidate_distance < distance then
        best, distance = pitch, candidate_distance
      end
    end
  end
  return best
end

return context
