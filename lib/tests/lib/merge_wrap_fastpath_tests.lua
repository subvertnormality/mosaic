-- Differential tests for the working-pattern build fast paths
-- (docs/musical-merge-extensions-plan.md §1.3 and §1.4 performance): the
-- hoisted loop invariants of the final mask layer, and (below) the wrap
-- rebuild's content-validated memo. Every build is compared with the
-- pre-change pattern.get_and_merge_patterns, kept verbatim here as
-- `reference_merge`, over seeded random songs: sources with integer and
-- float values, `true` trigs, every merge mode including pattern priorities,
-- step and channel masks, loop ranges and Foundation with and without an
-- Interlock leader. Bounded and deterministic so the suite stays fast.

local pattern_under_test = include("mosaic/lib/pattern")
local merge_config = include("mosaic/lib/musical_merge/config")
local merge_state_module = include("mosaic/lib/musical_merge/state")

-- The pre-change build (lib/pattern.lua before the fast paths), verbatim.
local reference_merge = (function()
  local foundation = include("mosaic/lib/musical_merge/foundation")
  local merge_state = include("mosaic/lib/musical_merge/state")
  local merge_config = include("mosaic/lib/musical_merge/config")
  local fragments = include("mosaic/lib/musical_merge/fragments")
  local merge_structure = include("mosaic/lib/musical_merge/structure")
  local interlock = include("mosaic/lib/musical_merge/interlock")

  local program = program

  local notes = program.initialise_64_table({})
  local lengths = program.initialise_64_table({})
  local velocities = program.initialise_64_table({})

  -- Helper variables
  local update_timer_id = nil
  local throttle_time = 0.001
  local currently_processing = false

  local unpack = table.unpack
  local insert = table.insert
  local sort = table.sort
  local pairs = pairs

  -- Pre-allocate tables
  local default_trig_values = {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0}
  local default_lengths = {1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1}
  local default_note_values = {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0}
  local default_note_mask_values = {-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1}
  local default_velocity_values = {100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100}

  local function effective_lengths(source)
    local result = {unpack(source.lengths)}
    local next_trig
    for s = 1, 64 do
      if source.trig_values[s] == 1 then
        next_trig = s + 64
        break
      end
    end
    if not next_trig then return result end

    -- Walking backwards gives every trig its nearest following trig, including
    -- wraparound, without scanning each sustained note separately.
    for s = 64, 1, -1 do
      if source.trig_values[s] == 1 then
        local length = result[s]
        if length > 1 then
          local distance = next_trig - s
          -- The original search excludes a full-cycle self-interruption and
          -- cuts only strictly inside the requested (possibly fractional) gate.
          if distance <= 63 and distance < length then result[s] = distance end
        end
        next_trig = s
      end
    end
    return result
  end

  local function sync_pattern_values(merged_pattern, pattern, s, source_lengths)
    merged_pattern.lengths[s] = source_lengths[s]
    merged_pattern.velocity_values[s] = pattern.velocity_values[s]
    merged_pattern.note_values[s] = pattern.note_values[s]
    merged_pattern.note_mask_values[s] = pattern.note_mask_values[s]
    return merged_pattern
  end

  local function extract_pattern_number(merge_mode)
    local prefix = "pattern_number_"
    if merge_mode:sub(1, #prefix) == prefix then
      return tonumber(merge_mode:sub(#prefix + 1))
    end
    return nil
  end

  local function get_and_merge_patterns(channel, trig_merge_mode, note_merge_mode, velocity_merge_mode, length_merge_mode, song_pattern, effective_lengths_cache)
    local selected_song_pattern = song_pattern or program.get_selected_song_pattern()
    local merged_pattern = {
      trig_values = {unpack(default_trig_values)},
      lengths = {unpack(default_lengths)},
      note_values = {unpack(default_note_values)},
      note_mask_values = {unpack(default_note_mask_values)},
      velocity_values = {unpack(default_velocity_values)},
      merged_notes = {}
    }
    local skip_bits = {unpack(default_trig_values)}
    local only_bits = {unpack(default_trig_values)}

    local pattern_channel = selected_song_pattern.channels[channel]
    local patterns = selected_song_pattern.patterns
    local note_priority = note_merge_mode and extract_pattern_number(note_merge_mode)
    local velocity_priority = velocity_merge_mode and extract_pattern_number(velocity_merge_mode)
    local length_priority = length_merge_mode and extract_pattern_number(length_merge_mode)
    local priority_lengths
    local merge_step_trig_masks = program.get_step_trig_masks(channel)

    for i = 1, 64 do
      notes[i] = {}
      lengths[i] = {}
      velocities[i] = {}
    end

    local function do_moded_merge(pattern_number, is_pattern_trig_one, s, mode, priority, values, merged_values, pushed_values)
      if priority == pattern_number then
        merged_values[s] = values[s]
      elseif mode == "up" or mode == "down" or mode == "average" then
        if is_pattern_trig_one then
          insert(pushed_values[s], values[s])
        end
      end
    end

    -- Priority sources participate in merging without becoming channel assignments.
    local patterns_to_process = {}
    for number, enabled in pairs(pattern_channel.selected_patterns) do
      patterns_to_process[number] = enabled
    end

    local function process_merge_mode(merge_mode)
      if merge_mode then
        local pattern_number = extract_pattern_number(merge_mode)
        if pattern_number and patterns_to_process[pattern_number] == nil then
          patterns_to_process[pattern_number] = false
        end
      end
    end

    process_merge_mode(note_merge_mode)
    process_merge_mode(velocity_merge_mode)
    process_merge_mode(length_merge_mode)

    for pattern_number, pattern_enabled in pairs(patterns_to_process) do
      local pattern = patterns[pattern_number]
      local source_lengths = effective_lengths_cache and effective_lengths_cache[pattern_number]
      if not source_lengths then
        source_lengths = effective_lengths(pattern)
        if effective_lengths_cache then effective_lengths_cache[pattern_number] = source_lengths end
      end
      if pattern_number == length_priority then priority_lengths = source_lengths end

      for s = 1, 64 do
        local is_pattern_trig_one = pattern.trig_values[s] == 1
        if pattern_enabled then
          if trig_merge_mode == "skip" then
            if is_pattern_trig_one and merged_pattern.trig_values[s] < 1 and skip_bits[s] < 1 then
              merged_pattern = sync_pattern_values(merged_pattern, pattern, s, source_lengths)
              merged_pattern.trig_values[s] = 1
            elseif is_pattern_trig_one and merged_pattern.trig_values[s] == 1 then
              merged_pattern.trig_values[s] = 0
              skip_bits[s] = 1
            end
          elseif trig_merge_mode == "only" then
            if is_pattern_trig_one and merged_pattern.trig_values[s] < 1 and only_bits[s] == 0 then
              only_bits[s] = 1
              merged_pattern.trig_values[s] = 0
            elseif is_pattern_trig_one and only_bits[s] == 1 then
              merged_pattern.trig_values[s] = 1
            end
          elseif trig_merge_mode == "all" and is_pattern_trig_one then
            merged_pattern.trig_values[s] = 1
          end
        end

        local is_positive_step_trig_mask = merge_step_trig_masks and merge_step_trig_masks[s] == 1
        local should_process_note_merge_mode = is_pattern_trig_one or is_positive_step_trig_mask or note_priority
        local should_process_velocity_merge_mode = is_pattern_trig_one or is_positive_step_trig_mask or velocity_priority
        local should_process_length_merge_mode = is_pattern_trig_one or is_positive_step_trig_mask or length_priority

        if should_process_note_merge_mode then
          do_moded_merge(pattern_number, pattern_enabled, s, note_merge_mode, note_priority, pattern.note_values, merged_pattern.note_values, notes)
        end
        if should_process_velocity_merge_mode then
          do_moded_merge(pattern_number, pattern_enabled, s, velocity_merge_mode, velocity_priority, pattern.velocity_values, merged_pattern.velocity_values, velocities)
        end
        if should_process_length_merge_mode then
          do_moded_merge(pattern_number, pattern_enabled, s, length_merge_mode, length_priority, source_lengths, merged_pattern.lengths, lengths)
        end
      end
    end

    local function do_mode_calculation(mode, s, values, merged_values)
      if mode == "up" or mode == "down" or mode == "average" then
        if not values[s] or #values[s] == 0 then
          merged_values[s] = 0
        elseif #values[s] == 1 then
          merged_values[s] = values[s][1]
        else
          sort(values[s])
          local min_value = values[s][1]
          local max_value = values[s][#values[s]]
          local average = fn.average_table_values(values[s])
          if mode == "up" then
            merged_values[s] = average + (max_value - min_value)
          elseif mode == "down" then
            merged_values[s] = min_value - (average - min_value)
          else
            merged_values[s] = average
          end
          merged_pattern.merged_notes[s] = true
        end
      end
    end

    -- Trig collection may copy another pattern's values. Apply explicit priorities
    -- after that collection so table iteration order cannot overwrite the choice.

    local step_trig_masks = pattern_channel.step_trig_masks or {}
    local step_note_masks = pattern_channel.step_note_masks or {}
    local step_velocity_masks = pattern_channel.step_velocity_masks or {}
    local step_length_masks = pattern_channel.step_length_masks or {}
    local channel_data = pattern_channel

    for s = 1, 64 do
      do_mode_calculation(note_merge_mode, s, notes, merged_pattern.note_values)
      do_mode_calculation(velocity_merge_mode, s, velocities, merged_pattern.velocity_values)
      do_mode_calculation(length_merge_mode, s, lengths, merged_pattern.lengths)

      if note_priority then merged_pattern.note_values[s] = patterns[note_priority].note_values[s] end
      if velocity_priority then merged_pattern.velocity_values[s] = patterns[velocity_priority].velocity_values[s] end
      if length_priority then merged_pattern.lengths[s] = priority_lengths[s] end
    end

    local requested_merge_settings = pattern_channel.musical_merge or merge_config.new()
    local merge_runtime = merge_state.effective(selected_song_pattern, channel, requested_merge_settings)
    local merge_settings = merge_runtime and merge_runtime.config
    local merge_version = merge_settings and merge_settings.schema_version
    local foundation_result, fragments_result
    -- Canonical v2 keeps every v1 Foundation behaviour; Fragments exists only in v2.
    local foundation_mode = (merge_version == 1 or merge_version == 2) and merge_settings.mode == "foundation"
    local fragments_mode = merge_version == 2 and merge_settings.mode == "fragments"
    if foundation_mode or fragments_mode then
      local source_trigs, source_velocities, binding_parts = {}, {}, {}
      for pattern_number, enabled in pairs(pattern_channel.selected_patterns) do
        if enabled then
          source_trigs[pattern_number] = patterns[pattern_number].trig_values
          source_velocities[pattern_number] = patterns[pattern_number].velocity_values
          binding_parts[#binding_parts + 1] = pattern_number
        end
      end
      table.sort(binding_parts)
      local cycle = merge_runtime.cycle or 1
      local effective_start=fn.calc_grid_count(pattern_channel.start_trig[1],pattern_channel.start_trig[2])
      local effective_end=fn.calc_grid_count(pattern_channel.end_trig[1],pattern_channel.end_trig[2])
      effective_end=math.min(effective_end,effective_start+(selected_song_pattern.global_pattern_length or 64)-1)
      local song_slot = selected_song_pattern.number or program.get().selected_song_pattern or 1
      local binding = table.concat(binding_parts, ",") .. "|" .. tostring(note_merge_mode) .. "|" ..
        tostring(velocity_merge_mode) .. "|" .. tostring(length_merge_mode)
      if foundation_mode then
        local cycle_percentage = merge_settings.percentages and merge_settings.percentages[cycle] or 100
        local effective_amount = foundation.round_half_up((merge_settings.amount or 100) * cycle_percentage / 100)
        -- Plan §3: the Interlock admission for this build's cycle. It reads the
        -- leader's stored anchors directly and builds no leader plan (§1.2.3).
        -- Its record is published as foundation.interlock (fields documented
        -- in musical_merge/interlock.lua). Every bypass status (RESYNC, PLAN
        -- LIMIT, LEADER OFF, LEADER MISSING) adds no filter: gap, eligibility,
        -- ranking, Amount, Accent and masks then run exactly as with Interlock
        -- off (§1.2 unsupported-admission fallback).
        local filters, interlock_result
        if interlock.settings(merge_settings) then
          interlock_result = interlock.admission({
            song = selected_song_pattern, channel = channel, config = merge_settings,
            first = effective_start, last = effective_end
          })
          filters = {}
          if interlock_result.status == interlock.SUPPORTED then
            filters[1] = {reason = interlock_result.reason, blocked = interlock_result.blocked}
          end
        end
        foundation_result = foundation.plan({
          filters = filters,
          start_step = effective_start,
          end_step = effective_end,
          anchor = merge_settings.anchor,
          source_trigs = source_trigs,
          source_velocities = source_velocities,
          merged_velocities = merged_pattern.velocity_values,
          amount = effective_amount,
          accent = merge_settings.accent,
          gap = merge_settings.gap,
          seed = merge_settings.seed,
          song_slot = song_slot,
          channel = channel,
          binding = binding,
          phrase = merge_runtime.ranking_phrase or 0,
          ranking_version = merge_settings.ranking_version
        })
        foundation_result.interlock = interlock_result
        foundation_result.cycle = cycle
        foundation_result.cycles = merge_settings.cycles or 1
        foundation_result.phrase = merge_runtime.phrase or 0
        foundation_result.config = merge_settings
        foundation_result.anchor_notes = patterns[merge_settings.anchor] and
          patterns[merge_settings.anchor].note_values or nil
        -- Plan §4 Markers: explicit structural positions of this plan, read by
        -- step.handle and the Harmony Pattern loop through one shared policy.
        local structure_settings = merge_structure.active(merge_settings)
        if structure_settings and foundation_result.status == "ok" then
          foundation_result.markers = merge_structure.markers(structure_settings.markers,
            merge_structure.positions(effective_start, effective_end), foundation_result.roles)
        end
        merged_pattern.foundation = foundation_result
      else
        -- Plan §2: a separate mode, never the Foundation planner. Shape
        -- percentages, Amount, Accent and Gap do not apply.
        local fragment_settings = merge_settings.fragments or {}
        fragments_result = fragments.plan({
          start_step = effective_start,
          end_step = effective_end,
          size = fragment_settings.size or 8,
          candidates = binding_parts,
          patterns = patterns,
          seed = merge_settings.seed,
          song_slot = song_slot,
          channel = channel,
          binding = binding,
          phrase = merge_runtime.ranking_phrase or 0,
          cycle = cycle,
          keep_anchor = fragment_settings.keep_anchor == true,
          anchor = merge_settings.anchor
        })
        fragments_result.cycle = cycle
        fragments_result.cycles = merge_settings.cycles or 1
        fragments_result.phrase = merge_runtime.phrase or 0
        fragments_result.config = merge_settings
        merged_pattern.fragments = fragments_result
        if fragments_result.status == "ok" then
          -- Inside a fragment the legacy note/velocity/length merge modes and
          -- merged-pentatonic do not apply: every value is the source's own.
          merged_pattern.merged_notes = {}
          for s = 1, 64 do merged_pattern.trig_values[s] = fragments_result.trigs[s] end
          for _, s in ipairs(fragments_result.positions) do
            merged_pattern.note_values[s] = fragments_result.notes[s]
            merged_pattern.velocity_values[s] = fragments_result.velocities[s]
            merged_pattern.lengths[s] = fragments_result.lengths[s]
          end
        end
      end
    end

    for s = 1, 64 do
      if foundation_result and foundation_result.status == "ok" then
        merged_pattern.trig_values[s] = foundation_result.trigs[s]
        if foundation_result.velocities[s] ~= nil then
          merged_pattern.velocity_values[s] = foundation_result.velocities[s]
        end
      end

      if step_trig_masks[s] then
        merged_pattern.trig_values[s] = step_trig_masks[s]
      elseif channel_data.trig_mask and channel_data.trig_mask ~= -1 then
        merged_pattern.trig_values[s] = channel_data.trig_mask
      end

      if step_note_masks[s] then
        merged_pattern.note_mask_values[s] = step_note_masks[s]
      elseif channel_data.note_mask and channel_data.note_mask ~= -1 then
        merged_pattern.note_mask_values[s] = channel_data.note_mask
      end

      if step_velocity_masks[s] then
        merged_pattern.velocity_values[s] = step_velocity_masks[s]
      elseif channel_data.velocity_mask and channel_data.velocity_mask ~= -1 then
        merged_pattern.velocity_values[s] = channel_data.velocity_mask
      end

      if step_length_masks[s] then
        merged_pattern.lengths[s] = step_length_masks[s]
      elseif channel_data.length_mask and channel_data.lengths_mask ~= -1 then
        merged_pattern.lengths[s] = program.get_length_mask(channel_data)
      end
    end

    return merged_pattern
  end

  return get_and_merge_patterns
end)()

local function deep_equal(left, right)
  if type(left) ~= "table" or type(right) ~= "table" then
    return left == right and math.type(left) == math.type(right)
  end
  for key, value in pairs(left) do if not deep_equal(value, right[key]) then return false end end
  for key in pairs(right) do if left[key] == nil then return false end end
  return true
end

-- The first differing path, for failure messages.
local function difference(left, right, path)
  path = path or ""
  if type(left) ~= "table" or type(right) ~= "table" then
    if left == right and math.type(left) == math.type(right) then return nil end
    return string.format("%s: %s (%s) vs %s (%s)", path, tostring(left), tostring(math.type(left)),
      tostring(right), tostring(math.type(right)))
  end
  for key, value in pairs(left) do
    local found = difference(value, right[key], path .. "." .. tostring(key))
    if found then return found end
  end
  for key in pairs(right) do
    if left[key] == nil then return path .. "." .. tostring(key) .. ": missing on the left" end
  end
  return nil
end

local MODES = {"up", "down", "average"}
local TRIG_MODES = {"all", "skip", "only"}

local function random_value(random, low, high)
  local value = random(low, high)
  if random(12) == 1 then value = value + 0.0 end
  if random(40) == 1 then value = value + 0.5 end
  return value
end

local function random_trig(random, density)
  local draw = random()
  if draw < density then return random(30) == 1 and 1.0 or 1 end
  if draw < density + 0.02 then return true end
  return 0
end

local function randomise_source(random, source)
  local density = ({0, 0.15, 0.4, 0.8})[random(4)]
  for s = 1, 64 do
    source.trig_values[s] = random_trig(random, density)
    source.note_values[s] = random_value(random, -7, 14)
    source.velocity_values[s] = random_value(random, 1, 127)
    source.lengths[s] = random(6) == 1 and random_value(random, 2, 9) or 1
    source.note_mask_values[s] = random(5) == 1 and random_value(random, 0, 12) or -1
  end
end

local function random_mode(random)
  if random(5) == 1 then return "pattern_number_" .. random(1, 16) end
  return MODES[random(#MODES)]
end

local function random_merge(random, channel)
  local kind = random(5)
  if kind == 1 then return nil end
  local value = merge_config.new()
  if kind == 2 then return value end
  value.mode = "foundation"
  value.anchor = random(1, 16)
  value.amount = random(0, 100)
  value.accent = random(4) == 1 and 0 or random(1, 100)
  value.gap = random(0, 3)
  value.seed = random(0, 65535)
  value.cycles = ({1, 2, 4})[random(3)]
  value.percentages = merge_config.curve("build", value.cycles)
  value.variation = random(2) == 1 and "per_phrase" or "fixed"
  if kind >= 4 then
    local leader = random(1, 16)
    if leader ~= channel then value.interlock = {leader = leader, window = random(0, 3)} end
  end
  return value
end

local function randomise_channel(random, song, c)
  local channel = song.channels[c]
  channel.selected_patterns = {}
  for _ = 1, random(1, 4) do channel.selected_patterns[random(1, 16)] = random(8) > 1 end
  channel.trig_merge_mode = TRIG_MODES[random(#TRIG_MODES)]
  channel.note_merge_mode = random_mode(random)
  channel.velocity_merge_mode = random_mode(random)
  channel.length_merge_mode = random_mode(random)
  channel.step_trig_masks, channel.step_note_masks = {}, {}
  channel.step_velocity_masks, channel.step_length_masks = {}, {}
  for _ = 1, random(0, 4) do
    local s = random(1, 64)
    channel.step_trig_masks[s] = random(0, 1)
    if random(2) == 1 then channel.step_note_masks[s] = random(0, 12) end
    if random(2) == 1 then channel.step_velocity_masks[s] = random(1, 127) end
    if random(3) == 1 then channel.step_length_masks[s] = random(1, 4) end
  end
  channel.trig_mask = random(8) == 1 and random(0, 1) or -1
  channel.note_mask = random(8) == 1 and random(0, 12) or -1
  channel.velocity_mask = random(8) == 1 and random(1, 127) or -1
  channel.length_mask = random(8) == 1 and random(1, 4) or nil
  channel.start_trig = {random(1, 16), random(4, 5)}
  channel.end_trig = {random(1, 16), random(6, 7)}
  channel.musical_merge = random_merge(random, c)
  -- Foundation's anchor is usually one of the channel's own sources.
  local value = channel.musical_merge
  if value and value.mode == "foundation" and random(4) > 1 then
    local numbers = {}
    for number in pairs(channel.selected_patterns) do numbers[#numbers + 1] = number end
    table.sort(numbers)
    value.anchor = numbers[random(#numbers)]
  end
end

local function random_song(random)
  program.init()
  merge_state_module.reset()
  program.set_selected_song_pattern(1)
  local song = program.get_song_pattern(1)
  for number = 1, 16 do randomise_source(random, song.patterns[number]) end
  for c = 1, 16 do randomise_channel(random, song, c) end
  return song
end

-- A build of channel c with the channel's own merge modes.
local function build(merge, song, c, ...)
  local channel = song.channels[c]
  return merge(c, channel.trig_merge_mode, channel.note_merge_mode, channel.velocity_merge_mode,
    channel.length_merge_mode, song, ...)
end

function test_merge_wrap_fastpath_build_matches_the_pre_change_build()
  local random = math.random
  math.randomseed(20260927)
  local foundation_ok, interlocked = 0, 0
  for case = 1, 500 do
    local song = random_song(random)
    for _ = 1, 4 do
      local c = random(1, 16)
      local expected = build(reference_merge, song, c)
      local actual = build(pattern_under_test.get_and_merge_patterns, song, c)
      local found = difference(actual, expected)
      if found then luaunit.fail(string.format("case %d channel %d %s", case, c, found)) end
      local plan = expected.foundation
      if plan and plan.status == "ok" then foundation_ok = foundation_ok + 1 end
      if plan and plan.interlock and plan.interlock.status == "ok" and next(plan.interlock.blocked) then
        interlocked = interlocked + 1
      end
    end
  end
  merge_state_module.reset()
  luaunit.assert_true(foundation_ok > 200, foundation_ok)
  luaunit.assert_true(interlocked > 20, interlocked)
end
