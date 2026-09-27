-- MM-12 Space gate inputs (docs/musical-merge-extensions-plan.md §6.1, §1.4).
--
-- The articulation snapshot captures, for every playable position of a leader,
-- the strum tail its planned voices can reach: resolved from the channel's
-- values, per-step overrides, parameter-slot values and stock precedence by the
-- same reader step playback uses (musical_resolution/articulation), and timed
-- by the same chord ordering and strum descriptor. Reading it executes no
-- parameter lock, sends nothing, schedules nothing and consumes no RNG. An
-- input whose tail cannot be computed without executing playback (a value that
-- depends on live modulation, a division index outside its table, a
-- non-finite value) makes the whole record unavailable, never zero.
--
-- Every duration is an exact reduced fraction in leader steps. Working-pattern
-- values are floats; `rational_of` recovers the fraction a float stands for
-- (the smallest-denominator convergent within 1e-9 of a step), and an
-- unrecoverable value is unavailable.
local common_time = include("mosaic/lib/musical_merge/common_time")
local articulation = include("mosaic/lib/musical_resolution/articulation")
local strum_descriptor = include("mosaic/lib/musical_resolution/strum_descriptor")
local chord_order = include("mosaic/lib/musical_resolution/chord_order")
local chord_timing = include("mosaic/lib/clock/chord_timing")
local stock_parameter = include("mosaic/lib/musical_resolution/stock_parameter")

local gate = {}

gate.UNAVAILABLE = "GATE INPUT UNAVAILABLE"

local MAX_DENOMINATOR = 1 << 20
local TOLERANCE = 1e-9
local ZERO = {0, 1}

local rational, add, mul, compare = common_time.rational, common_time.add, common_time.mul, common_time.compare

local function finite(value)
  return type(value) == "number" and value == value and value ~= math.huge and value ~= -math.huge
end

-- The exact fraction a stored float stands for, or nil.
function gate.rational_of(value)
  if not finite(value) then return nil end
  local whole = math.tointeger(value)
  if whole then return {whole, 1} end
  local sign = value < 0 and -1 or 1
  local magnitude = value * sign
  if magnitude >= 2 ^ 40 then return nil end
  local h0, h1, k0, k1 = 0, 1, 1, 0
  local remainder = magnitude
  for _ = 1, 64 do
    local term = math.floor(remainder)
    term = math.tointeger(term)
    if not term then return nil end
    h0, h1 = h1, term * h1 + h0
    k0, k1 = k1, term * k1 + k0
    if k1 > MAX_DENOMINATOR then return nil end
    if math.abs(magnitude - h1 / k1) <= TOLERANCE * math.max(1, magnitude) then
      return rational(sign * h1, k1)
    end
    local fraction = remainder - term
    if fraction <= 0 then return nil end
    remainder = 1 / fraction
  end
  return nil
end
local rational_of = gate.rational_of

-- Stock reads for the snapshot: the playback readers' precedence with pure
-- parameter access. A control whose getter or mapping is not norns core
-- follows live modulation (step.lua reads such a control anew on every
-- step), so it is unavailable.
local core_sources = {
  get = "core/params/control.lua",
  map_value = "core/params/control.lua",
  map = "core/controlspec.lua",
}

local function is_core(fn_value, source)
  if type(fn_value) ~= "function" then return false end
  local info = debug.getinfo(fn_value, "S")
  local defined = info and info.source or ""
  return defined:sub(-#source) == source
end

local function new_reader()
  local reader = {failed = false}

  local function param_value(param_id)
    local lookup = params.lookup
    local index = lookup and lookup[param_id]
    local param = index and params.params[index]
    if param then
      if param.t == 3 then
        local spec = param.controlspec
        if spec == nil or not is_core(param.get, core_sources.get) or
          not is_core(param.map_value, core_sources.map_value) or not is_core(spec.map, core_sources.map) then
          reader.failed = true
          return nil
        end
      end
      return param:get(), param
    end
    local ok, value = pcall(params.get, params, param_id)
    if not ok then reader.failed = true; return nil end
    local found, looked = pcall(params.lookup_param, params, param_id)
    return value, found and looked or nil
  end

  function reader.step_lock(i, channel, current_step)
    return program.get_step_param_trig_lock(channel, current_step, i)
  end

  function reader.assigned(param_id)
    return (param_value(param_id))
  end

  local function default_of(param)
    return param and param.default
  end

  function reader.fallback(kind, channel)
    local param_id = fn.get_param_id_from_stock_id(kind, channel.number)
    if not param_id then return nil, nil end
    local value, param = param_value(param_id)
    return value, default_of, param
  end

  return reader
end

-- Exact arithmetic that cannot be represented raises; callers turn that into
-- an unavailable record (never a rounded or dropped value).
local UNSUPPORTED = {}

local function must(value)
  if value == nil then error(UNSUPPORTED, 0) end
  return value
end

-- The exact delay of one strum ordinal: the descriptor's own float function
-- decides whether the voice is scheduled (so the same voices as playback are
-- kept); the value is the same formula in exact fractions, cross-checked
-- against the float.
local function exact_delay(fail, division, spread, acceleration, ordinal)
  if not division or division == 0 or ordinal == 0 then return ZERO end
  if not finite(division) or not finite(spread) or not finite(acceleration) then return fail() end
  local float = chord_timing.delay(division, spread, acceleration, ordinal)
  if float == nil then return nil end
  if not finite(float) or float < 0 then return fail() end
  local d, s, a = rational_of(division), rational_of(spread), rational_of(acceleration)
  if not d or not s or not a then return fail() end
  -- ordinal · (d + s) + s · a · ordinal · (ordinal − 1) / 2
  local value = must(mul(must(add(d, s)), {ordinal, 1}))
  value = must(add(value, must(mul(must(mul(s, a)), {ordinal * (ordinal - 1), 2}))))
  if math.abs(value[1] / value[2] - float) > TOLERANCE * math.max(1, math.abs(float)) then return fail() end
  return value
end

local function later(a, b)
  if b == nil then return a end
  if a == nil then return b end
  if must(compare(b, a)) == 1 then return b end
  return a
end

-- The articulation snapshot of `channel` over playable steps first..last.
-- Returns {status = "ok", tails = {[step] = fraction}, s_max = fraction} with
-- tails[step] nil for a step that can schedule no voice, or
-- {status = UNAVAILABLE, step = first failing step}.
local function snapshot(channel, first, last)
  local failed = false
  local function fail() failed = true; return nil end
  local root_now, chord_voice, root_later = strum_descriptor.new(chord_order.index,
    function(division, spread, acceleration, ordinal)
      return exact_delay(fail, division, spread, acceleration, ordinal)
    end)
  local tails, s_max = {}, ZERO
  for current_step = first, last do
    local reader = new_reader()
    local stock = stock_parameter.resolver(channel.trig_lock_params, reader.step_lock, reader.assigned,
      reader.fallback, channel, current_step)
    local ok, mute_root, chord_one, chord_two, chord_three, chord_four, has_chord_notes,
      chord_strum_pattern, arp_division, chord_division, _, chord_spread, chord_acceleration =
      pcall(articulation.resolve, channel, current_step, stock)
    if not ok or reader.failed then return {status = gate.UNAVAILABLE, step = current_step} end
    local voices, tail = false, ZERO
    if arp_division then
      -- An arp is bounded by the gate length already: it adds nothing. With a
      -- muted root and no chord slot its sequence is empty (arp_descriptor).
      voices = has_chord_notes or not mute_root
    else
      if root_now(chord_strum_pattern, mute_root) then voices = true end
      if has_chord_notes then
        local chord_notes = {chord_one, chord_two, chord_three, chord_four}
        for i = 1, 4 do
          local number, delay = chord_voice(i, chord_notes, chord_strum_pattern, chord_division, chord_spread,
            chord_acceleration)
          if failed then return {status = gate.UNAVAILABLE, step = current_step} end
          if number then voices = true; tail = later(tail, delay) end
        end
      end
      local delay = root_later(chord_strum_pattern, mute_root, chord_division, chord_spread, chord_acceleration)
      if failed then return {status = gate.UNAVAILABLE, step = current_step} end
      if delay then voices = true; tail = later(tail, delay) end
    end
    if voices then
      tails[current_step] = tail
      s_max = later(s_max, tail)
    end
  end
  return {status = "ok", tails = tails, s_max = s_max}
end

function gate.snapshot(channel, first, last)
  local ok, record = pcall(snapshot, channel, first, last)
  if ok then return record end
  if record ~= UNSUPPORTED then error(record, 0) end
  return {status = gate.UNAVAILABLE, step = first}
end

-- The tail of a step as a number (nil when the step schedules no voice).
function gate.tail(record, current_step)
  local tail = record.tails and record.tails[current_step]
  return tail and tail[1] / tail[2] or nil
end

-- §1.4 L_max in leader steps, from stored values only. A and a are the largest
-- and smallest stored length in any of the slot's 16 patterns, M the largest
-- channel or step length mask. Every merge operand lies in [min(a, 1), A]
-- (effective_lengths only shortens a length above 1, to a distance >= 1).
-- fn.average_table_values rounds half up to an integer r, avg − 1/2 < r <=
-- avg + 1/2, so average <= A + 1/2, up = r + (max − min) <= 2A − min(a, 1) +
-- 1/2 and down = 2·min − r < min + 1/2. With integer stored lengths r <= A and
-- r >= min, which gives the plan's max(2A − min(a, 1), M); a fractional stored
-- length adds the 1/2. The trailing 1 is the working pattern's default length
-- where no length merge applies. nil when a value is unrecoverable.
local function exact(value)
  local result = rational_of(value)
  if not result then error(UNSUPPORTED, 0) end
  return result
end

-- The scan compares stored numbers directly (float ordering is exact) and
-- converts only the extremes, so it costs ~1,100 reads and no allocation.
local function length_bound(song, channel)
  local largest, smallest
  local integral = true
  for number = 1, 16 do
    local source = song.patterns[number]
    local lengths = source and source.lengths
    if lengths then
      for step = 1, 64 do
        local value = lengths[step]
        if value ~= nil then
          if not finite(value) then error(UNSUPPORTED, 0) end
          if integral and math.tointeger(value) == nil then integral = false end
          if largest == nil or value > largest then largest = value end
          if smallest == nil or value < smallest then smallest = value end
        end
      end
    end
  end
  local mask
  if channel.length_mask ~= nil then
    if not finite(channel.length_mask) then error(UNSUPPORTED, 0) end
    mask = channel.length_mask
  end
  for _, value in pairs(channel.step_length_masks or {}) do
    if not finite(value) then error(UNSUPPORTED, 0) end
    if mask == nil or value > mask then mask = value end
  end
  local bound = {1, 1}
  if largest then
    local floor = smallest < 1 and exact(smallest) or {1, 1}
    local up = must(common_time.sub(must(mul(exact(largest), {2, 1})), floor))
    if not integral then up = must(add(up, {1, 2})) end
    bound = later(bound, up)
  end
  if mask ~= nil then bound = later(bound, exact(mask)) end
  return bound
end

function gate.length_bound(song, channel)
  local ok, bound = pcall(length_bound, song, channel)
  if ok then return bound end
  if bound ~= UNSUPPORTED then error(bound, 0) end
  return nil
end

return gate
