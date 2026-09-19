-- Pure capture-bank construction for Rhythm Doctor.  No capture, worker, file or
-- UI dependency belongs here.  `sample_index` is authoritative for every event.
-- See docs/rhythm-doctor/PLAN.md, "Four bars, clock and quantisation".
local Bank = {
  VERSION = 2,
  LANES = { "BD", "SD", "CYM", "BASS" },
  WINDOW_CELLS = 64,
  -- 45 seconds × an explicit 100 retained candidates/second/lane × 5 lanes.
  -- A worker exceeding this contract is rejected before allocating bank copies.
  MAX_CANDIDATES = 22500,
  MAX_CAPTURE_SECONDS = 45,
  MIN_BPM = 40,
  MAX_BPM = 240,
}

local function copy(value)
  if type(value) ~= "table" then return value end
  local out = {}
  for k, v in pairs(value) do out[k] = copy(v) end
  return out
end

local function valid_lane(lane)
  for _, name in ipairs(Bank.LANES) do if name == lane then return true end end
  return false
end

local function number(value)
  return type(value) == "number" and value == value and value ~= math.huge and value ~= -math.huge
end
local function integer(value) return number(value) and value >= 0 and math.floor(value) == value end

local function failure(code, detail)
  return nil, { code = code, detail = detail }
end

local function timeline_length(args)
  local samples_per_cell = args.sample_rate * 15 / args.bpm
  return math.floor((args.capture_end_sample - args.origin_sample) / samples_per_cell), samples_per_cell
end

local function empty_lanes()
  local lanes = {}
  for _, lane in ipairs(Bank.LANES) do lanes[lane] = {} end
  return lanes
end

local function normalized_sensitivities(values)
  local out = {}
  for _, lane in ipairs(Bank.LANES) do
    local value = values and values[lane] or 0
    if not number(value) or value < 0 or value > 1 then return nil, lane end
    out[lane] = value
  end
  return out
end

local function quantize_candidate(candidate, origin_sample, samples_per_cell, cells)
  -- The right-side limit is exclusive.  Keeping it that way prevents a partial
  -- final cell from being silently manufactured by the display window.
  if candidate.sample_index < origin_sample or candidate.sample_index >= origin_sample + cells * samples_per_cell then
    return nil
  end
  return math.min(cells - 1, math.floor((candidate.sample_index - origin_sample) / samples_per_cell + .5))
end

local function rebuild(bank)
  local lanes = empty_lanes()
  local collision_count = 0
  local retained_counts = empty_lanes()
  -- Collision diagnostics describe the retained detector candidates, not merely
  -- the candidates visible at the current sensitivity.  Thus lowering a
  -- threshold can reveal a candidate without changing its original diagnosis.
  for _, candidate in ipairs(bank.candidates) do
    if candidate.cell ~= nil then
      local step = candidate.cell + 1
      retained_counts[candidate.lane][step] = (retained_counts[candidate.lane][step] or 0) + 1
    end
  end
  for _, counts in pairs(retained_counts) do
    for _, count in pairs(counts) do collision_count = collision_count + math.max(0, count - 1) end
  end
  for _, candidate in ipairs(bank.candidates) do
    if candidate.cell ~= nil and candidate.confidence >= bank.sensitivities[candidate.lane] then
      local step = candidate.cell + 1
      local previous = lanes[candidate.lane][step]
      if previous then
        if candidate.velocity > previous.velocity then
          lanes[candidate.lane][step] = {
            velocity = candidate.velocity, confidence = candidate.confidence,
            sample_index = candidate.sample_index, collision_count = (retained_counts[candidate.lane][step] or 1) - 1,
          }
        else
          previous.collision_count = (retained_counts[candidate.lane][step] or 1) - 1
        end
      else
        lanes[candidate.lane][step] = {
          velocity = candidate.velocity, confidence = candidate.confidence,
          sample_index = candidate.sample_index, collision_count = (retained_counts[candidate.lane][step] or 1) - 1,
        }
      end
    end
  end
  bank.lanes, bank.collision_count = lanes, collision_count
  return bank
end

-- Build validates an already-retained capture and candidate list.  Candidates are
-- retained with their first quantised `cell` so changing sensitivity never moves a
-- hit.  The returned value has no metatable and is safe to serialize.
function Bank.build(args)
  args = args or {}
  if type(args.project_id) ~= "string" or args.project_id == "" then return failure("INVALID_PROJECT") end
  if not integer(args.sample_rate) or args.sample_rate <= 0 then return failure("INVALID_SAMPLE_RATE") end
  if not integer(args.capture_start_sample) or not integer(args.capture_end_sample) or not integer(args.origin_sample) then
    return failure("INVALID_SAMPLE_RANGE")
  end
  if args.capture_end_sample < args.capture_start_sample or args.origin_sample < args.capture_start_sample or args.origin_sample > args.capture_end_sample then
    return failure("INVALID_SAMPLE_RANGE")
  end
  if args.capture_end_sample - args.capture_start_sample > args.sample_rate * Bank.MAX_CAPTURE_SECONDS then
    return failure("CAPTURE_TOO_LONG")
  end
  if not number(args.bpm) or args.bpm < Bank.MIN_BPM or args.bpm > Bank.MAX_BPM then return failure("UNSUPPORTED_BPM") end
  local cells, samples_per_cell = timeline_length(args)
  if cells < Bank.WINDOW_CELLS then return failure("NOT_ENOUGH_ALIGNED_AUDIO") end
  local sensitivities, bad_lane = normalized_sensitivities(args.sensitivities)
  if not sensitivities then return failure("INVALID_SENSITIVITY", bad_lane) end
  if args.candidates ~= nil and type(args.candidates) ~= "table" then return failure("INVALID_CANDIDATE") end
  if args.candidates and #args.candidates > Bank.MAX_CANDIDATES then return failure("CANDIDATE_LIMIT") end
  local candidates = {}
  for index, event in ipairs(args.candidates or {}) do
    if type(event) ~= "table" or not valid_lane(event.lane) or not integer(event.sample_index) or
        not number(event.velocity) or event.velocity < 1 or event.velocity > 127 or not number(event.confidence) or
        event.confidence < 0 or event.confidence > 1 then return failure("INVALID_CANDIDATE", index) end
    local item = copy(event)
    item.velocity = math.floor(item.velocity + .5)
    item.cell = quantize_candidate(item, args.origin_sample, samples_per_cell, cells)
    if item.cell ~= nil then candidates[#candidates + 1] = item end
  end
  local bank = {
    version = Bank.VERSION, project_id = args.project_id,
    generation = args.generation or 0, analysis_revision = args.analysis_revision or 0,
    tempo_mode = args.tempo_mode or "auto", bpm = args.bpm,
    tempo_candidates = copy(args.tempo_candidates or {}), tempo_confidence = args.tempo_confidence,
    meter = args.meter or "4/4", source = copy(args.source or {}),
    capture_start_sample = args.capture_start_sample, capture_end_sample = args.capture_end_sample,
    origin_sample = args.origin_sample, sample_rate = args.sample_rate,
    samples_per_cell = samples_per_cell, timeline_cells = cells,
    timeline_end_sample = args.origin_sample + cells * samples_per_cell,
    window_start = 0, sensitivities = sensitivities, candidates = candidates,
    detector = copy(args.detector or {}), quality_warnings = copy(args.quality_warnings or {}),
  }
  return rebuild(bank)
end

-- Boundary validation for a worker result.  This intentionally checks no model
-- quality claim: it only prevents incomplete/mismatched data becoming READY.
function Bank.valid_ready(bank, expected)
  local function invalid() return false, "INVALID_BANK" end
  if type(bank) ~= "table" or bank.version ~= Bank.VERSION or
      type(bank.project_id) ~= "string" or bank.project_id == "" or
      not integer(bank.generation) or not integer(bank.analysis_revision) or
      not integer(bank.sample_rate) or bank.sample_rate == 0 or
      not integer(bank.capture_start_sample) or not integer(bank.capture_end_sample) or
      not integer(bank.origin_sample) or not number(bank.bpm) or
      bank.bpm < Bank.MIN_BPM or bank.bpm > Bank.MAX_BPM then return invalid() end
  if bank.origin_sample < bank.capture_start_sample or bank.capture_end_sample < bank.origin_sample or
      bank.capture_end_sample - bank.capture_start_sample > bank.sample_rate * Bank.MAX_CAPTURE_SECONDS then return invalid() end
  local cells, spacing = timeline_length(bank)
  if cells < Bank.WINDOW_CELLS or bank.timeline_cells ~= cells or bank.samples_per_cell ~= spacing or
      bank.timeline_end_sample ~= bank.origin_sample + cells * spacing or
      not integer(bank.window_start) or bank.window_start > cells - Bank.WINDOW_CELLS then return invalid() end
  if type(expected) == "table" and (bank.project_id ~= expected.project_id or bank.generation ~= expected.generation or
      bank.analysis_revision ~= expected.analysis_revision) then return invalid() end
  if bank.meter ~= "4/4" or (bank.tempo_mode ~= "auto" and bank.tempo_mode ~= "manual") or
      type(bank.sensitivities) ~= "table" or type(bank.lanes) ~= "table" or
      type(bank.candidates) ~= "table" or #bank.candidates > Bank.MAX_CANDIDATES then return invalid() end
  local function valid_hit(hit, cell)
    return type(hit) == "table" and integer(hit.velocity) and hit.velocity >= 1 and hit.velocity <= 127 and
      number(hit.confidence) and hit.confidence >= 0 and hit.confidence <= 1 and integer(hit.sample_index) and
      quantize_candidate(hit, bank.origin_sample, spacing, cells) == cell
  end
  for lane in pairs(bank.lanes) do if not valid_lane(lane) then return invalid() end end
  for _, lane in ipairs(Bank.LANES) do
    local threshold = bank.sensitivities[lane]
    if not number(threshold) or threshold < 0 or threshold > 1 or type(bank.lanes[lane]) ~= "table" then return invalid() end
    for step, hit in pairs(bank.lanes[lane]) do
      if not integer(step) or step < 1 or step > cells or not valid_hit(hit, step - 1) then return invalid() end
    end
  end
  local count = 0
  for index, hit in pairs(bank.candidates) do
    count = count + 1
    if not integer(index) or index < 1 or index > #bank.candidates or type(hit) ~= "table" or
        not valid_lane(hit.lane) or not integer(hit.cell) or hit.cell >= cells or not valid_hit(hit, hit.cell) then return invalid() end
  end
  if count ~= #bank.candidates then return invalid() end
  return true
end

function Bank.with_sensitivity(bank, lane, sensitivity)
  if type(bank) ~= "table" or not valid_lane(lane) or not number(sensitivity) or sensitivity < 0 or sensitivity > 1 then
    return nil, { code = "INVALID_SENSITIVITY" }
  end
  local changed = copy(bank)
  changed.sensitivities[lane] = sensitivity
  return rebuild(changed)
end

function Bank.window_bounds(bank)
  if type(bank) ~= "table" or not integer(bank.timeline_cells) or bank.timeline_cells < Bank.WINDOW_CELLS then return nil, { code = "NOT_ENOUGH_ALIGNED_AUDIO" } end
  return 0, bank.timeline_cells - Bank.WINDOW_CELLS
end

function Bank.move_window(bank, desired_start)
  local low, high = Bank.window_bounds(bank)
  if low == nil then return nil, high end
  if not number(desired_start or bank.window_start or 0) then return nil, { code = "INVALID_WINDOW_START" } end
  local start = math.max(low, math.min(high, math.floor(desired_start or bank.window_start or 0)))
  return start, start == low, start == high
end

function Bank.with_window_start(bank, desired_start)
  local start, at_start, at_end = Bank.move_window(bank, desired_start)
  if not start then return nil, at_start end
  -- Timelines/candidates are immutable after analysis. Scrolling changes only
  -- this lightweight header; callers must treat shared bank arrays as read-only.
  -- `window` still copies displayed hit records, so UI paint previews cannot
  -- mutate a retained candidate through a view.
  local changed = {}
  for key, value in pairs(bank) do changed[key] = value end
  changed.window_start = start
  return changed, at_start, at_end
end

function Bank.window(bank, lane, requested_start)
  if not valid_lane(lane) then return nil, { code = "INVALID_LANE" } end
  local start, at_start, at_end = Bank.move_window(bank, requested_start)
  if not start then return nil, at_start end
  local cells = {}
  for step = 1, Bank.WINDOW_CELLS do
    local hit = bank.lanes[lane][start + step]
    cells[step] = hit and copy(hit) or nil
  end
  return { lane = lane, start = start, cells = cells, cell_count = Bank.WINDOW_CELLS, at_start = at_start, at_end = at_end,
    end_cell = start + Bank.WINDOW_CELLS - 1 }
end

return Bank
