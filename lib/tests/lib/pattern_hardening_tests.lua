-- Hardening matrix for pattern and scale-merge primitives.
-- README.md:630-673 defines trig cardinality and note/velocity/length arithmetic.
-- These tests use literal expected values and invariants rather than pattern.lua as an oracle.

local pattern_hardening = include("mosaic/lib/pattern")

local function fresh_song()
  program.init()
  return program.get_song_pattern(1)
end

local function select_sources(channel, order)
  channel.selected_patterns = {}
  for _, source in ipairs(order) do
    channel.selected_patterns[source] = true
  end
end

local function set_source_value(source, field, value)
  source.trig_values[1] = 1
  source[field][1] = value
end

local function copy_array(values)
  local copy = {}
  for i = 1, #values do copy[i] = values[i] end
  return copy
end

local function snapshot_source(source)
  return {
    trig_values = copy_array(source.trig_values),
    note_values = copy_array(source.note_values),
    velocity_values = copy_array(source.velocity_values),
    lengths = copy_array(source.lengths),
    note_mask_values = copy_array(source.note_mask_values)
  }
end

function test_hardening_trig_merge_truth_table_for_all_sixteen_source_cardinalities()
  -- README.md:634-636: All means >=1, Skip means exactly 1, Only means >1.
  for count = 0, 16 do
    for _, mode in ipairs({"all", "skip", "only"}) do
      local song = fresh_song()
      local channel = song.channels[1]
      local order = {}
      for source = 16, 1, -1 do
        order[#order + 1] = source
        if source <= count then song.patterns[source].trig_values[1] = 1 end
      end
      select_sources(channel, order)

      local result = pattern_hardening.get_and_merge_patterns(1, mode, false, false, false)
      local expected = 0
      if mode == "all" and count >= 1 then expected = 1 end
      if mode == "skip" and count == 1 then expected = 1 end
      if mode == "only" and count > 1 then expected = 1 end
      luaunit.assert_equals(result.trig_values[1], expected, mode .. " count " .. count)
    end
  end
end

function test_hardening_every_pattern_slot_can_be_an_unassigned_priority_source()
  -- README.md:647 permits note priority from a pattern not assigned to the channel;
  -- velocity and length priority use the same Pattern gesture at lines 660 and 671.
  local fields = {
    {name = "note_values", argument = 1, base = -20},
    {name = "velocity_values", argument = 2, base = 40},
    {name = "lengths", argument = 3, base = 0.25}
  }

  for priority = 1, 16 do
    for _, field in ipairs(fields) do
      local song = fresh_song()
      local channel = song.channels[1]
      select_sources(channel, {1})
      song.patterns[1].trig_values[1] = 1
      song.patterns[1].note_values[1] = 2
      song.patterns[1].velocity_values[1] = 64
      song.patterns[1].lengths[1] = 1

      local wanted = field.base + priority
      song.patterns[priority][field.name][1] = wanted
      song.patterns[priority].trig_values[1] = 1

      local modes = {false, false, false}
      modes[field.argument] = "pattern_number_" .. priority
      local result = pattern_hardening.get_and_merge_patterns(
        1, "all", modes[1], modes[2], modes[3]
      )

      luaunit.assert_equals(result[field.name][1], wanted, field.name .. " priority " .. priority)
      luaunit.assert_equals(result.trig_values[1], 1, "priority must not remove assigned trig")
      if priority ~= 1 then
        luaunit.assert_nil(channel.selected_patterns[priority], "priority source became assigned")
      end
    end
  end
end

function test_hardening_numeric_merge_literal_partitions()
  -- README.md:644-646,657-659,668-670. Half values round toward the greater integer.
  local cases = {
    {values = {-3, -2}, average = -2, up = -1, down = -4},
    {values = {0, 1}, average = 1, up = 2, down = -1},
    {values = {1, 2, 3, 4}, average = 3, up = 6, down = -1},
    {values = {0.25, 1.75}, average = 1, up = 2.5, down = -0.5}
  }
  local fields = {
    {name = "note_values", argument = 1, include_fractional = false},
    {name = "velocity_values", argument = 2, include_fractional = false},
    {name = "lengths", argument = 3, include_fractional = true}
  }

  for _, field in ipairs(fields) do
    for case_number, case in ipairs(cases) do
      if field.include_fractional or case_number < 4 then
        for _, mode in ipairs({"average", "up", "down"}) do
          local song = fresh_song()
          local channel = song.channels[1]
          local selected = {}
          for source, value in ipairs(case.values) do
            selected[#selected + 1] = source
            set_source_value(song.patterns[source], field.name, value)
          end
          select_sources(channel, selected)
          local modes = {false, false, false}
          modes[field.argument] = mode
          local result = pattern_hardening.get_and_merge_patterns(
            1, "all", modes[1], modes[2], modes[3]
          )
          luaunit.assert_equals(
            result[field.name][1], case[mode],
            field.name .. " " .. mode .. " partition " .. case_number
          )
          luaunit.assert_true(result.merged_notes[1], "multiple contributors must be marked merged")
        end
      end
    end
  end
end

function test_hardening_numeric_merge_empty_and_single_contributor_boundaries()
  local fields = {
    {name = "note_values", argument = 1, value = -7},
    {name = "velocity_values", argument = 2, value = 0},
    {name = "lengths", argument = 3, value = -0.5}
  }

  for _, field in ipairs(fields) do
    for _, mode in ipairs({"average", "up", "down"}) do
      local song = fresh_song()
      local modes = {false, false, false}
      modes[field.argument] = mode
      local empty = pattern_hardening.get_and_merge_patterns(
        1, "all", modes[1], modes[2], modes[3]
      )
      luaunit.assert_equals(empty[field.name][1], 0, field.name .. " empty " .. mode)
      luaunit.assert_nil(empty.merged_notes[1])

      song = fresh_song()
      local channel = song.channels[1]
      select_sources(channel, {16})
      set_source_value(song.patterns[16], field.name, field.value)
      local single = pattern_hardening.get_and_merge_patterns(
        1, "all", modes[1], modes[2], modes[3]
      )
      luaunit.assert_equals(single[field.name][1], field.value, field.name .. " single " .. mode)
      luaunit.assert_nil(single.merged_notes[1])
    end
  end
end

function test_hardening_merge_is_order_independent_and_does_not_mutate_sources()
  local orders = {
    {1, 2, 3, 16},
    {16, 3, 2, 1},
    {2, 16, 1, 3}
  }
  local expected = nil

  for _, order in ipairs(orders) do
    local song = fresh_song()
    local channel = song.channels[1]
    local values = {
      [1] = {-4, 10, 0.5},
      [2] = {1, 40, 1.5},
      [3] = {5, 70, 2.5},
      [16] = {8, 100, 4.5}
    }
    local before = {}
    for source, source_values in pairs(values) do
      local p = song.patterns[source]
      p.trig_values[1] = 1
      p.note_values[1] = source_values[1]
      p.velocity_values[1] = source_values[2]
      p.lengths[1] = source_values[3]
      before[source] = snapshot_source(p)
    end
    select_sources(channel, order)

    local result = pattern_hardening.get_and_merge_patterns(1, "only", "up", "down", "average")
    local signature = {
      result.trig_values[1],
      result.note_values[1],
      result.velocity_values[1],
      result.lengths[1]
    }
    if expected == nil then expected = signature else luaunit.assert_equals(signature, expected) end
    luaunit.assert_equals(signature, {1, 15, -35, 2})
    for source, snapshot in pairs(before) do
      luaunit.assert_equals(snapshot_source(song.patterns[source]), snapshot, "source mutation " .. source)
    end

    result.note_values[1] = 999
    result.trig_values[1] = 0
    local again = pattern_hardening.get_and_merge_patterns(1, "only", "up", "down", "average")
    luaunit.assert_equals(again.note_values[1], 15)
    luaunit.assert_equals(again.trig_values[1], 1)
  end
end

function test_hardening_merge_masks_and_selected_patterns_are_channel_isolated()
  local song = fresh_song()
  local channel_one = song.channels[1]
  local channel_sixteen = song.channels[16]
  select_sources(channel_one, {1})
  select_sources(channel_sixteen, {16})

  set_source_value(song.patterns[1], "note_values", 3)
  song.patterns[1].velocity_values[1] = 31
  song.patterns[1].lengths[1] = 1
  set_source_value(song.patterns[16], "note_values", 9)
  song.patterns[16].velocity_values[1] = 96
  song.patterns[16].lengths[1] = 4

  program.set_step_note_mask(channel_one, 1, 70)
  channel_one.step_velocity_masks[1] = 71
  program.set_step_length_mask(channel_one, 1, 7)
  program.set_step_trig_mask(16, 1, 0)

  local one = pattern_hardening.get_and_merge_patterns(1, "all", "average", "average", "average")
  local sixteen = pattern_hardening.get_and_merge_patterns(16, "all", "average", "average", "average")

  luaunit.assert_equals(one.trig_values[1], 1)
  luaunit.assert_equals(one.note_mask_values[1], 70)
  luaunit.assert_equals(one.velocity_values[1], 71)
  luaunit.assert_equals(one.lengths[1], 7)

  luaunit.assert_equals(sixteen.trig_values[1], 0)
  luaunit.assert_equals(sixteen.note_values[1], 9)
  luaunit.assert_equals(sixteen.note_mask_values[1], -1)
  luaunit.assert_equals(sixteen.velocity_values[1], 96)
  luaunit.assert_equals(sixteen.lengths[1], 4)

  luaunit.assert_equals(channel_one.selected_patterns, {[1] = true})
  luaunit.assert_equals(channel_sixteen.selected_patterns, {[16] = true})
end
