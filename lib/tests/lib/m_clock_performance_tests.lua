local clock = os.clock

step = include("mosaic/lib/step")
pattern = include("mosaic/lib/pattern")

local m_clock = include("mosaic/lib/clock/m_clock")
local quantiser = include("mosaic/lib/quantiser")

-- Mocks
include("mosaic/lib/tests/helpers/mocks/sinfonion_mock")
include("mosaic/lib/tests/helpers/mocks/params_mock")
include("mosaic/lib/tests/helpers/mocks/m_midi_mock")
include("mosaic/lib/tests/helpers/mocks/channel_edit_page_ui_mock")
include("mosaic/lib/tests/helpers/mocks/device_map_mock")
include("mosaic/lib/tests/helpers/mocks/norns_mock")
include("mosaic/lib/tests/helpers/mocks/channel_sequence_page_mock")
include("mosaic/lib/tests/helpers/mocks/channel_edit_page_mock")

local function setup()
  program.init()
  globals.reset()
  params.reset()
end

local function clock_setup()
  m_clock.init()
  m_clock:start()
end

local function progress_clock_by_beats(b)
  for i = 1, (24 * b) do
    m_clock.get_clock_lattice():pulse()
  end
end

local function progress_clock_by_pulses(p)
  for i = 1, p do
    m_clock.get_clock_lattice():pulse()
  end
end


-- Helper to generate test data
local function generate_test_actions(count)
  local actions = {}
  for i = 1, count do
    actions[i] = {
      channel_number = (i % 16) + 1,
      trig_lock = (i % 10) + 1,
      start_step = 1,
      end_step = 64,
      start_value = 0,
      end_value = 127,
      quant = 1,
      func = function(val) end,
      should_wrap = true
    }
  end
  return actions
end

-- Memory usage helper
local function get_memory_usage()
  collectgarbage("collect")
  return collectgarbage("count")
end

-- Benchmark helper
local function benchmark_operation(name, operation, iterations)
  local start_time = clock()
  local start_memory = get_memory_usage()
  
  -- Run operation multiple times
  for i = 1, iterations do
    operation()
  end
  
  local end_time = clock()
  local end_memory = get_memory_usage()
  
  return {
    name = name,
    time = end_time - start_time,
    memory_delta = end_memory - start_memory,
    iterations = iterations
  }
end


function test_massive_concurrent_automation_with_param_slides()
  setup()
  clock_setup()
  
  local start_memory = get_memory_usage()
  local start_time = clock()
  
  -- Configuration
  local channels = 16
  local patterns_per_channel = 4
  local steps_per_pattern = 64
  local automation_points = 32
  local total_runtime_pulses = 96 * 16 -- 16 bars worth
  
  -- Track performance metrics
  local peak_memory = start_memory
  local action_count = 0
  local processed_values = 0
  
  -- Parameter types for slides
  local param_types = {
    { name = "cutoff", min = 0, max = 127, quant = 1 },
    { name = "resonance", min = 0, max = 127, quant = 1 },
    { name = "attack", min = 0, max = 127, quant = 0.1 },
    { name = "decay", min = 0, max = 127, quant = 0.1 },
    { name = "sustain", min = 0, max = 127, quant = 1 },
    { name = "release", min = 0, max = 127, quant = 0.1 },
    { name = "pan", min = -63, max = 63, quant = 1 },
    { name = "delay_send", min = 0, max = 127, quant = 1 },
    { name = "reverb_send", min = 0, max = 127, quant = 1 },
    { name = "probability", min = 0, max = 100, quant = 0.1 }
  }
  
  -- Create complex automation patterns for each channel
  for channel = 1, channels do
    for pattern = 1, patterns_per_channel do
      -- Create multiple overlapping automations per pattern
      for point = 1, automation_points do
        local start_step = math.random(1, steps_per_pattern - 8)
        local end_step = math.min(start_step + math.random(4, 16), steps_per_pattern)
        
        -- Create different types of automation
        local param = param_types[(point % #param_types) + 1]
        local automation_type = point % 4
        local start_value, end_value, quant
        
        if automation_type == 0 then
          -- Full range sweep
          start_value = param.min
          end_value = param.max
          quant = param.quant
        elseif automation_type == 1 then
          -- Fine control around center
          local center = (param.max + param.min) / 2
          start_value = center - param.quant * 5
          end_value = center + param.quant * 5
          quant = param.quant
        elseif automation_type == 2 then
          -- High to low
          start_value = param.max
          end_value = param.min
          quant = param.quant * 2
        else
          -- Random range with fine control
          start_value = param.min + math.random() * (param.max - param.min)
          end_value = param.min + math.random() * (param.max - param.min)
          quant = param.quant / 2
        end
        
        -- Add some overlapping slides
        if point % 3 == 0 then
          -- Create a slide that overlaps with the next automation
          local slide_end = math.min(end_step + math.random(2, 8), steps_per_pattern)
          m_clock.execute_action_across_steps_by_pulses({
            channel_number = channel,
            trig_lock = (pattern * automation_points + point) % 10 + 1,
            start_step = end_step,
            end_step = slide_end,
            start_value = end_value,
            end_value = param.min + math.random() * (param.max - param.min),
            quant = param.quant,
            func = function(val)
              processed_values = processed_values + 1
            end,
            should_wrap = true
          })
          action_count = action_count + 1
        end
        
        -- Create the main automation
        m_clock.execute_action_across_steps_by_pulses({
          channel_number = channel,
          trig_lock = (pattern * automation_points + point) % 10 + 1,
          start_step = start_step,
          end_step = end_step,
          start_value = start_value,
          end_value = end_value,
          quant = quant,
          func = function(val)
            processed_values = processed_values + 1
          end,
          should_wrap = true
        })
        
        action_count = action_count + 1
        
        -- Add some wrapping slides
        if point % 5 == 0 and end_step > steps_per_pattern - 4 then
          -- Create a slide that wraps around to the start
          m_clock.execute_action_across_steps_by_pulses({
            channel_number = channel,
            trig_lock = (pattern * automation_points + point) % 10 + 1,
            start_step = end_step,
            end_step = 4,
            start_value = end_value,
            end_value = param.min + math.random() * (param.max - param.min),
            quant = param.quant,
            func = function(val)
              processed_values = processed_values + 1
            end,
            should_wrap = true
          })
          action_count = action_count + 1
        end
      end
    end
  end
  
  local setup_time = clock() - start_time
  
  -- Process the automation
  local process_start = clock()
  local last_memory = get_memory_usage()
  local memory_samples = {}
  
  -- Track timing consistency
  local processing_times = {}
  local max_process_time = 0
  local min_process_time = math.huge
  
  -- Run for 16 bars worth of pulses
  for pulse = 1, total_runtime_pulses do
    local pulse_start = clock()
    progress_clock_by_pulses(1)
    local pulse_time = clock() - pulse_start
    
    table.insert(processing_times, pulse_time)
    max_process_time = math.max(max_process_time, pulse_time)
    min_process_time = math.min(min_process_time, pulse_time)
    
    -- Sample memory every bar
    if pulse % 96 == 0 then
      collectgarbage("collect")
      local current_memory = get_memory_usage()
      peak_memory = math.max(peak_memory, current_memory)
      table.insert(memory_samples, current_memory)
      last_memory = current_memory
    end
  end
  
  -- Calculate timing statistics
  local avg_process_time = 0
  local timing_variance = 0
  for _, time in ipairs(processing_times) do
    avg_process_time = avg_process_time + time
  end
  avg_process_time = avg_process_time / #processing_times
  
  for _, time in ipairs(processing_times) do
    timing_variance = timing_variance + (time - avg_process_time) ^ 2
  end
  timing_variance = math.sqrt(timing_variance / #processing_times)
  
  -- Verify performance meets requirements
  luaunit.assert_true(max_process_time < 0.002, -- 2ms max processing time per pulse
    "Maximum processing time exceeded 2ms")
  luaunit.assert_true(timing_variance < 0.001, -- 1ms timing variance
    "Timing variance exceeded 1ms")
  luaunit.assert_true((peak_memory - start_memory) < 1024,
    "Memory usage exceeded 1MB")
end 