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


function test_hardening_working_merge_refreshes_after_source_edit_assignment_and_song_copy()
  -- README.md:622-630 assigns any subset of the 16 patterns to a channel, and 638-647
  -- selects the note merge rule. Rebuilding the working pattern must observe subsequent
  -- source edits and assignment changes without leaking those changes through a song copy.
  local song = fresh_song()
  local channel = song.channels[1]
  channel.trig_merge_mode = "all"
  channel.note_merge_mode = "average"
  select_sources(channel, {1, 2})
  set_source_value(song.patterns[1], "note_values", 0)
  set_source_value(song.patterns[2], "note_values", 4)

  pattern_hardening.update_working_pattern(1, song)
  luaunit.assert_equals(channel.working_pattern.note_values[1], 2)

  song.patterns[2].note_values[1] = 8
  pattern_hardening.update_working_pattern(1, song)
  luaunit.assert_equals(channel.working_pattern.note_values[1], 4, "edited source")

  channel.selected_patterns[2] = nil
  pattern_hardening.update_working_pattern(1, song)
  luaunit.assert_equals(channel.working_pattern.note_values[1], 0, "unassigned source")
  channel.selected_patterns[2] = true
  pattern_hardening.update_working_pattern(1, song)
  luaunit.assert_equals(channel.working_pattern.note_values[1], 4, "reassigned source")

  program.set_song_pattern(1, 96)
  program.set_selected_song_pattern(96)
  local copied = program.get_song_pattern(96)
  copied.patterns[1].note_values[1] = -2
  pattern_hardening.update_working_pattern(1, copied)
  luaunit.assert_equals(copied.channels[1].working_pattern.note_values[1], 3, "copied song edit")

  program.set_selected_song_pattern(1)
  pattern_hardening.update_working_pattern(1, song)
  luaunit.assert_equals(channel.working_pattern.note_values[1], 4, "source song isolation")
  luaunit.assert_equals(song.patterns[1].note_values[1], 0)
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


function test_hardening_song_boundary_does_not_cancel_committed_pattern_rebuild()
  -- Characterisation, not manual text: the final input release commits the edit.
  -- README.md:447-465 requires that edit to change the pattern, while 1070-1074
  -- advances the song. A rebuild for the new slot must not cancel the committed
  -- rebuild for the old slot. Each slot still debounces repeated requests.
  local original_scheduler = scheduler
  local stepped_scheduler = {jobs = {}, next_id = 1}

  function stepped_scheduler.start(co)
    local id = stepped_scheduler.next_id
    stepped_scheduler.next_id = id + 1
    stepped_scheduler.jobs[id] = {co = co, active = true}
    return id
  end

  function stepped_scheduler.debounce(func)
    local current_id = nil
    return function(...)
      if current_id and stepped_scheduler.jobs[current_id] then
        stepped_scheduler.jobs[current_id].active = false
      end
      local args = {...}
      current_id = stepped_scheduler.start(coroutine.create(function()
        func(table.unpack(args))
      end))
    end
  end

  function stepped_scheduler.tick()
    local ids = {}
    for id, job in pairs(stepped_scheduler.jobs) do
      if job.active then ids[#ids + 1] = id end
    end
    table.sort(ids)
    for _, id in ipairs(ids) do
      local job = stepped_scheduler.jobs[id]
      if job.active then
        local ok, err = coroutine.resume(job.co)
        assert(ok, err)
        if coroutine.status(job.co) == "dead" then job.active = false end
      end
    end
  end

  function stepped_scheduler.active_count()
    local count = 0
    for _, job in pairs(stepped_scheduler.jobs) do
      if job.active then count = count + 1 end
    end
    return count
  end

  function stepped_scheduler.run_until_idle()
    local ticks = 0
    while stepped_scheduler.active_count() > 0 do
      stepped_scheduler.tick()
      ticks = ticks + 1
      assert(ticks <= 40, "pattern rebuild failed to quiesce")
    end
  end

  local observed = {}
  scheduler = stepped_scheduler
  local ok, err = pcall(function()
    local pattern_under_test = include("mosaic/lib/pattern")
    program.init()
    local first = program.get_song_pattern(1)
    local second = program.get_song_pattern(2)

    local function configure(song, note)
      song.patterns[1].trig_values[1] = 1
      song.patterns[1].note_values[1] = note
      for channel = 1, 16 do
        song.channels[channel].selected_patterns = {[1] = true}
        song.channels[channel].trig_merge_mode = "all"
        song.channels[channel].note_merge_mode = "average"
      end
    end

    configure(first, 0)
    configure(second, 12)
    program.set_selected_song_pattern(1)
    pattern_under_test.update_working_patterns()
    stepped_scheduler.run_until_idle()
    program.set_selected_song_pattern(2)
    pattern_under_test.update_working_patterns()
    stepped_scheduler.run_until_idle()

    -- Channel 1 finishes before the boundary; channel 16 is still queued.
    first.patterns[1].note_values[1] = 7
    program.set_selected_song_pattern(1)
    pattern_under_test.update_working_patterns()
    stepped_scheduler.tick()
    program.set_selected_song_pattern(2)
    pattern_under_test.update_working_patterns()
    observed.cross_song_jobs = stepped_scheduler.active_count()
    stepped_scheduler.run_until_idle()
    observed.first_early = first.channels[1].working_pattern.note_values[1]
    observed.first_late = first.channels[16].working_pattern.note_values[1]
    observed.second_early = second.channels[1].working_pattern.note_values[1]
    observed.second_late = second.channels[16].working_pattern.note_values[1]

    -- A newer edit in the same slot replaces its partial sweep, while a rebuild
    -- for another slot remains independent. All channels must receive the latest.
    first.patterns[1].note_values[1] = 8
    program.set_selected_song_pattern(1)
    pattern_under_test.update_working_patterns()
    for _ = 1, 8 do stepped_scheduler.tick() end
    first.patterns[1].note_values[1] = 9
    pattern_under_test.update_working_patterns()
    program.set_selected_song_pattern(2)
    pattern_under_test.update_working_patterns()
    observed.debounced_jobs = stepped_scheduler.active_count()
    stepped_scheduler.run_until_idle()
    observed.latest = {}
    for channel = 1, 16 do
      observed.latest[channel] = first.channels[channel].working_pattern.note_values[1]
    end
    observed.second_after = second.channels[16].working_pattern.note_values[1]
  end)
  scheduler = original_scheduler

  luaunit.assert_true(ok, err)
  luaunit.assert_equals(observed.cross_song_jobs, 2, "different song slots must retain both sweeps")
  luaunit.assert_equals(observed.first_early, 7)
  luaunit.assert_equals(observed.first_late, 7, "boundary cancelled late-channel edit")
  luaunit.assert_equals(observed.second_early, 12)
  luaunit.assert_equals(observed.second_late, 12, "new song rebuilt from another slot")
  luaunit.assert_equals(observed.debounced_jobs, 2, "same-slot requests were not debounced")
  for channel = 1, 16 do
    luaunit.assert_equals(observed.latest[channel], 9, "latest edit missing on channel " .. channel)
  end
  luaunit.assert_equals(observed.second_after, 12, "queued edit leaked between song slots")
end
