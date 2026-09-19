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

function context.scale_pitch_classes(scale_number, transpose)
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
