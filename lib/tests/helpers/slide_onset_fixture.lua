-- Queue test intent through the real channel action, after its native
-- begin_cycle has resolved fractional carry and swing/shuffle phase.
local fixture = {}
-- Legacy tests load several m_clock tables. Production has one global module;
-- bind that name to the tested closure while it admits or invokes callbacks.
-- Restore it even on failure, so unrelated legacy tests retain their context.
local function invoke(module, callback, ...)
  local previous = _G.m_clock
  _G.m_clock = module
  local ok, result = pcall(callback, ...)
  _G.m_clock = previous
  if not ok then error(result, 0) end
  return result
end
function fixture.queue(_module, args, after_start)
  -- The legacy suite reloads this global module; init installs clocks there.
  local m_clock = _G.m_clock
  local sprocket = m_clock["channel_" .. args.channel_number .. "_clock"]
  _module["channel_" .. args.channel_number .. "_clock"] = sprocket
  local callback = args.func
  args.func = function(...) return invoke(_module, callback, ...) end
  if not sprocket._test_slide_queue then
    sprocket._test_slide_queue = {}
    local original = sprocket.action
    sprocket.action = function(t)
      original(t)
      local queued = sprocket._test_slide_queue
      sprocket._test_slide_queue = {}
      for _, entry in ipairs(queued) do
        -- Execute through the same module closure whose ring init/sampler ran.
        invoke(_module, _module.execute_action_across_steps_by_pulses, entry.args)
        if entry.after_start then invoke(_module, entry.after_start) end
      end
    end
  end
  table.insert(sprocket._test_slide_queue, {args = args, after_start = after_start})
end
function fixture.start_pending(module)
  for pulse = 1, 4096 do
    local pending = false
    for channel = 1, 16 do
      local clock = _G.m_clock["channel_" .. channel .. "_clock"]
      if clock and clock._test_slide_queue and #clock._test_slide_queue > 0 then pending = true end
    end
    if not pending then return end
    module.get_clock_lattice():pulse()
  end
  error("Queued slide did not reach a channel onset")
end
-- Isolated scheduler contract: the caller supplies an independently derived
-- onset-to-onset duration. This does not use the production projection result.
-- Actual application destination handoff is covered separately by native tests.
function fixture.observe(module, args, duration)
  local events, origin = {}, nil
  local original = args.func
  args.func = function(value, previous)
    events[#events + 1] = {pulse = module.get_clock_lattice().transport, value = value}
    original(value, previous)
  end
  fixture.queue(module, args, function() origin = module.get_clock_lattice().transport end)
  return function()
    luaunit.assert_not_nil(origin, "Slide request must reach its channel onset")
    -- The independent fixture starts its 8-pulse sampler at transport 1.
    local first_sample = 1 + math.ceil((origin - 1) / 8) * 8
    local final_sample = 1 + math.ceil((origin + duration - 1) / 8) * 8
    local count = (final_sample - first_sample) / 8 + 1
    luaunit.assert_equals(#events, count, "No missing, duplicate or post-endpoint samples")
    for index, event in ipairs(events) do
      local pulse = first_sample + (index - 1) * 8
      luaunit.assert_equals(event.pulse, pulse)
      local elapsed = pulse - origin
      local expected
      if elapsed >= duration then
        expected = args.end_value
      else
        expected = args.start_value + (args.end_value - args.start_value) * elapsed / duration
        if args.quant and args.quant > 0 then
          expected = math.floor(expected / args.quant + 0.5) * args.quant
        end
      end
      luaunit.assert_almost_equals(event.value, expected, 0.000000001)
    end
    luaunit.assert_equals(events[#events].value, args.end_value)
  end
end
return fixture
