-- Characterisation of the existing dynamic clock binding, not manual text.
function test_slide_realign_uses_replacement_clock_without_emitting_a_sample()
  local lifetime = include("mosaic/lib/clock/slide_lifetime")
  local current = {quantize_value = function(value) return value end,
    channel_1_clock = {realign = false}}
  local model = {
    get = function() return {selected_song_pattern = 1} end,
    get_channel = function() return {} end,
    get_channel_step_bounds = function() return 1, 4 end,
  }
  local slides = lifetime.new(function() return current end, model,
    function() return {transport = 2} end)
  slides.reset()
  local emitted, projected = 0, nil
  slides.push{channel = 1, trig_lock = 1, pulse_count = 0, total_pulses = 10,
    start_pulse = 0, end_step = 3, end_occurrence = 3,
    start_value = 0, last_value = 0, end_value = 100, quant = 1,
    func = function() emitted = emitted + 1 end}
  current = {channel_1_clock = {realign = true, onset_count = 20,
    project_onset_occurrence = function(_, occurrence)
      projected = occurrence
      return 24
    end}}
  slides.realign()
  luaunit.assert_equals(projected, 23)
  luaunit.assert_equals(emitted, 0)
  luaunit.assert_true(slides.is_active({number = 1}, 1))
end

-- The read-only counterpart of slides.handoff, used by the lock preview. It must
-- answer the same question without retiring an action or emitting its value,
-- because a preview may run many times before the step it is predicting.
local function handoff_fixture(transport)
  local lifetime = include("mosaic/lib/clock/slide_lifetime")
  local model = {
    get = function() return {selected_song_pattern = 1} end,
    get_channel = function() return {} end,
    get_channel_step_bounds = function() return 1, 4 end,
  }
  local emitted = {}
  local slides = lifetime.new(function() return {quantize_value = function(v) return v end} end,
    model, function() return {transport = transport} end)
  slides.reset()
  slides.push{channel = 1, trig_lock = 1, pulse_count = 0, total_pulses = 10,
    start_pulse = 0, end_step = 3, end_occurrence = 3,
    start_value = 0, last_value = 0, end_value = 100, quant = 1,
    func = function(value) emitted[#emitted + 1] = value end}
  return slides, emitted
end

function test_would_handoff_reports_a_completed_destination_lock_without_retiring_or_emitting()
  local slides, emitted = handoff_fixture(10)
  luaunit.assert_true(slides.would_handoff(1, 1, 3, 100))
  -- Asking twice gives the same answer: the predicate committed nothing.
  luaunit.assert_true(slides.would_handoff(1, 1, 3, 100))
  luaunit.assert_equals(emitted, {})
  luaunit.assert_true(slides.is_active({number = 1}, 1))
  -- The real handoff still applies afterwards, and it is the one with effects.
  luaunit.assert_true(slides.handoff(1, 1, 3, 100))
  luaunit.assert_equals(emitted, {100})
  luaunit.assert_false(slides.is_active({number = 1}, 1))
end

function test_would_handoff_rejects_a_different_step_value_slot_or_channel()
  local slides = handoff_fixture(10)
  luaunit.assert_false(slides.would_handoff(1, 1, 4, 100))
  luaunit.assert_false(slides.would_handoff(1, 1, 3, 99))
  luaunit.assert_false(slides.would_handoff(1, 2, 3, 100))
  luaunit.assert_false(slides.would_handoff(2, 1, 3, 100))
end

function test_would_handoff_rejects_a_slide_that_has_not_reached_its_destination()
  local slides = handoff_fixture(9)
  luaunit.assert_false(slides.would_handoff(1, 1, 3, 100))
  -- The real handoff agrees, and retires the unfinished action without emitting.
  luaunit.assert_false(slides.handoff(1, 1, 3, 100))
end
