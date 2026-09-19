-- README.md Musical Merge phrase development: counters advance only on channel
-- wraps; phrase-setting activation starts a fresh epoch before the boundary onset.

local state = include("mosaic/lib/musical_merge/state")
local config = include("mosaic/lib/musical_merge/config")

local function value(cycles, variation)
  local result = config.new()
  result.mode = "foundation"
  result.anchor = 1
  result.cycles = cycles or 4
  result.shape = "build"
  result.percentages = config.curve("build", result.cycles)
  result.variation = variation or "fixed"
  return result
end

function test_musical_merge_state_wraps_cycles_and_phrase_without_redraw_or_probability_inputs()
  state.reset()
  local song = {}
  local requested = value(4, "per_phrase")
  local first = state.effective(song, 2, requested)
  luaunit.assert_equals({first.cycle, first.phrase, first.ranking_phrase}, {1, 0, 0})
  for cycle = 2, 4 do
    state.on_cycle_boundary(song, 2, requested)
    local current = state.effective(song, 2, requested)
    luaunit.assert_equals({current.cycle, current.phrase}, {cycle, 0})
  end
  state.on_cycle_boundary(song, 2, requested)
  local next_phrase = state.effective(song, 2, requested)
  luaunit.assert_equals({next_phrase.cycle, next_phrase.phrase, next_phrase.ranking_phrase}, {1, 1, 1})
  luaunit.assert_equals(state.effective(song, 2, requested), next_phrase)
end

function test_musical_merge_state_fixed_variation_never_changes_ranking_phrase()
  state.reset()
  local song, requested = {}, value(2, "fixed")
  for _ = 1, 9 do state.on_cycle_boundary(song, 1, requested) end
  local current = state.effective(song, 1, requested)
  luaunit.assert_true(current.phrase > 0)
  luaunit.assert_equals(current.ranking_phrase, 0)
end

function test_musical_merge_state_queued_phrase_change_restarts_before_boundary_without_double_increment()
  state.reset()
  local song, old = {}, value(8, "fixed")
  for _ = 1, 6 do state.on_cycle_boundary(song, 3, old) end
  luaunit.assert_equals(state.effective(song, 3, old).cycle, 7)
  local replacement = value(2, "per_phrase")
  luaunit.assert_equals(state.request(song, 3, replacement, true), "queued")
  luaunit.assert_equals(state.effective(song, 3, old).cycle, 7)
  local activated = state.on_cycle_boundary(song, 3, old)
  luaunit.assert_true(activated)
  local current = state.effective(song, 3, old)
  luaunit.assert_equals({current.cycle, current.phrase, current.config.cycles}, {1, 0, 2})
  state.on_cycle_boundary(song, 3, old)
  luaunit.assert_equals(state.effective(song, 3, old).cycle, 2)
end

function test_musical_merge_state_non_phrase_edits_retain_position_and_latest_queue_wins()
  state.reset()
  local song, requested = {}, value(4, "fixed")
  state.on_cycle_boundary(song, 4, requested)
  state.on_cycle_boundary(song, 4, requested)
  luaunit.assert_equals(state.effective(song, 4, requested).cycle, 3)
  local amount = value(4, "fixed");amount.amount = 25
  local latest = value(4, "fixed");latest.amount = 75
  state.request(song, 4, amount, true)
  state.request(song, 4, latest, true)
  state.on_cycle_boundary(song, 4, requested)
  local current = state.effective(song, 4, requested)
  luaunit.assert_equals(current.cycle, 4)
  luaunit.assert_equals(current.config.amount, 75)
end

function test_musical_merge_state_stop_promotes_requested_and_resets_each_channel_epoch()
  state.reset()
  local song, requested = {}, value(4, "per_phrase")
  state.on_cycle_boundary(song, 1, requested)
  state.on_cycle_boundary(song, 2, requested)
  local changed = value(2, "fixed")
  state.request(song, 1, changed, true)
  state.stop(song)
  luaunit.assert_equals(state.effective(song, 1, requested).cycle, 1)
  luaunit.assert_equals(state.effective(song, 1, requested).config.cycles, 2)
  luaunit.assert_equals(state.effective(song, 2, requested).cycle, 1)
end

function test_musical_merge_state_is_shared_across_norns_include_callers()
  local writer=include("mosaic/lib/musical_merge/state")
  local reader=include("mosaic/lib/musical_merge/state")
  writer.reset();local song,requested={},value(4,"fixed")
  reader.effective(song,6,requested)
  local changed=value(2,"per_phrase")
  writer.request(song,6,changed,true)
  luaunit.assert_equals(reader.effective(song,6,requested).config.cycles,4)
  reader.on_cycle_boundary(song,6,requested)
  luaunit.assert_equals(writer.effective(song,6,requested).config.cycles,2)
end

function test_musical_merge_global_transaction_waits_for_pattern_not_channel_boundary()
  state.reset();local song,old={},value(4,"fixed")
  state.effective(song,2,old);local replacement=value(2,"per_phrase")
  state.request_global(song,2,replacement,true)
  state.on_cycle_boundary(song,2,old)
  luaunit.assert_equals(state.effective(song,2,old).config.cycles,4)
  state.on_pattern_boundary(song)
  local active=state.effective(song,2,old)
  luaunit.assert_equals({active.config.cycles,active.cycle,active.phrase},{2,1,0})
end
