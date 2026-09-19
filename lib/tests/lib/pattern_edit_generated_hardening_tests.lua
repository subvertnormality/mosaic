-- Deterministic model-based hardening for the real pattern/channel sequencer control.
-- README.md:397 defines tap-to-toggle, hold-plus-end length editing and the visible
-- 64-step editor. README.md:722 defines ascending, distinct channel range endpoints.
-- Generated actions are characterisation beyond those manual statements. Seeds and
-- operation indices are retained in assertion messages so failures are reproducible.

local sequencer_control_generated = include("mosaic/lib/controls/sequencer")

local SEEDS = {19780503, 42424243, 8675309}
local SONGS = {1, 96}
local OPERATIONS_PER_SEED = 1600

local function coords(step)
  return ((step - 1) % 16) + 1, math.floor((step - 1) / 16) + 4
end

-- Park-Miller LCG: deterministic on Lua 5.3 without relying on global math.random.
local function generator(seed)
  local state = seed
  return function(limit)
    state = (state * 48271) % 2147483647
    return (state % limit) + 1
  end
end

local function new_pattern_model()
  local value = {trigs = {}, lengths = {}}
  for step = 1, 64 do
    value.trigs[step] = 0
    value.lengths[step] = 1
  end
  return value
end

local function new_song_model()
  local value = {active = false, patterns = {}, ranges = {}}
  for pattern_number = 1, 16 do value.patterns[pattern_number] = new_pattern_model() end
  for channel = 1, 16 do value.ranges[channel] = {start_step = 1, end_step = 64} end
  return value
end

local function assert_pattern_matches(actual, expected, context)
  for step = 1, 64 do
    luaunit.assert_equals(actual.trig_values[step], expected.trigs[step],
      context .. " trig step=" .. step)
    luaunit.assert_equals(actual.lengths[step], expected.lengths[step],
      context .. " length step=" .. step)
  end
end

local function assert_selected_state(model, song_number, pattern_number, channel_number, context)
  local song = program.get_song_pattern(song_number)
  luaunit.assert_equals(song.active, model[song_number].active, context .. " active")
  assert_pattern_matches(song.patterns[pattern_number],
    model[song_number].patterns[pattern_number], context)
  local range = model[song_number].ranges[channel_number]
  local channel = song.channels[channel_number]
  luaunit.assert_equals(fn.calc_grid_count(channel.start_trig[1], channel.start_trig[2]),
    range.start_step, context .. " range start")
  luaunit.assert_equals(fn.calc_grid_count(channel.end_trig[1], channel.end_trig[2]),
    range.end_step, context .. " range end")
end

local function setup()
  program.init()
  globals.reset()
  params.reset()
end

function test_hardening_generated_pattern_edits_match_independent_state_model()
  for _, seed in ipairs(SEEDS) do
    setup()
    local next_value = generator(seed)
    local model = {[1] = new_song_model(), [96] = new_song_model()}
    local pattern_control = sequencer_control_generated:new(4, "pattern")
    local channel_control = sequencer_control_generated:new(4, "channel")

    -- Deterministic prefix guarantees both songs, every pattern, every channel and
    -- every step are targeted before the generated interaction sequence begins.
    for song_index, song_number in ipairs(SONGS) do
      program.set_selected_song_pattern(song_number)
      for pattern_number = 1, 16 do
        program.get().selected_pattern = pattern_number
        for local_step = 1, 4 do
          local step = (pattern_number - 1) * 4 + local_step
          local x, y = coords(step)
          pattern_control:press(x, y)
          model[song_number].patterns[pattern_number].trigs[step] = 1
          model[song_number].active = true
        end
      end
      for channel_number = 1, 16 do
        program.get().selected_channel = channel_number
        local start_step = channel_number
        local end_step = channel_number + 32
        local x1, y1 = coords(start_step)
        local x2, y2 = coords(end_step)
        luaunit.assert_true(channel_control:dual_press(x1, y1, x2, y2))
        model[song_number].ranges[channel_number] = {
          start_step = start_step, end_step = end_step
        }
      end
    end

    for operation = 1, OPERATIONS_PER_SEED do
      local song_number = SONGS[next_value(#SONGS)]
      local pattern_number = next_value(16)
      local channel_number = next_value(16)
      local step = next_value(64)
      local action = next_value(8)
      local context = "seed=" .. seed .. " operation=" .. operation ..
        " action=" .. action .. " song=" .. song_number ..
        " pattern=" .. pattern_number .. " channel=" .. channel_number

      program.set_selected_song_pattern(song_number)
      program.get().selected_pattern = pattern_number
      program.get().selected_channel = channel_number
      local expected_pattern = model[song_number].patterns[pattern_number]
      local x, y = coords(step)

      if action <= 3 then
        pattern_control:press(x, y)
        expected_pattern.trigs[step] = 1 - expected_pattern.trigs[step]
        model[song_number].active = true
      elseif action <= 5 then
        local end_step = next_value(64)
        local end_x, end_y = coords(end_step)
        pattern_control:dual_press(x, y, end_x, end_y)
        if expected_pattern.trigs[step] == 1 then
          if end_step == step then
            -- characterisation: the direct control accepts an equal-key call as 65;
            -- m_grid does not emit a two-key gesture for one physical key.
            expected_pattern.lengths[step] = 65
          else
            expected_pattern.lengths[step] = ((end_step - step) % 64) + 1
          end
        end
      elseif action == 6 then
        pattern_control:long_press(x, y)
        if expected_pattern.trigs[step] == 1 then expected_pattern.lengths[step] = 1 end
      else
        local other_step = next_value(64)
        local other_x, other_y = coords(other_step)
        local before = model[song_number].ranges[channel_number]
        local accepted = channel_control:dual_press(x, y, other_x, other_y)
        if other_step > step then
          luaunit.assert_true(accepted, context .. " accepted ascending range")
          model[song_number].ranges[channel_number] = {
            start_step = step, end_step = other_step
          }
        else
          luaunit.assert_false(accepted, context .. " rejected nonascending range")
          model[song_number].ranges[channel_number] = before
        end
      end

      assert_selected_state(model, song_number, pattern_number, channel_number, context)

      -- Periodically sample a second pattern/channel and the other song to catch
      -- writes leaking beyond the selected identities without making every action
      -- scan the full 2 x 16 x 64 state space.
      if operation % 17 == 0 then
        local probe_song = song_number == 1 and 96 or 1
        local probe_pattern = pattern_number % 16 + 1
        local probe_channel = channel_number % 16 + 1
        assert_selected_state(model, probe_song, probe_pattern, probe_channel,
          context .. " isolation probe")
      end
    end

    for _, song_number in ipairs(SONGS) do
      for pattern_number = 1, 16 do
        for channel_number = 1, 16 do
          assert_selected_state(model, song_number, pattern_number, channel_number,
            "seed=" .. seed .. " final sweep")
        end
      end
    end
  end
end
