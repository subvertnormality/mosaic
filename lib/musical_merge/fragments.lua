-- Phrase fragments (MM-08): a separate merge mode, never the Foundation planner.
-- Pure: values and reasons only, no clock callbacks, no draw from Mosaic's RNG.
-- Contract: docs/musical-merge-extensions-plan.md §2.
local foundation = include("mosaic/lib/musical_merge/foundation")

local fragments = {}

-- §2.1: the playable positions start..end. Project validation forbids first >
-- last, so the range never wraps.
function fragments.positions(start_step, end_step)
  local result = {}
  for step = start_step, end_step do result[#result + 1] = step end
  return result
end

-- §2.1: index ranges (1-based into P) partitioning P from p_1 in size S; the
-- last fragment is shorter when N is not a multiple of S.
function fragments.layout(count, size)
  local result = {}
  local first = 1
  while first <= count do
    result[#result + 1] = {first = first, last = math.min(first + size - 1, count)}
    first = first + size
  end
  return result
end

-- §2.2: "frag|1|seed|slot|channel|binding|phrase|c|k".
function fragments.rank_identity(args, cycle, k)
  return table.concat({
    "frag", 1, args.seed or 0, args.song_slot or 1, args.channel or 1,
    args.binding or "", args.phrase or 0, cycle or 1, k
  }, "|")
end

function fragments.choose(args, cycle, k)
  local candidates = args.candidates or {}
  if #candidates == 0 then return nil end
  return candidates[foundation.fnv1a(fragments.rank_identity(args, cycle, k)) % #candidates + 1]
end

-- §2.3 Differing lengths: on the playable ring P, cap each onset's positive
-- length at the index distance to the next onset (itself after N steps when it
-- is the sole onset). Nonpositive lengths and steps outside P are unchanged.
-- Deliberately not the legacy effective_lengths helper.
function fragments.resolve_lengths(positions, trigs, lengths)
  local result = {}
  for step, value in pairs(lengths) do result[step] = value end
  local count = #positions
  local onsets = {}
  for index, step in ipairs(positions) do
    if trigs[step] == 1 then onsets[#onsets + 1] = index end
  end
  for order, index in ipairs(onsets) do
    local following = onsets[order % #onsets + 1]
    local delta = (following - index) % count
    if delta == 0 then delta = count end
    local step = positions[index]
    local length = result[step]
    if type(length) == "number" and length > 0 and length > delta then result[step] = delta end
  end
  return result
end

local function is_trig(values, step)
  return values ~= nil and values[step] == 1
end

function fragments.plan(args)
  local candidates = args.candidates or {}
  if #candidates == 0 then
    return {status = "assign_pattern", reason = "ASSIGN PATTERN"}
  end
  local patterns = args.patterns
  local positions = fragments.positions(args.start_step, args.end_step)
  local result = {
    status = "ok",
    positions = positions,
    fragments = {},
    trigs = {}, notes = {}, velocities = {}, lengths = {},
    roles = {}, reasons = {}, sources = {}, fragment_of = {},
    kept_anchor_count = 0,
    anchor_status = "off"
  }
  for step = 1, 64 do result.trigs[step] = 0 end

  local anchor_pattern
  if args.keep_anchor then
    for _, number in ipairs(candidates) do
      if number == args.anchor then anchor_pattern = patterns[number] end
    end
    result.anchor_status = anchor_pattern and "ok" or "anchor_missing"
  end

  for index, range in ipairs(fragments.layout(#positions, args.size)) do
    local k = index - 1
    local chosen = fragments.choose(args, args.cycle, k)
    local owner = patterns[chosen]
    result.fragments[index] = {
      index = k, source = chosen,
      first_step = positions[range.first], last_step = positions[range.last]
    }
    local reason = string.format("FRAGMENT %d · P%02d", k, chosen)
    for position = range.first, range.last do
      local step = positions[position]
      local taken, role, from = owner, "fragment", chosen
      if anchor_pattern and chosen ~= args.anchor and is_trig(anchor_pattern.trig_values, step) and
        not is_trig(owner.trig_values, step) then
        taken, role, from = anchor_pattern, "anchor", args.anchor
        result.reasons[step] = "KEPT ANCHOR"
        result.kept_anchor_count = result.kept_anchor_count + 1
      else
        result.reasons[step] = reason
      end
      result.trigs[step] = taken.trig_values[step]
      result.notes[step] = taken.note_values[step]
      result.velocities[step] = taken.velocity_values[step]
      result.lengths[step] = taken.lengths[step]
      result.fragment_of[step] = k
      if taken.trig_values[step] == 1 then
        result.roles[step] = role
        result.sources[step] = {from}
      end
    end
  end

  result.lengths = fragments.resolve_lengths(positions, result.trigs, result.lengths)
  return result
end

return fragments
