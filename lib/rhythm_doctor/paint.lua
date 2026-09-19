-- Pure, pinned 64-cell painting.  Applying returns a copy; the UI integration
-- owns source mutation, history hooks and channel reprojection.
local Paint = { WINDOW_CELLS = 64, POLICIES = { toggle = true, add = true, replace = true } }
local function copy(value)
  if type(value) ~= "table" then return value end
  local out = {}; for k, v in pairs(value) do out[k] = copy(v) end; return out
end
local function same_target(a, b)
  return a and b and a.project_id == b.project_id and a.song_slot == b.song_slot and a.pattern_id == b.pattern_id and a.revision == b.revision
end
local function same_value(a, b)
  if type(a) ~= type(b) then return false end
  if type(a) ~= "table" then return a == b end
  for k, value in pairs(a) do if not same_value(value, b[k]) then return false end end
  for k in pairs(b) do if a[k] == nil then return false end end
  return true
end
local function shifted_cells(cells, shift)
  local out = {}; shift = ((shift or 0) % Paint.WINDOW_CELLS + Paint.WINDOW_CELLS) % Paint.WINDOW_CELLS
  for source = 1, Paint.WINDOW_CELLS do out[((source - 1 + shift) % Paint.WINDOW_CELLS) + 1] = cells[source] end
  return out
end
function Paint.preview(spec)
  if type(spec) ~= "table" or not Paint.POLICIES[spec.policy] or type(spec.target) ~= "table" or type(spec.cells) ~= "table" then return nil, { code = "INVALID_PREVIEW" } end
  local function finite_integer(value) return type(value)=="number" and value==value and value~=math.huge and value~=-math.huge and math.floor(value)==value end
  if type(spec.project_id) ~= "string" or not finite_integer(spec.generation) or not finite_integer(spec.analysis_revision) or not finite_integer(spec.window_revision) or
      spec.target.project_id ~= spec.project_id or spec.target.song_slot == nil or spec.target.pattern_id == nil or not finite_integer(spec.target.revision) then return nil, { code = "INVALID_PREVIEW" } end
  if spec.lane ~= "BD" and spec.lane ~= "SD" and spec.lane ~= "HH" and spec.lane ~= "TOM" and spec.lane ~= "BASS" then return nil, { code = "INVALID_PREVIEW" } end
  local shift=spec.shift or 0
  if type(shift) ~= "number" or shift ~= shift or shift == math.huge or shift == -math.huge or math.floor(shift) ~= shift or not finite_integer(spec.window_start) or spec.window_start < 0 then return nil, { code = "INVALID_PREVIEW" } end
  for step, hit in pairs(spec.cells) do
    if type(step) ~= "number" or math.floor(step) ~= step or step < 1 or step > Paint.WINDOW_CELLS or (hit ~= nil and (type(hit) ~= "table" or type(hit.velocity) ~= "number" or hit.velocity ~= hit.velocity or math.floor(hit.velocity) ~= hit.velocity or hit.velocity < 1 or hit.velocity > 127)) then return nil, { code = "INVALID_PREVIEW" } end
  end
  local preview = copy(spec); preview.shifted_cells = shifted_cells(spec.cells, spec.shift); preview.cells = nil
  preview.requires_replace_confirmation = preview.policy == "replace"
  return preview
end
function Paint.valid_preview(preview, context)
  return type(preview) == "table" and type(context) == "table" and preview.project_id == context.project_id and
    preview.generation == context.generation and preview.analysis_revision == context.analysis_revision and
    preview.window_revision == context.window_revision and preview.lane == context.lane and preview.window_start == context.window_start and
    preview.shift == context.shift and preview.policy == context.policy and same_value(preview.thresholds or {}, context.thresholds or {}) and
    same_target(preview.target, context.target)
end
function Paint.apply(source, preview, adapter)
  if type(source) ~= "table" or type(preview) ~= "table" or not Paint.POLICIES[preview.policy] then return nil, { code = "INVALID_PAINT" } end
  if preview.target and source.revision ~= preview.target.revision then return nil, { code = "PATTERN_CHANGED" } end
  adapter = adapter or { trig_field = "trigs", velocity_field = "velocities", length_field = "lengths", on = true, off = false }
  if type(adapter) ~= "table" or type(adapter.trig_field) ~= "string" or type(adapter.velocity_field or "velocities") ~= "string" or
      type(adapter.length_field or "lengths") ~= "string" or adapter.on == nil or adapter.off == nil or type(source[adapter.trig_field]) ~= "table" then
    return nil, { code = "INVALID_TRIG_ADAPTER" }
  end
  local velocity_field, length_field = adapter.velocity_field or "velocities", adapter.length_field or "lengths"
  local after = copy(source)
  after[adapter.trig_field], after[velocity_field], after[length_field] = copy(source[adapter.trig_field]), copy(source[velocity_field] or {}), copy(source[length_field] or {})
  local trigs = after[adapter.trig_field]
  local velocities, lengths = after[velocity_field], after[length_field]
  local hits = preview.shifted_cells or shifted_cells(preview.cells or {}, preview.shift)
  for step = 1, Paint.WINDOW_CELLS do
    local hit = hits[step]
    if preview.policy == "replace" then
      trigs[step], lengths[step] = hit and adapter.on or adapter.off, hit and 1 or 0
      if hit then velocities[step] = hit.velocity end
    elseif hit then
      if preview.policy == "toggle" and trigs[step] == adapter.on then trigs[step], lengths[step] = adapter.off, 0
      else
        local was_on = trigs[step] == adapter.on
        trigs[step], velocities[step] = adapter.on, hit.velocity
        if not was_on then lengths[step] = 1 end
      end
    end
  end
  return after
end
return Paint
