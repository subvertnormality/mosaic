local l = include("mosaic/lib/mosaic_lattice")

local clock_controller = include("mosaic/lib/clock_controller")

local lattice

local function setup()
  lattice = l:new()
  lattice:toggle()
  lattice.pattern_length = 64
end


-- Setup function to create a new sprocket with default attributes
local function create_sprocket(args)
  local sprocket = lattice:new_sprocket({
      id = args.id or 1,
      division = args.division or 1 / 4,
      action = args.action or function() end,
      enabled = args.enabled ~= nil and args.enabled or true,
      swing = args.swing or 0,
      delay = args.delay or 0,
      ppqn = args.ppqn or 96,
      step = args.step or 1,
      swing_or_shuffle = args.swing_or_shuffle or 1, -- Swing
      shuffle_basis = args.shuffle_basis or 0,
      shuffle_feel = args.shuffle_feel or 0,
  })

  return sprocket
end

-- Progress the sprocket's phase manually
local function progress_lattice_pulse(pulses)
    for _ = 1, pulses do
      lattice:pulse()
    end
end

function test_sprocket_initialization()

  setup()

  local sprocket = create_sprocket({
      division = 1 / 4,
      swing = 10,
  })

  luaunit.assert_equals(sprocket.phase, 1)
  luaunit.assert_equals(sprocket.division, 1 / 4)
  luaunit.assert_equals(sprocket.swing, 10)
  luaunit.assert_equals(sprocket.ppqn, 96) -- Default ppqn
end


function test_swing_update()

  setup()

  local sprocket = create_sprocket({
      swing = 20, -- 20% swing
  })

  sprocket:update_swing()
  luaunit.assert_equals(sprocket.even_swing, 1.2) -- 20% increase
  luaunit.assert_equals(sprocket.odd_swing, 0.8)  -- 20% decrease

  -- Test for negative swing
  sprocket:set_swing(-30)
  luaunit.assert_equals(sprocket.even_swing, 0.7)
  luaunit.assert_equals(sprocket.odd_swing, 1.3)
end

function test_shuffle_update()

  setup()

  local sprocket = create_sprocket({
      division = 1 / 8,
      shuffle_feel = 1, -- Smooth
      shuffle_basis = 2, -- Moderate shuffle basis
      swing_or_shuffle = 2, -- Shuffle mode
  })

  -- Manually update shuffle on step 1
  sprocket:update_shuffle(1)
  luaunit.assert_not_equals(sprocket.current_ppqn, math.floor(96 / 8)) -- It should now reflect the shuffle value
end


function test_phase_and_step_progression()

  setup()

  local division = clock_controller.calculate_divisor(clock_controller.get_clock_divisions()[13])

  local sprocket = create_sprocket({
      division = 1 / (division * 4),
  })

  -- Simulate progressing the sprocket phase manually
  progress_lattice_pulse(24) -- One beat (24 pulses)
  luaunit.assert_equals(sprocket.step, 2)
  
  -- Complete a full cycle (96 pulses in total for 1/4 note)
  progress_lattice_pulse(72) -- Additional 72 pulses
  luaunit.assert_equals(sprocket.phase, 1) -- Reset after full cycle
  luaunit.assert_equals(sprocket.step, 5)  -- Step incremented
end

function test_delay_handling()

  setup()

  local division = clock_controller.calculate_divisor(clock_controller.get_clock_divisions()[13])


  local sprocket = create_sprocket({
    division = 1 / (division * 4),
    delay = 0.5, -- Half of the division delayed
  })

  -- Check the initial phase is reduced due to delay
  luaunit.assert_equals(sprocket.phase, 1 - (96 / 4) * 0.5)

  -- Progress through the delay and ensure action is delayed
  progress_lattice_pulse(36)
  luaunit.assert_equals(sprocket.step, 2)  -- Step incremented
end


function test_enable_and_disable_sprocket()

  setup()

  local sprocket = create_sprocket({
      enabled = true,
  })

  luaunit.assert_true(sprocket.enabled)

  -- Disable the sprocket and ensure it doesn't run
  sprocket:stop()
  luaunit.assert_false(sprocket.enabled)

  -- Enable it again
  sprocket:start()
  luaunit.assert_true(sprocket.enabled)
end

function test_sprocket_destroy()

  setup()

  local sprocket = create_sprocket({
      enabled = true,
  })

  sprocket:destroy()
  luaunit.assert_false(sprocket.enabled)
  luaunit.assert_true(sprocket.flag) -- Destroyed sprocket should be flagged for removal
end

function test_change_division_mid_pattern()

  setup()

  local division_div_2 = clock_controller.calculate_divisor(clock_controller.get_clock_divisions()[15])
  local division = clock_controller.calculate_divisor(clock_controller.get_clock_divisions()[13])
  
  local sprocket = create_sprocket({
      division = 1 / (division_div_2 * 4),
  })

  -- Progress halfway through the first cycle
  progress_lattice_pulse(24)
  luaunit.assert_equals(sprocket.phase, 25)
  luaunit.assert_equals(sprocket.current_ppqn, 48)

  -- Change the division to 1/4
  sprocket:set_division(1 / (division * 4))
  luaunit.assert_equals(sprocket.current_ppqn, 24)

  -- Verify the phase has been updated to reflect the new division
  luaunit.assert_equals(sprocket.division, 1 / (division * 4))
  luaunit.assert_equals(sprocket.phase, 13)


end


function test_simultaneous_swing_and_shuffle_changes()

  setup()

  local division = clock_controller.calculate_divisor(clock_controller.get_clock_divisions()[13])

  local sprocket = create_sprocket({
      division = 1 / (division * 4),
      swing = 5,
      shuffle_basis = 1,
      shuffle_feel = 1,
      swing_or_shuffle = 2, -- Shuffle active
  })

  -- Progress sprocket for initial phase
  progress_lattice_pulse(24)

  -- Change swing and shuffle simultaneously
  sprocket:set_swing(40)
  sprocket:set_shuffle_feel(2)

  -- Verify both swing and shuffle changes were applied
  luaunit.assert_true(sprocket.even_swing > sprocket.odd_swing)
  luaunit.assert_not_equals(sprocket.current_ppqn, 96 / 16) -- Shuffle affected timing
end


-- Test changing swing mid-pattern and check for phase consistency
function test_changing_swing_mid_pattern()

  setup()

  local sprocket = create_sprocket({
      division = 1 / 4,
      swing = 0,  -- Start with no swing
  })

  local initial_ppqn = sprocket.current_ppqn

  -- Simulate progression up to half of the pattern (2 steps)
  local pulses_to_half_pattern = sprocket.current_ppqn * 2
  progress_lattice_pulse(pulses_to_half_pattern)

  -- Check phase and step before changing swing
  local phase_before = sprocket.phase
  local step_before = sprocket.step

  -- Change the swing mid-pattern
  sprocket:set_swing(30)

  -- Continue progression
  progress_lattice_pulse(pulses_to_half_pattern)

  -- Check that phase and step are consistent
  luaunit.assert_equals(sprocket.phase, phase_before)
  luaunit.assert_equals(sprocket.step, step_before + 2)

  -- Verify that the PPQN has been updated
  luaunit.assert_not_equals(sprocket.current_ppqn, initial_ppqn)
end

-- Test that the sum of PPQNs over a pattern adds up correctly
function test_shuffle_ppqn_sum()

  setup()

  local sprocket = create_sprocket({
      division = 1 / 4,
      swing_or_shuffle = 2, -- Shuffle mode
      shuffle_feel = 1,     -- Some feel
      shuffle_basis = 3,    -- Some basis
  })

  local total_pulses = 0
  local expected_total_pulses = sprocket.ppqn * 4  -- For 4 steps (1 full pattern)

  -- Simulate a full pattern progression and sum the PPQNs
  for step = 1, 4 do
      sprocket:update_shuffle(step)
      total_pulses = total_pulses + sprocket.current_ppqn
  end

  -- Check that total pulses add up to expected total
  luaunit.assert_equals(total_pulses, expected_total_pulses)
end

-- Test phase consistency with multiple changes in swing and shuffle
function test_phase_consistency_with_shuffle_changes()

  setup()

  local sprocket = create_sprocket({
      division = 1 / 4,
      swing_or_shuffle = 2, -- Shuffle mode
      shuffle_feel = 1,     -- Initial feel
      shuffle_basis = 1,    -- Initial basis
  })

  -- Store initial state
  local initial_phase = sprocket.phase
  local initial_step = sprocket.step

  -- Simulate progression and change shuffle parameters every step
  for i = 1, 8 do
      -- Progress the lattice by one pulse
      progress_lattice_pulse(1)

      -- Change shuffle parameters
      local new_feel = ((i - 1) % 4) + 1  -- Cycle through feels 1 to 4
      local new_basis = ((i - 1) % 6) + 1 -- Cycle through bases 1 to 6

      sprocket:set_shuffle_feel(new_feel)
      sprocket:set_shuffle_basis(new_basis)

      -- Check that step increments correctly
      if sprocket.phase > sprocket.current_ppqn then
          sprocket.phase = sprocket.phase - sprocket.current_ppqn
          sprocket.step = sprocket.step + 1
      end

      -- Assert that the sprocket's step is as expected
      luaunit.assert_equals(sprocket.step, initial_step + math.floor((sprocket.transport - 1) / sprocket.current_ppqn))
  end
end


-- Test multiple permutations of shuffle basis and feels for phase issues
function test_multiple_basis_and_feels()

  setup()

  local basis_values = {1, 2, 3, 4, 5, 6}
  local feel_values = {1, 2, 3, 4}

  for _, basis in ipairs(basis_values) do
      for _, feel in ipairs(feel_values) do
          local sprocket = create_sprocket({
              division = 1 / 4,
              swing_or_shuffle = 2, -- Shuffle mode
              shuffle_feel = feel,
              shuffle_basis = basis,
          })

          -- Simulate a full pattern progression
          local total_pulses = 0
          local expected_total_pulses = sprocket.ppqn * 4  -- For 4 steps

          for step = 1, 4 do
              sprocket:update_shuffle(step)
              total_pulses = total_pulses + sprocket.current_ppqn
          end

          -- Check that total pulses add up to expected total
          luaunit.assert_equals(total_pulses, expected_total_pulses, "Mismatch in total pulses for basis " .. basis .. " and feel " .. feel)
      end
  end
end

-- Test changing division mid-pattern and verify phase consistency
function test_change_division_mid_pattern_phase_consistency()

  setup()

  local division1 = 1 / 4
  local division2 = 1 / 8

  local sprocket = create_sprocket({
      division = division1,
  })

  -- Simulate progression up to 2 steps

  local pulses_for_two_steps = sprocket.current_ppqn * 2
  progress_lattice_pulse(pulses_for_two_steps)

  luaunit.assert_equals(sprocket.step, 3)


  -- Change division mid-pattern
  sprocket:set_division(division2)
  sprocket:update_swing()
  sprocket:update_shuffle(sprocket.step)

  -- Store the state after changing division
  local phase_after_division_change = sprocket.phase
  local step_after_division_change = sprocket.step

  -- Continue progression
  progress_lattice_pulse(sprocket.current_ppqn * 2)

  -- Verify phase consistency
  luaunit.assert_equals(sprocket.phase, phase_after_division_change)
  luaunit.assert_equals(sprocket.step, step_after_division_change + 2)
end

-- Test that delay continues to work when changing swing/shuffle
function test_delay_with_swing_shuffle_changes()

  setup()

  local sprocket = create_sprocket({
      division = 1 / 4,
      delay = 0.25, -- Delay by a quarter of the division
      swing = 0,
      swing_or_shuffle = 1, -- Swing mode
  })

  -- Simulate progression up to the action trigger
  progress_lattice_pulse(sprocket.current_ppqn * sprocket.delay)

  local action_triggered = false
  sprocket.action = function()
      action_triggered = true
  end

  -- Verify action is triggered after delay
  luaunit.assert_false(action_triggered)
  progress_lattice_pulse(1)
  luaunit.assert_true(action_triggered)

  -- Change swing and shuffle parameters mid-pattern
  sprocket:set_swing(20)
  sprocket:set_swing_or_shuffle(2) -- Switch to shuffle
  sprocket:set_shuffle_feel(2)
  sprocket:set_shuffle_basis(2)
  sprocket:update_swing()
  sprocket:update_shuffle(sprocket.step)

  -- Reset action trigger flag
  action_triggered = false

  -- Simulate next step
  progress_lattice_pulse(sprocket.current_ppqn)

  luaunit.assert_true(action_triggered)
end

-- Test that the total pulses account for swing adjustments
function test_total_pulses_with_swing()

  setup()

  local sprocket = create_sprocket({
      division = 1 / 4,
      swing = 50, -- Maximum swing
  })

  -- Simulate a full pattern progression
  local total_pulses = 0

  for step = 1, 4 do
      sprocket:update_swing()
      sprocket:update_shuffle(sprocket.step)
      total_pulses = total_pulses + sprocket.current_ppqn
      sprocket.step = sprocket.step + 1
  end

  local expected_total_pulses = sprocket.ppqn * 4  -- Should be consistent regardless of swing
  luaunit.assert_equals(total_pulses, expected_total_pulses)
end

-- Test that the sprocket correctly handles division changes with delay applied
function test_delay_with_division_change()

  setup()

  local sprocket = create_sprocket({
      division = 1 / 4,
      delay = 0.5, -- Delay by half division
  })

  -- Simulate one step
  progress_lattice_pulse(sprocket.current_ppqn)

  -- Change division
  sprocket:set_division(1 / 8)
  sprocket:update_swing()
  sprocket:update_shuffle(sprocket.step)

  -- Check that delay still works correctly
  local action_triggered = false
  sprocket.action = function()
      action_triggered = true
  end

  -- Simulate next step with new division
  progress_lattice_pulse(sprocket.current_ppqn * (1 - sprocket.delay))
  luaunit.assert_false(action_triggered)
  progress_lattice_pulse(sprocket.current_ppqn * sprocket.delay)
  luaunit.assert_true(action_triggered)
end

-- Test that cumulative PPQN errors are handled correctly over many steps
function test_cumulative_ppqn_error_over_time()

  setup()

  local sprocket = create_sprocket({
      division = 1 / 4,
      swing_or_shuffle = 2, -- Shuffle mode
      shuffle_feel = 1,
      shuffle_basis = 1,
  })

  local total_pulses = 0
  local expected_total_pulses = sprocket.ppqn * 100  -- Over 100 steps

  for step = 1, 100 do
      sprocket:update_shuffle(step)
      total_pulses = total_pulses + sprocket.current_ppqn
  end

  -- Allow for small floating-point inaccuracies
  luaunit.assertAlmostEquals(total_pulses, expected_total_pulses, 1e-6)
end


function test_ppqn_swing_stability_over_time()
  setup()
  local sprocket = create_sprocket({
    division = 1/4,
    swing_or_shuffle = 1, -- Swing mode
    swing = 25
  })
  
  local expected_ppqn = 96 * 2 -- Default PPQN for 1/4 division over two steps
  local total_steps = 1000 -- Run for 1000 steps
  local expected_pulses = 1000 * 96
  local accum = 1
  local total = 0

  for i = 1, total_steps do
    progress_lattice_pulse(sprocket.current_ppqn)
    sprocket:update_swing()
    sprocket:update_shuffle(sprocket.step)
    
    total = total + sprocket.current_ppqn
    if accum % 2 == 0 then
      accum = 1
      luaunit.assertAlmostEquals(total, expected_ppqn * (i / 2), 1)
    else
      accum = accum + 1
    end
  end
  
  -- Verify no significant drift in total pulses
  local actual_pulses = sprocket.transport - 1
  luaunit.assertAlmostEquals(actual_pulses, expected_pulses, expected_pulses * 0.001) -- Allow 0.1% tolerance
end


function test_ppqn_swing_stability_over_time_odd_pattern_length()
  setup()

  lattice:set_pattern_length(63)


  local sprocket = create_sprocket({
    division = 1/4,
    swing_or_shuffle = 1, -- Swing mode
    swing = 25
  })
  
  local expected_ppqn = 96 * 2 -- Default PPQN for 1/4 division over two steps
  local total_steps = 252 -- Run for 100 steps
  local expected_pulses = 252 * 96

  local total = 0

  for i = 1, total_steps do
    progress_lattice_pulse(1)
    progress_lattice_pulse(sprocket.current_ppqn - 1)

    total = total + sprocket.current_ppqn

    local step_mod = (sprocket.step % sprocket.lattice.pattern_length) + 1
    if sprocket.step < sprocket.lattice.pattern_length then
      step_mod = sprocket.step + 1
    end

    if sprocket.step % sprocket.lattice.pattern_length + 1 == 0 then
      luaunit.assertAlmostEquals((total / 96) % 63, 0, 1)
    end
  end
  
  -- Verify no significant drift in total pulses
  local actual_pulses = sprocket.transport - 1
  luaunit.assertAlmostEquals(actual_pulses, expected_pulses, expected_pulses * 0.001) -- Allow 0.1% tolerance
end



function test_ppqn_shuffle_stability_over_time_odd_pattern_length()
  setup()

  lattice:set_pattern_length(63)


  local sprocket = create_sprocket({
    division = 1/4,
    swing_or_shuffle = 2, -- Swing mode
    shuffle_feel = 1, -- Smooth
    shuffle_basis = 2, -- Moderate shuffle basis
    shuffle_amount = 100
  })
  
  local expected_ppqn = 96 * 2 -- Default PPQN for 1/4 division over two steps
  local total_steps = 2520
  local expected_pulses = 2520 * 96

  local total = 0

  for i = 1, total_steps do
    progress_lattice_pulse(1)
    progress_lattice_pulse(sprocket.current_ppqn - 1)

    total = total + sprocket.current_ppqn

    local step_mod = (sprocket.step % sprocket.lattice.pattern_length) + 1
    if sprocket.step < sprocket.lattice.pattern_length then
      step_mod = sprocket.step + 1
    end

    if sprocket.step % sprocket.lattice.pattern_length + 1 == 0 then
      luaunit.assertAlmostEquals((total / 96) % 63, 0, 1)
    end
  end
  
  -- Verify no significant drift in total pulses
  local actual_pulses = sprocket.transport - 1
  luaunit.assertAlmostEquals(actual_pulses, expected_pulses, expected_pulses * 0.001) -- Allow 0.1% tolerance
end

function test_shuffle_pattern_reset_at_pattern_boundaries()
  setup()
  
  local sprocket = create_sprocket({
    division = 1/4,
    swing_or_shuffle = 2,
    shuffle_feel = 1,
    shuffle_basis = 2,
    shuffle_amount = 100
  })
  
  -- Store initial timing pattern
  local initial_timings = {}
  for i = 1, 8 do
    initial_timings[i] = sprocket.current_ppqn
    progress_lattice_pulse(sprocket.current_ppqn)
  end
  
  -- Progress to next pattern and compare
  local second_pattern_timings = {}
  for i = 1, 8 do
    second_pattern_timings[i] = sprocket.current_ppqn
    progress_lattice_pulse(sprocket.current_ppqn)
  end
  
  -- Verify pattern resets correctly
  for i = 1, 8 do
    luaunit.assert_equals(initial_timings[i], second_pattern_timings[i])
  end
end

function test_shuffle_at_extreme_divisions()
  setup()
  
  local test_divisions = {1/32, 1/16, 1/8, 1/4, 1/2, 1, 2}
  
  for _, div in ipairs(test_divisions) do
    local sprocket = create_sprocket({
      division = div / 4,
      swing_or_shuffle = 2,
      shuffle_feel = 1,
      shuffle_basis = 2,
      shuffle_amount = 100
    })
    
    local total_pulses = 0
    local expected_pulses = sprocket.ppqn * 4 * div
    
    -- Run one pattern
    for i = 1, 4 do
      progress_lattice_pulse(sprocket.current_ppqn)
      total_pulses = total_pulses + sprocket.current_ppqn
    end
    
    luaunit.assertAlmostEquals(total_pulses, expected_pulses, 1)
  end
end

function test_shuffle_with_delayed_actions()
  setup()
  
  local action_log = {}
  local sprocket = create_sprocket({
    division = 1/4,
    swing_or_shuffle = 2,
    shuffle_feel = 1,
    shuffle_basis = 2,
    shuffle_amount = 100,
    delay = 0.25
  })
  
  sprocket.action = function()
    table.insert(action_log, sprocket.transport)
  end
  
  -- Run multiple patterns and verify delayed actions
  for i = 1, 16 do
    progress_lattice_pulse(sprocket.current_ppqn)
    
    if #action_log > 0 then
      local last_action = action_log[#action_log]
      -- Verify action happened after delay
      luaunit.assert_true(last_action >= sprocket.current_ppqn * sprocket.delay)
    end
  end
end

function test_shuffle_with_pattern_length_changes()
  setup()
  
  local sprocket = create_sprocket({
    division = 1/4,
    swing_or_shuffle = 2,
    shuffle_feel = 1,
    shuffle_basis = 2,
    shuffle_amount = 100
  })
  
  local test_lengths = {4, 8, 12, 16, 32}
  
  for _, length in ipairs(test_lengths) do
    lattice:set_pattern_length(length)
    
    local total_pulses = 0
    local expected_per_step = sprocket.ppqn
    
    -- Run one full pattern
    for step = 1, length do
      progress_lattice_pulse(sprocket.current_ppqn)
      total_pulses = total_pulses + sprocket.current_ppqn
    end
    
    -- Verify total timing for pattern
    luaunit.assertAlmostEquals(total_pulses, expected_per_step * length, 1)
  end
end

function test_shuffle_maintains_timing_across_short_patterns()
  setup()
  
  local test_lengths = {6, 7, 10, 12, 14, 15}
  
  for _, pattern_length in ipairs(test_lengths) do
    lattice:set_pattern_length(pattern_length)
    
    local sprocket = create_sprocket({
      division = 1/4,
      swing_or_shuffle = 2,
      shuffle_feel = 1,
      shuffle_basis = 2,
      shuffle_amount = 100
    })
    
    local patterns_data = {}
    
    for pattern = 1, 4 do
      local pattern_data = {
        steps = {},
        total_pulses = 0,
        shuffle_positions = {}
      }
      
      for step = 1, pattern_length do
        sprocket:update_shuffle(step)
        local step_data = {
          ppqn = sprocket.current_ppqn,
          shuffle_position = ((step - 1) % 8) + 1,
          actual_step = sprocket.step
        }
        table.insert(pattern_data.steps, step_data)
        pattern_data.total_pulses = pattern_data.total_pulses + step_data.ppqn
        table.insert(pattern_data.shuffle_positions, step_data.shuffle_position)
        
        progress_lattice_pulse(step_data.ppqn)
      end
      
      table.insert(patterns_data, pattern_data)
      
      -- Verify each step in pattern follows correct shuffle map
      for step = 1, pattern_length do
        local step_data = pattern_data.steps[step]
        local feel_map = {4/14, 4/14, 3/14, 3/14, 4/14, 4/14, 3/14, 3/14} -- Smooth feel, basis 2
        local expected_multiplier = feel_map[step_data.shuffle_position]
        local base_multiplier = 0.25
        
        -- Match the exact calculation from update_shuffle()
        local adjusted_multiplier = base_multiplier + sprocket.shuffle_amount * (expected_multiplier - base_multiplier)
        local ppc = sprocket.ppqn * 4
        local exact_ppqn = ((sprocket.division * 4) * ppc) * adjusted_multiplier
        local expected_ppqn = math.floor(exact_ppqn + 0.5) -- Round to nearest integer
        
        luaunit.assertAlmostEquals(
          step_data.ppqn,
          expected_ppqn,
          1,
          string.format(
            "Pattern %d, Step %d shuffle timing incorrect (length %d, shuffle pos %d)\nExpected multiplier: %f\nGot ppqn: %d, Expected: %d",
            pattern, step, pattern_length, step_data.shuffle_position,
            expected_multiplier, step_data.ppqn, expected_ppqn
          )
        )
      end
    end
  end
end

function test_shuffle_pattern_boundaries_with_short_lengths()
  setup()
  
  local test_lengths = {5, 7, 10, 14}
  
  for _, pattern_length in ipairs(test_lengths) do
    lattice:set_pattern_length(pattern_length)
    
    local sprocket = create_sprocket({
      division = 1/4,
      swing_or_shuffle = 2,
      shuffle_feel = 1,
      shuffle_basis = 2,
      shuffle_amount = 100
    })
    
    -- Run exactly one pattern plus one step
    local step_timings = {}
    local total_pulses = 0
    
    -- Collect timings for full pattern
    for step = 1, pattern_length do
      sprocket:update_shuffle(step)
      step_timings[step] = sprocket.current_ppqn
      progress_lattice_pulse(sprocket.current_ppqn)
      total_pulses = total_pulses + sprocket.current_ppqn
    end
    
    -- Check first step of next pattern
    sprocket:update_shuffle(pattern_length + 1)
    luaunit.assert_equals(sprocket.current_ppqn, step_timings[1],
      string.format("First step timing mismatch after pattern boundary with length %d",
                   pattern_length))
  end
end

function test_shuffle_timing_consistency_with_short_patterns()
  setup()
  
  local test_lengths = {6, 10, 14}
  
  for _, pattern_length in ipairs(test_lengths) do
    lattice:set_pattern_length(pattern_length)
    
    -- Test multiple shuffle feels and bases
    for feel = 1, 4 do
      for basis = 1, 6 do
        local sprocket = create_sprocket({
          division = 1/4,
          swing_or_shuffle = 2,
          shuffle_feel = feel,
          shuffle_basis = basis,
          shuffle_amount = 100
        })
        
        local total_pulses = 0
        local total_patterns = 3
        
        -- Run and verify multiple complete patterns
        for pattern = 1, total_patterns do
          local pattern_pulses = 0
          
          for step = 1, pattern_length do
            sprocket:update_shuffle(step)
            pattern_pulses = pattern_pulses + sprocket.current_ppqn
            progress_lattice_pulse(sprocket.current_ppqn)
          end
          
          -- Each pattern should have consistent total length
          luaunit.assertAlmostEquals(pattern_pulses, sprocket.ppqn * pattern_length, 1,
            string.format("Pattern %d timing inconsistent with length %d, feel %d, basis %d",
                       pattern, pattern_length, feel, basis))
          
          total_pulses = total_pulses + pattern_pulses
        end
      end
    end
  end
end

function test_shuffle_step_transitions_short_patterns()
  setup()
  
  local test_lengths = {5, 7, 10}
  
  for _, pattern_length in ipairs(test_lengths) do
    lattice:set_pattern_length(pattern_length)
    
    local sprocket = create_sprocket({
      division = 1/4,
      swing_or_shuffle = 2,
      shuffle_feel = 1,
      shuffle_basis = 2,
      shuffle_amount = 100
    })

    -- Run 3 complete patterns checking step transitions
    local total_steps = pattern_length * 3
    
    -- Check initial state
    luaunit.assert_equals(sprocket.step, 1, "Initial step should be 1")
    
    for i = 1, total_steps do
      local current_step = ((sprocket.step - 1) % pattern_length) + 1
      local expected_step = ((i - 1) % pattern_length) + 1
      
      -- Verify current step before pulse
      luaunit.assert_equals(
        current_step, 
        expected_step,
        string.format("\nPattern length: %d\nStep: %d\nExpected step: %d\nActual step: %d\nCurrent PPQN: %d",
          pattern_length,
          i,
          expected_step,
          current_step,
          sprocket.current_ppqn
        )
      )
      
      -- Store current ppqn
      local current_ppqn = sprocket.current_ppqn
      
      -- Progress the lattice
      progress_lattice_pulse(current_ppqn)
    end
  end
end

function test_basic_step_increment()
  setup()
  
  local pattern_length = 5
  lattice:set_pattern_length(pattern_length)
  
  local sprocket = create_sprocket({
    division = 1/4,
    swing_or_shuffle = 2,
    shuffle_feel = 1,
    shuffle_basis = 2,
    shuffle_amount = 100
  })
  
  -- Debug array to track steps
  local steps = {sprocket.step}
  
  -- Test first few steps explicitly
  luaunit.assert_equals(sprocket.step, 1, "Initial step should be 1")
  
  progress_lattice_pulse(sprocket.current_ppqn)
  table.insert(steps, sprocket.step)
  luaunit.assert_equals(sprocket.step, 2, "Step should increment to 2")
  
  progress_lattice_pulse(sprocket.current_ppqn)
  table.insert(steps, sprocket.step)
  luaunit.assert_equals(sprocket.step, 3, "Step should increment to 3")
  
  -- Step just to the pattern boundary (need 2 more steps to get to 5)
  for i = 1, 2 do
    progress_lattice_pulse(sprocket.current_ppqn)
    table.insert(steps, sprocket.step)
  end
  
  -- One more step to wrap
  progress_lattice_pulse(sprocket.current_ppqn)
  table.insert(steps, sprocket.step)
  
  luaunit.assert_equals(
    ((sprocket.step - 1) % pattern_length) + 1, 
    1, 
    string.format("Step should wrap to 1 after pattern length (got %d)", sprocket.step)
  )
end

function test_step_wrapping_simple()
  setup()
  
  local pattern_length = 4
  lattice:set_pattern_length(pattern_length)
  
  local sprocket = create_sprocket({
    division = 1/4,
  })

  -- Track steps through exactly one pattern
  local steps = {}
  
  for i = 1, pattern_length + 1 do
    table.insert(steps, sprocket.step)
    progress_lattice_pulse(sprocket.current_ppqn)
  end
  
  luaunit.assert_equals(steps[1], 1, "Should start at 1")
  luaunit.assert_equals(steps[pattern_length + 1], 1, "Should wrap back to 1")
end