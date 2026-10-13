-- Shared player-facing strategy and unapplied request cursor. Musical state
-- remains owned by the existing validated optional-config transaction.
local state = include("mosaic/lib/musical_merge/state")
local strategy = {}
strategy.choices = {"skip", "only", "all", "foundation", "fragments"}
local cursors = rawget(_G, "__mosaic_merge_strategy_cursors")
if not cursors then
  cursors = setmetatable({}, {__mode = "k"})
  rawset(_G, "__mosaic_merge_strategy_cursors", cursors)
end
local function choice(config, channel)
  local mode = config and config.mode
  if mode == "foundation" or mode == "fragments" then return mode end
  return channel.trig_merge_mode or "skip"
end
local function accepted(song, channel)
  local record = state.peek(song, channel.number)
  local pending = record and (record.global_queued or record.queued)
  local active = record and record.active or channel.musical_merge
  return choice(pending or channel.musical_merge, channel), choice(active, channel),
    pending and choice(pending, channel), record and record.global_queued and "NEXT PATTERN" or "NEXT CYCLE"
end
function strategy.snapshot(song, channel)
  local requested, active, pending, boundary = accepted(song, channel)
  local cursor = cursors[channel]
  if cursor and cursor.basis ~= requested then cursors[channel] = nil; cursor = nil end
  return {selected = cursor and cursor.selected or requested, active = active,
    pending = pending, boundary = pending and boundary, error = cursor and cursor.error}
end
function strategy.owned(song, channel, kind)
  local active = strategy.snapshot(song, channel).active
  return active == "fragments" or (active == "foundation" and kind == "trig")
end
function strategy.step(song, channel, delta, wrap)
  local selected = strategy.snapshot(song, channel).selected
  local index = 1
  for i, item in ipairs(strategy.choices) do if item == selected then index = i end end
  index = index + (delta > 0 and 1 or -1)
  if wrap then index = (index - 1) % #strategy.choices + 1
  else index = math.max(1, math.min(#strategy.choices, index)) end
  return strategy.choices[index]
end
function strategy.request(song, channel, selected, commit)
  local valid = false
  for _, item in ipairs(strategy.choices) do if selected == item then valid = true end end
  if not valid then return false, "INVALID STRATEGY" end
  local ok, status = commit(selected)
  local requested = accepted(song, channel)
  local message = status
  if not ok and (status == "INVALID merge anchor" or status == "INVALID anchor not assigned") then message = "NEEDS ANCHOR" end
  cursors[channel] = {selected = selected, basis = requested, error = not ok and message or nil}
  return ok, message
end
return strategy
