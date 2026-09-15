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
