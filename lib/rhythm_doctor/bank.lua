-- Pure capture-bank construction for Rhythm Doctor.  No capture, worker, file or
-- UI dependency belongs here.  `sample_index` is authoritative for every event.
-- See docs/rhythm-doctor/PLAN.md, "Four bars, clock and quantisation".
local Bank = {
  VERSION = 4,
  -- The lane set the on-device backend produces. It is a DEFAULT, not the only
  -- possibility: the remote analysis server separates a kit and returns ten
  -- lanes, and a bank has to hold whichever set its own analysis produced or
  -- the extra lanes are discarded on arrival.
  LANES = { "BD", "SD", "CYM" },
  WINDOW_CELLS = 64,
  -- 45 seconds × an explicit 100 retained candidates/second/lane × 5 lanes.
  -- A worker exceeding this contract is rejected before allocating bank copies.
  MAX_CANDIDATES = 22500,
  MAX_CAPTURE_SECONDS = 45,
  MIN_BPM = 40,
  -- The tempo the detector reports when it cannot measure one; the Finish
  -- gate needs a tempo before any analysis exists.
  DEFAULT_BPM = 120,
  -- The slowest tempo the detector will report. A capture long enough for a
  -- window at this tempo is long enough at every tempo it can report, so it
  -- is the only span Finish can promise before a tempo has been measured.
  SLOWEST_SUPPORTED_BPM = 40,
  MAX_BPM = 240,
}

local function copy(value)
  if type(value) ~= "table" then return value end
  local out = {}
  for k, v in pairs(value) do out[k] = copy(v) end
  return out
end

local function valid_lane(lane, names)
  for _, name in ipairs(names or Bank.LANES) do if name == lane then return true end end
  return false
end

-- A declared lane set: names only, each a non-empty plain word, no repeats.
local function lane_names(value)
  if value == nil then return Bank.LANES end
  if type(value) ~= "table" or #value == 0 or #value > 32 then return nil end
  local seen, out = {}, {}
  for index, name in ipairs(value) do
    if type(name) ~= "string" or not name:match("^[A-Z][A-Z0-9_]*$") or #name > 16 then return nil end
    if seen[name] then return nil end
    seen[name], out[index] = true, name
  end
  return out
end

local function number(value)
  return type(value) == "number" and value == value and value ~= math.huge and value ~= -math.huge
end
local function integer(value) return number(value) and value >= 0 and math.floor(value) == value end

local function failure(code, detail)
  return nil, { code = code, detail = detail }
end

-- Derived geometry is a float and a project file is text: Lua writes fourteen
-- significant digits, so a bank read back from disk is close to the one that
-- was written rather than identical to it. A real capture stored 15046.530612245
-- where the double was 15046.530612244898, and demanding equality rejected the
-- bank -- and with it the whole project. This is tight enough that a spacing
-- which disagrees with the tempo is still caught, and loose enough to survive
-- being written down.
local function same_measure(actual, expected)
  if type(actual) ~= "number" or actual ~= actual or type(expected) ~= "number" then return false end
  local scale = math.abs(expected)
  return math.abs(actual - expected) <= 1e-9 * (scale > 1 and scale or 1)
end

local function timeline_length(args)
  local samples_per_cell = args.sample_rate * 15 / args.bpm
  return math.floor((args.capture_end_sample - args.origin_sample) / samples_per_cell), samples_per_cell
end

local function empty_lanes(names)
  local lanes = {}
  for _, lane in ipairs(names) do lanes[lane] = {} end
  return lanes
end

local function normalized_sensitivities(values, names)
  local out = {}
  for _, lane in ipairs(names) do
    local value = values and values[lane] or 0
    if not number(value) or value < 0 or value > 1 then return nil, lane end
    out[lane] = value
  end
  return out
end

-- The cell the phrase start occupies, clamped to a window start the UI can
-- actually adopt. A phrase beginning three bars from the end of the capture is
-- a real detection, but jumping there would show a view running off the end of
-- the timeline, which reads as a fault rather than as the end of the take.
local function phrase_cell(sample, origin_sample, samples_per_cell, cells)
  if not number(sample) or sample < origin_sample then return 0 end
  local cell = math.floor((sample - origin_sample) / samples_per_cell + .5)
  return math.max(0, math.min(cell, cells - 1))
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
  local names = bank.lane_names or Bank.LANES
  local lanes = empty_lanes(names)
  local collision_count = 0
  local retained_counts = empty_lanes(names)
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
-- A bank needs at least WINDOW_CELLS cells, and a cell spans
-- sample_rate * 15 / bpm samples, so the capture must run this long before an
-- analysis can produce a browsable window. Tying the Finish gate to this rather
-- than a fixed number keeps the UI and the bank rule from drifting apart.
function Bank.minimum_capture_seconds(bpm)
  if type(bpm) ~= "number" or bpm ~= bpm or bpm < Bank.MIN_BPM or bpm > Bank.MAX_BPM then return nil end
  return Bank.WINDOW_CELLS * 15 / bpm
end

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
  local names = lane_names(args.lane_names)
  if not names then return failure("INVALID_LANE_SET") end
  local sensitivities, bad_lane = normalized_sensitivities(args.sensitivities, names)
  if not sensitivities then return failure("INVALID_SENSITIVITY", bad_lane) end
  if args.candidates ~= nil and type(args.candidates) ~= "table" then return failure("INVALID_CANDIDATE") end
  if args.candidates and #args.candidates > Bank.MAX_CANDIDATES then return failure("CANDIDATE_LIMIT") end
  local candidates = {}
  for index, event in ipairs(args.candidates or {}) do
    if type(event) ~= "table" or not valid_lane(event.lane, names) or not integer(event.sample_index) or
        not number(event.velocity) or event.velocity < 1 or event.velocity > 127 or not number(event.confidence) or
        event.confidence < 0 or event.confidence > 1 then return failure("INVALID_CANDIDATE", index) end
    local item = copy(event)
    item.velocity = math.floor(item.velocity + .5)
    item.cell = quantize_candidate(item, args.origin_sample, samples_per_cell, cells)
    if item.cell ~= nil then candidates[#candidates + 1] = item end
  end
  local bank = {
    version = Bank.VERSION, project_id = args.project_id, lane_names = names,
    generation = args.generation or 0, analysis_revision = args.analysis_revision or 0,
    tempo_mode = args.tempo_mode or "auto", bpm = args.bpm,
    tempo_candidates = copy(args.tempo_candidates or {}), tempo_confidence = args.tempo_confidence,
    -- Only an explicit false means the tempo was not detected: a bank that
    -- says nothing predates the flag and must not be relabelled as a guess.
    tempo_detected = args.tempo_detected ~= false,
    meter = args.meter or "4/4",
    source = copy(args.source or (args.beat_positions and { beat_positions = args.beat_positions }) or {}),
    capture_start_sample = args.capture_start_sample, capture_end_sample = args.capture_end_sample,
    origin_sample = args.origin_sample, sample_rate = args.sample_rate,
    samples_per_cell = samples_per_cell, timeline_cells = cells,
    timeline_end_sample = args.origin_sample + cells * samples_per_cell,
    window_start = 0, sensitivities = sensitivities, candidates = candidates,
    phrase_start_cell = phrase_cell(args.phrase_start_sample, args.origin_sample, samples_per_cell, cells),
    phrase_confidence = number(args.phrase_confidence) and
      math.max(0, math.min(1, args.phrase_confidence)) or 0,
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
  if cells < Bank.WINDOW_CELLS or bank.timeline_cells ~= cells or
      not same_measure(bank.samples_per_cell, spacing) or
      not same_measure(bank.timeline_end_sample, bank.origin_sample + cells * spacing) or
      not integer(bank.window_start) or bank.window_start > cells - Bank.WINDOW_CELLS then return invalid() end
  if type(expected) == "table" and (bank.project_id ~= expected.project_id or bank.generation ~= expected.generation or
      bank.analysis_revision ~= expected.analysis_revision) then return invalid() end
  if not integer(bank.phrase_start_cell) or bank.phrase_start_cell >= cells or
      not number(bank.phrase_confidence) or bank.phrase_confidence < 0 or bank.phrase_confidence > 1 then
    return invalid()
  end
  if bank.meter ~= "4/4" or (bank.tempo_mode ~= "auto" and bank.tempo_mode ~= "manual") or
      type(bank.sensitivities) ~= "table" or type(bank.lanes) ~= "table" or
      type(bank.candidates) ~= "table" or #bank.candidates > Bank.MAX_CANDIDATES then return invalid() end
  local function valid_hit(hit, cell)
    return type(hit) == "table" and integer(hit.velocity) and hit.velocity >= 1 and hit.velocity <= 127 and
      number(hit.confidence) and hit.confidence >= 0 and hit.confidence <= 1 and integer(hit.sample_index) and
      quantize_candidate(hit, bank.origin_sample, spacing, cells) == cell
  end
  local names = lane_names(bank.lane_names)
  if not names then return invalid() end
  for lane in pairs(bank.lanes) do if not valid_lane(lane, names) then return invalid() end end
  for _, lane in ipairs(names) do
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
        not valid_lane(hit.lane, names) or not integer(hit.cell) or hit.cell >= cells or not valid_hit(hit, hit.cell) then return invalid() end
  end
  if count ~= #bank.candidates then return invalid() end
  return true
end

function Bank.with_sensitivity(bank, lane, sensitivity)
  if type(bank) ~= "table" or not valid_lane(lane, bank.lane_names) or not number(sensitivity) or sensitivity < 0 or sensitivity > 1 then
    return nil, { code = "INVALID_SENSITIVITY" }
  end
  local changed = copy(bank)
  changed.sensitivities[lane] = sensitivity
  return rebuild(changed)
end

-- Where the window must sit to show the phrase. Kept here rather than in the
-- UI so that the clamp and the bank's own window rule cannot disagree.
function Bank.phrase_window_start(bank)
  local low, high = Bank.window_bounds(bank)
  if low == nil then return nil, high end
  return math.max(low, math.min(high, bank.phrase_start_cell or 0))
end

-- Bring a bank written before phrase alignment up to the current schema. A
-- player's saved captures predate this feature and must keep loading; the
-- upgraded bank claims no phrase, which is true, rather than inventing one.
function Bank.upgrade(bank)
  if type(bank) ~= "table" then return nil end
  if bank.version == Bank.VERSION then return bank end
  if bank.version ~= 2 and bank.version ~= 3 then return nil end
  local changed = copy(bank)
  -- A bank written before lane sets were data had whatever lanes the product
  -- had then, which for anything saved before BASS was withdrawn is four.
  -- Keeping that lane would resurrect one removed because it only ever
  -- duplicated BD; refusing the bank would lose the player their whole
  -- project over it. The lane is dropped and the rest of the bank loads.
  if changed.lane_names == nil then
    changed.lane_names = { table.unpack(Bank.LANES) }
    for lane in pairs(changed.lanes or {}) do
      if not valid_lane(lane, changed.lane_names) then changed.lanes[lane] = nil end
    end
    for lane in pairs(changed.sensitivities or {}) do
      if not valid_lane(lane, changed.lane_names) then changed.sensitivities[lane] = nil end
    end
    local kept = {}
    for _, candidate in ipairs(changed.candidates or {}) do
      if valid_lane(candidate.lane, changed.lane_names) then kept[#kept + 1] = candidate end
    end
    changed.candidates = kept
  end
  if bank.version == 2 then changed.phrase_start_cell, changed.phrase_confidence = 0, 0 end
  changed.version = Bank.VERSION
  changed.source = type(changed.source) == "table" and changed.source or {}
  return changed
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
  if type(bank) ~= "table" or not valid_lane(lane, bank.lane_names) then return nil, { code = "INVALID_LANE" } end
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
