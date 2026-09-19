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
    schema_version = 1,
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
    target = {kind = "legacy"}
  }
end

function config.validate(value)
  if type(value) ~= "table" or value.schema_version ~= 1 then
    return nil, "merge schema version"
  end
  if value.mode ~= "off" and value.mode ~= "foundation" then return nil, "merge mode" end
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

return config
