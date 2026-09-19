local harmony_state = include("mosaic/lib/harmony/state")

local pattern_harmony = {}
local role_order = {bass=1, inner1=2, inner2=3, inner3=4, top=5}

local function target_identity(merge)
  if not merge or merge.mode=="off" then return "off" end
  local target = merge.target or {kind="legacy"}
  local parts = {tostring(merge.keep_anchor_pitch == true), target.kind or "legacy"}
  if target.kind == "degrees" then
    for _, degree in ipairs(target.degrees or {}) do parts[#parts + 1] = degree end
  elseif target.kind == "chord" then
    parts[#parts + 1] = target.group_id or "missing"
  end
  return table.concat(parts, ",")
end

function pattern_harmony.binding_key(channel, effective_merge)
  local patterns = {}
  for number, enabled in pairs(channel.selected_patterns or {}) do
    if enabled then patterns[#patterns + 1] = number end
  end
  table.sort(patterns)
  return table.concat({
    "pattern-binding-v1",
    table.concat(patterns, ","),
    channel.note_merge_mode or "average",
    target_identity(effective_merge or channel.musical_merge)
  }, "|")
end

local function role_config(channel, role_name, material_id)
  local value = channel.roles["v" .. role_order[role_name]]
  if not value or not value.enabled then return nil end
  local result = {}
  for key, item in pairs(value) do result[key] = item end
  result.id = role_name
  result.material_id = material_id
  return result
end

function pattern_harmony.prepare(song, channel_number, source_revision, binding, resolved, channel, conflicts)
  local map = channel.pattern_maps and channel.pattern_maps[binding]
  if not map then return {status="raw", binding=binding, mapped={}} end
  local per_role, mapped, alias_conflict = {}, {}, false
  for source, role in pairs(map.assignments or {}) do
    local numeric = tonumber(source)
    local pitch = resolved[numeric]
    if conflicts and conflicts[numeric] then
      mapped[numeric]=role
      return {status="source_conflict",reason="source_conflict",binding=binding,mapped=mapped,
        fallback=channel.fallback}
    end
    if pitch ~= nil then
      local pc = ((pitch % 12) + 12) % 12
      mapped[numeric] = role
      if per_role[role] and per_role[role].pc ~= pc then alias_conflict=true end
      per_role[role] = per_role[role] or {pc=pc, sources={}}
      per_role[role].sources[#per_role[role].sources + 1] = numeric
    end
  end
  if alias_conflict then return {status="alias_conflict",binding=binding,mapped=mapped,
    fallback=channel.fallback} end
  local material, roles, entry_previous = {}, {}, {}
  for _, role in ipairs({"bass","inner1","inner2","inner3","top"}) do
    local entry = per_role[role]
    if entry then
      local id = "pattern:" .. role
      material[#material + 1] = {id=id, pc=entry.pc, required=true}
      local configured = role_config(channel, role, id)
      if configured then roles[#roles + 1] = configured;entry_previous[role]=resolved[entry.sources[1]] end
    end
  end
  if #material == 0 then return {status="raw", binding=binding, mapped={}} end
  if #roles ~= #material then
    return {status="no_solution", reason="disabled_role", binding=binding,
      mapped=mapped, fallback=channel.fallback}
  end
  local revision = table.concat({binding, map.revision or 0, source_revision}, "|")
  local result = harmony_state.prepare_pattern(song, channel_number, revision, material, roles, channel,entry_previous,
    per_role.bass ~= nil)
  result.binding, result.mapped, result.fallback = binding, mapped, channel.fallback
  result.role_pitches = result.role_pitches or {}
  return result
end

function pattern_harmony.pitch_for(frame, source_value, legacy_pitch)
  local role = frame and frame.mapped and frame.mapped[source_value]
  if not role then return legacy_pitch end
  if frame.status ~= "ok" then
    return frame.fallback == "legacy" and legacy_pitch or nil
  end
  return frame.role_pitches[role]
end

return pattern_harmony
