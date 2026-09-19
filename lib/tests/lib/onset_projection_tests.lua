-- Characterisation of the pure onset recurrence extracted from m_lattice.
-- It reads a sprocket-shaped timing view but must not mutate it or a clock.
local projection = include("mosaic/lib/clock/onset_projection")

local function timing(overrides)
  local value = {
    ppqn = 96, division = 1 / 4,
    swing_or_shuffle = 1, shuffle_feel = 0, shuffle_basis = 0, shuffle_amount = 0,
    even_swing = 1, odd_swing = 1,
  }
  for key, item in pairs(overrides or {}) do value[key] = item end
  return value
end

local function copy(value)
  local result = {}
  for key, item in pairs(value) do result[key] = item end
  return result
end

function test_onset_projection_interval_matches_every_full_shuffle_feel_and_basis()
  for feel = 1, 4 do
    for basis = 1, 6 do
      local view = timing({swing_or_shuffle = 2, shuffle_feel = feel, shuffle_basis = basis, shuffle_amount = 1})
      local carry, total = .5, 0
      for step = 1, 8 do
        local interval
        interval, carry = projection.interval(view, 64, step, carry)
        total = total + interval
      end
      -- Every feel/basis redistributes exactly eight straight 1/4 intervals.
      luaunit.assert_equals(total, 768, "feel " .. feel .. " basis " .. basis)
    end
  end
end

function test_onset_projection_fractional_carry_and_future_pulse_projection_are_exact()
  local view = timing({division = 1 / (5.3 * 4)})
  local carry, intervals = .5, {}
  for step = 1, 12 do intervals[step], carry = projection.interval(view, 64, step, carry) end
  luaunit.assert_equals(intervals, {18,18,18,18,19,18,18,18,18,18,18,18})
  -- At a resolved step-1 onset current_ppqn is 18 and its carried remainder is .613207... .
  luaunit.assert_equals(projection.project_pulses(view, 64, 18, 96 / 5.3 + .5 - 18, 1, 6), 109)
end

function test_onset_projection_wraps_its_step_input_at_the_explicit_pattern_length()
  local view = timing({swing_or_shuffle = 2, shuffle_feel = 1, shuffle_basis = 1, shuffle_amount = 1})
  local carry, sequence = .5, {}
  for step = 1, 9 do
    local wrapped = ((step - 1) % 3) + 1
    sequence[step], carry = projection.interval(view, 3, wrapped, carry)
  end
  luaunit.assert_equals(sequence, {128,85,86,128,85,85,128,86,85})
end

function test_onset_projection_occurrence_uses_existing_phase_and_transport_offset_rules()
  local view = timing({division = 1 / 16, current_ppqn = 24, ppqn_error = .5, step = 1,
    phase = 2, shuffle_updated = true, onset_count = 1,
    last_processed_transport = 10, last_onset_transport = 10})
  luaunit.assert_equals(projection.project_occurrence(view, 64, 11, 2), 23)
end

function test_onset_projection_does_not_mutate_its_readonly_timing_view()
  local view = timing({swing_or_shuffle = 2, shuffle_feel = 4, shuffle_basis = 6, shuffle_amount = .5})
  view.current_ppqn, view.ppqn_error, view.step, view.phase = 18, .75, 6, 2
  view.shuffle_updated, view.onset_count = true, 4
  view.last_processed_transport, view.last_onset_transport = 20, 20
  local before = copy(view)
  projection.calculate(view, 7, 6)
  projection.interval(view, 7, 6, .75)
  projection.project_pulses(view, 7, 18, .75, 6, 8)
  projection.project_occurrence(view, 7, 21, 6)
  luaunit.assert_equals(view, before)
end
