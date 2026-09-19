-- README.md Voice leading lifecycle: preparing is not consuming; a frame commits
-- once on accepted scheduling, and unconsumed revisions coalesce from history.

local loaded, harmony_state = pcall(include, "mosaic/lib/harmony/state")
local config = include("mosaic/lib/harmony/config")

local function material(values)
  local result = {}
  for index, item in ipairs(values) do
    result[index] = {id = item[1], pc = item[2], required = item[3] == true}
  end
  return result
end

function test_harmony_state_module_exists()
  luaunit.assert_true(loaded)
end

function test_harmony_state_revoice_failure_does_not_replace_consumed_history()
  harmony_state.reset()
  local song, channel = {}, config.new_channel("revoice")
  channel.roles.v1 = {min=48,max=60,centre=54,preferred_leap=12,strict_leap=false,enabled=true}
  local first = harmony_state.prepare_revoice(song, 1, "a", material({{"root", 0}}), channel)
  luaunit.assert_equals(first.status, "ok")
  harmony_state.consume_revoice(song, 1, first)
  local consumed = harmony_state.snapshot(song).channels[1].consumed
  channel.roles.v1.min, channel.roles.v1.max = 49, 59
  local failed = harmony_state.prepare_revoice(song, 1, "b", material({{"root", 0}}), channel)
  luaunit.assert_equals(failed.status, "no_solution")
  luaunit.assert_equals(harmony_state.snapshot(song).channels[1].consumed, consumed)
end

function test_harmony_state_group_frame_is_callback_order_independent_and_consumes_once()
  harmony_state.reset()
  local song = {}
  local group = config.four_part_smooth(1, {2, 3, 4, 5})
  group.enabled = true
  local c = material({{"tone1", 0, true}, {"tone2", 4, true}, {"tone3", 7, true}})
  local first = harmony_state.prepare_group(song, 1, "rev-c", c, group)
  local reversed_callback = harmony_state.prepare_group(song, 1, "rev-c", c, group)
  luaunit.assert_is(first, reversed_callback)
  luaunit.assert_nil(harmony_state.snapshot(song).groups[1].consumed_revision)
  harmony_state.consume_group(song, 1, first)
  harmony_state.consume_group(song, 1, first)
  local snapshot = harmony_state.snapshot(song).groups[1]
  luaunit.assert_equals(snapshot.consumed_revision, "rev-c")
  luaunit.assert_equals(snapshot.consumed_count, 1)
end

function test_harmony_state_two_unconsumed_revisions_solve_latest_from_last_consumed()
  harmony_state.reset()
  local song = {}
  local group = config.four_part_smooth(1, {2, 3, 4, 5})
  group.enabled = true
  local c = harmony_state.prepare_group(song, 1, "a",
    material({{"tone1", 0, true}, {"tone2", 4, true}, {"tone3", 7, true}}), group)
  harmony_state.consume_group(song, 1, c)
  harmony_state.prepare_group(song, 1, "b",
    material({{"tone1", 9, true}, {"tone2", 0, true}, {"tone3", 4, true}}), group)
  local latest = harmony_state.prepare_group(song, 1, "c",
    material({{"tone1", 5, true}, {"tone2", 9, true}, {"tone3", 0, true}}), group)

  local independent_song = {}
  local seeded = harmony_state.prepare_group(independent_song, 1, "a",
    material({{"tone1", 0, true}, {"tone2", 4, true}, {"tone3", 7, true}}), group)
  harmony_state.consume_group(independent_song, 1, seeded)
  local direct = harmony_state.prepare_group(independent_song, 1, "c",
    material({{"tone1", 5, true}, {"tone2", 9, true}, {"tone3", 0, true}}), group)
  luaunit.assert_equals(latest.pitches, direct.pitches)
end

function test_harmony_state_groups_and_channels_are_independent_and_resettable()
  harmony_state.reset()
  local song, group = {}, config.new_group(2)
  group.enabled = true
  local frame = harmony_state.prepare_group(song, 7, "x", material({{"tone1", 0, true}}), group)
  harmony_state.consume_group(song, 7, frame)
  harmony_state.prepare_revoice(song, 12, "y", material({{"root", 4}}), config.new_channel("revoice"))
  luaunit.assert_not_nil(harmony_state.snapshot(song).groups[7])
  luaunit.assert_not_nil(harmony_state.snapshot(song).channels[12])
  harmony_state.reset_song(song)
  luaunit.assert_equals(harmony_state.snapshot(song), {groups = {}, channels = {}})
end

