local config = {}

local function integer(value, low, high)
  return type(value) == "number" and value == value and value % 1 == 0 and
    value >= low and value <= high
end

local function round_half_up(value)
  return math.floor(value + 0.5)
end

function config.curve(shape, cycles)
  local result = {}
  for index = 1, cycles do
    if cycles == 1 or shape == "flat" then
      result[index] = 100
    elseif shape == "build" then
      result[index] = round_half_up(100 * index / cycles)
    elseif shape == "answer" then
      result[index] = index % 2 == 1 and 100 or 25
    elseif shape == "fill" then
      result[index] = index == cycles and 100 or 25
    end
  end
  return result
end

function config.new()
  return {
    schema_version = 2,
    mode = "off",
    anchor = nil,
    amount = 100,
    accent = 70,
    gap = 0,
    seed = 0,
    ranking_version = 1,
    cycles = 1,
    shape = "flat",
    percentages = {100},
    variation = "fixed",
    keep_anchor_pitch = false,
    target = {kind = "legacy"},
    interlock = {leader = nil, window = 0},
    space = {leader = nil, release = 0},
    fragments = {size = 8, keep_anchor = false},
    structure = {markers = "off", group_id = nil}
  }
end

-- Fields shared by v1 and v2 (v1 had no others with semantics).
local function validate_common(value)
  if value.anchor ~= nil and not integer(value.anchor, 1, 16) then return nil, "merge anchor" end
  if value.mode == "foundation" and value.anchor == nil then return nil, "merge anchor" end
  if not integer(value.amount, 0, 100) then return nil, "merge amount" end
  if not integer(value.accent, 0, 100) then return nil, "merge accent" end
  if not integer(value.gap, 0, 8) then return nil, "merge gap" end
  if not integer(value.seed, 0, 65535) then return nil, "merge seed" end
  if value.ranking_version ~= 1 then return nil, "merge ranking version" end
  if value.cycles ~= 1 and value.cycles ~= 2 and value.cycles ~= 4 and value.cycles ~= 8 then
    return nil, "merge cycles"
  end
  if value.shape ~= "flat" and value.shape ~= "build" and value.shape ~= "answer" and
    value.shape ~= "fill" and value.shape ~= "custom" then return nil, "merge shape" end
  if type(value.percentages) ~= "table" or #value.percentages ~= value.cycles then
    return nil, "merge percentages"
  end
  for _, percentage in ipairs(value.percentages) do
    if not integer(percentage, 0, 100) then return nil, "merge percentages" end
  end
  if value.variation ~= "fixed" and value.variation ~= "per_phrase" then
    return nil, "merge variation"
  end
  if type(value.keep_anchor_pitch) ~= "boolean" then return nil, "merge anchor pitch" end
  local target = value.target
  if type(target) ~= "table" or
    (target.kind ~= "legacy" and target.kind ~= "scale" and target.kind ~= "degrees" and
      target.kind ~= "chord") then return nil, "merge target" end
  if target.kind == "degrees" then
    if type(target.degrees) ~= "table" or #target.degrees == 0 then return nil, "merge target degrees" end
    local seen = {}
    for _, degree in ipairs(target.degrees) do
      if not integer(degree, 1, 16) or seen[degree] then return nil, "merge target degrees" end
      seen[degree] = true
    end
  elseif target.kind == "chord" and not integer(target.group_id, 1, 16) then
    return nil, "merge target group"
  end
  return true
end

-- The saved schema_version 1 validator, unchanged: it ignores keys it does not know.
function config.validate_v1(value)
  if type(value) ~= "table" or value.schema_version ~= 1 then
    return nil, "merge schema version"
  end
  if value.mode ~= "off" and value.mode ~= "foundation" then return nil, "merge mode" end
  return validate_common(value)
end

local function only_keys(value, allowed)
  for key in pairs(value) do if not allowed[key] then return false end end
  return true
end

-- A sequence with exactly the keys 1..#value.
local function closed_array(value)
  local count = 0
  for _ in pairs(value) do count = count + 1 end
  return count == #value
end

local top_level = {
  schema_version = true, mode = true, anchor = true, amount = true, accent = true, gap = true,
  seed = true, ranking_version = true, cycles = true, shape = true, percentages = true,
  variation = true, keep_anchor_pitch = true, target = true, interlock = true, space = true,
  fragments = true, structure = true
}
local target_keys = {
  legacy = {kind = true}, scale = {kind = true}, degrees = {kind = true, degrees = true},
  chord = {kind = true, group_id = true}
}
local markers = {off = true, anchors = true, every_4 = true, every_8 = true}

local function leader(value, channel)
  return value == nil or (integer(value, 1, 16) and value ~= channel)
end

-- The closed, recursive schema_version 2 validator. `channel`, when known,
-- rejects a leader naming its own channel. (The one-way dependency graph of
-- plan §1.5 is validated by the Interlock card.)
function config.validate(value, channel)
  if type(value) ~= "table" or value.schema_version ~= 2 then
    return nil, "merge schema version"
  end
  if not only_keys(value, top_level) then return nil, "merge field" end
  if value.mode ~= "off" and value.mode ~= "foundation" and value.mode ~= "fragments" then
    return nil, "merge mode"
  end
  local ok, reason = validate_common(value)
  if not ok then return nil, reason end
  if not closed_array(value.percentages) then return nil, "merge percentages" end
  local target = value.target
  if not only_keys(target, target_keys[target.kind]) then return nil, "merge target" end
  if target.kind == "degrees" and not closed_array(target.degrees) then return nil, "merge target degrees" end

  local interlock = value.interlock
  if type(interlock) ~= "table" or not only_keys(interlock, {leader = true, window = true}) or
    not leader(interlock.leader, channel) or not integer(interlock.window, 0, 4) then
    return nil, "merge interlock"
  end
  local space = value.space
  if type(space) ~= "table" or not only_keys(space, {leader = true, release = true}) or
    not leader(space.leader, channel) or not integer(space.release, 0, 4) then
    return nil, "merge space"
  end
  local fragments = value.fragments
  if type(fragments) ~= "table" or not only_keys(fragments, {size = true, keep_anchor = true}) or
    (fragments.size ~= 4 and fragments.size ~= 8 and fragments.size ~= 16) or
    type(fragments.keep_anchor) ~= "boolean" then
    return nil, "merge fragments"
  end
  if value.mode == "fragments" and fragments.keep_anchor and value.anchor == nil then
    return nil, "merge anchor"
  end
  local structure = value.structure
  if type(structure) ~= "table" or not only_keys(structure, {markers = true, group_id = true}) or
    not markers[structure.markers] or
    (structure.group_id ~= nil and not integer(structure.group_id, 1, 16)) or
    (structure.markers ~= "off" and structure.group_id == nil) then
    return nil, "merge structure"
  end
  return true
end

local function copy_target(target)
  if target.kind == "degrees" then
    local degrees = {}
    for index, degree in ipairs(target.degrees) do degrees[index] = degree end
    return {kind = "degrees", degrees = degrees}
  elseif target.kind == "chord" then
    return {kind = "chord", group_id = target.group_id}
  end
  return {kind = target.kind}
end

local function copy_common(value, result)
  result.mode = value.mode
  result.anchor = value.anchor
  result.amount = value.amount
  result.accent = value.accent
  result.gap = value.gap
  result.seed = value.seed
  result.ranking_version = value.ranking_version
  result.cycles = value.cycles
  result.shape = value.shape
  result.percentages = {}
  for index = 1, value.cycles do result.percentages[index] = value.percentages[index] end
  result.variation = value.variation
  result.keep_anchor_pitch = value.keep_anchor_pitch
  result.target = copy_target(value.target)
  return result
end

-- Canonical, idempotent form of a saved or drafted configuration, as a fresh
-- table (the argument is never changed or aliased). Version 1 is validated with
-- its own validator; only its recognized semantic fields are copied into a new
-- v2 configuration with every new field at its default, discarding every other
-- key, including nested ones and keys that collide with v2 field names. Version
-- 2 must pass the closed validator. Any other value is rejected.
function config.canonicalize(value, channel)
  if type(value) ~= "table" then return nil, "merge schema version" end
  if value.schema_version == 1 then
    local ok, reason = config.validate_v1(value)
    if not ok then return nil, reason end
    return copy_common(value, config.new())
  end
  local ok, reason = config.validate(value, channel)
  if not ok then return nil, reason end
  local result = copy_common(value, config.new())
  result.interlock = {leader = value.interlock.leader, window = value.interlock.window}
  result.space = {leader = value.space.leader, release = value.space.release}
  result.fragments = {size = value.fragments.size, keep_anchor = value.fragments.keep_anchor}
  -- An inactive group has no semantics: markers Off stores no group.
  result.structure = {markers = value.structure.markers,
    group_id = value.structure.markers ~= "off" and value.structure.group_id or nil}
  return result
end

return config
