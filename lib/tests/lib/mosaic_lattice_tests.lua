local l = include("mosaic/lib/mosaic_lattice")
local fn = include("mosaic/lib/functions")
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