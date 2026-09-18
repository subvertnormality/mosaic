-- Characterisation of the MIDI parameter decisions currently embedded in
-- step.process_params. The preview is a read-only prediction: it reports which
-- values a step would send, and may not send them, claim shared state, consume
-- RNG, start or cancel slides, or write the resend cache.
local preview = include("mosaic/lib/clock/parameter_preview")

local function cc_param(id, msb, opts)
  opts = opts or {}
  return {param_id = id, id = opts.id or ("cc" .. msb), type = "midi", cc_msb = msb,
          cc_lsb = opts.cc_lsb, cc_min_value = 0, cc_max_value = 127,
          off_value = opts.off_value, channel = opts.channel}
end

local function nrpn_param(id, msb, lsb, opts)
  opts = opts or {}
  return {param_id = id, id = opts.id or ("nrpn" .. msb .. "." .. lsb), type = "midi",
          nrpn_msb = msb, nrpn_lsb = lsb, nrpn_min_value = 0, nrpn_max_value = 16383,
          off_value = opts.off_value, channel = opts.channel}
end

-- A view supplies only reads. Anything the preview must not do is absent from it,
-- so an attempt to take a side effect fails as a missing field rather than
-- silently succeeding against a live system.
local function view(overrides)
  local v = {
    params = {},
    mute = false,
    midi_channel = 1,
    midi_device = 1,
    recording_selected = false,
    recording_dirty = function() return nil end,
    step_lock = function() return nil end,
    assigned = function() return nil end,
    is_sliding = function() return false end,
    would_handoff = function() return false end,
    next_lock = function() return nil end,
    channel_slide = function() return false end,
    step_slide = function() return false end,
    nrpn_mode = function() return "twos" end,
    resend_unchanged = true,
    last_sent = function() return nil end,
  }
  for key, value in pairs(overrides or {}) do v[key] = value end
  return v
end

local function sent(bundles)
  local out = {}
  for _, bundle in ipairs(bundles) do
    if bundle.send then out[#out + 1] = bundle end
  end
  return out
end

local function reasons(bundles)
  local out = {}
  for _, bundle in ipairs(bundles) do out[bundle.slot] = bundle.reason end
  return out
end

function test_parameter_preview_returns_no_bundles_for_a_muted_channel()
  -- process_params returns immediately on a muted channel, before claiming.
  local bundles = preview.midi_bundles(view({mute = true, params = {cc_param("p1", 74)},
                                             assigned = function() return 64 end}), 1)
  luaunit.assert_equals(bundles, {})
end

function test_parameter_preview_reports_a_locked_slot_with_its_lock_value()
  local bundles = preview.midi_bundles(view({
    params = {cc_param("p1", 74)},
    step_lock = function() return 100 end,
    assigned = function() return 20 end}), 3)
  luaunit.assert_equals(#sent(bundles), 1)
  local bundle = sent(bundles)[1]
  luaunit.assert_equals(bundle.value, 100)
  luaunit.assert_equals(bundle.kind, "lock")
  luaunit.assert_equals(bundle.midi_channel, 1)
end

function test_parameter_preview_reports_the_assigned_value_when_the_step_is_unlocked()
  local bundles = preview.midi_bundles(view({
    params = {cc_param("p1", 74)},
    assigned = function() return 20 end}), 3)
  luaunit.assert_equals(#sent(bundles), 1)
  luaunit.assert_equals(sent(bundles)[1].value, 20)
  luaunit.assert_equals(sent(bundles)[1].kind, "assigned")
end

function test_parameter_preview_suppresses_an_off_lock_and_an_off_assigned_value()
  local locked = preview.midi_bundles(view({
    params = {cc_param("p1", 74, {off_value = -1})},
    step_lock = function() return -1 end}), 1)
  luaunit.assert_equals(#sent(locked), 0)
  luaunit.assert_equals(reasons(locked), {"off"})

  local assigned = preview.midi_bundles(view({
    params = {cc_param("p1", 74, {off_value = -1})},
    assigned = function() return -1 end}), 1)
  luaunit.assert_equals(#sent(assigned), 0)
  luaunit.assert_equals(reasons(assigned), {"off"})
end

function test_parameter_preview_lets_a_locked_slot_claim_a_shared_address_from_an_assigned_slot()
  -- Two slots carry the same CC. The locked slot claims the address, so the
  -- assigned slot does not also write it.
  local bundles = preview.midi_bundles(view({
    params = {cc_param("p1", 74), cc_param("p2", 74)},
    step_lock = function(slot) return slot == 1 and 100 or nil end,
    assigned = function() return 20 end}), 1)
  luaunit.assert_equals(#sent(bundles), 1)
  luaunit.assert_equals(sent(bundles)[1].slot, 1)
  luaunit.assert_equals(reasons(bundles)[2], "claimed")
end

function test_parameter_preview_claims_a_shared_address_for_a_sliding_slot_too()
  local bundles = preview.midi_bundles(view({
    params = {cc_param("p1", 74), cc_param("p2", 74)},
    is_sliding = function(slot) return slot == 1 end,
    assigned = function() return 20 end}), 1)
  luaunit.assert_equals(reasons(bundles)[1], "sliding")
  luaunit.assert_equals(reasons(bundles)[2], "claimed")
  luaunit.assert_equals(#sent(bundles), 0)
end

function test_parameter_preview_separates_addresses_that_differ_only_by_midi_channel()
  local bundles = preview.midi_bundles(view({
    params = {cc_param("p1", 74, {channel = 2}), cc_param("p2", 74, {channel = 3})},
    step_lock = function(slot) return slot == 1 and 100 or nil end,
    assigned = function() return 20 end}), 1)
  -- Different channels are different addresses, so no claim crosses them.
  luaunit.assert_equals(#sent(bundles), 2)
end

function test_parameter_preview_marks_a_lock_that_a_running_slide_hands_off_and_sends_nothing()
  local bundles = preview.midi_bundles(view({
    params = {cc_param("p1", 74)},
    step_lock = function() return 100 end,
    would_handoff = function() return true end}), 4)
  luaunit.assert_equals(#sent(bundles), 0)
  luaunit.assert_equals(reasons(bundles), {"handoff"})
end

function test_parameter_preview_skips_a_dirty_recording_lock_only_on_the_selected_channel()
  local dirty = view({params = {cc_param("p1", 74)}, recording_selected = true,
                      recording_dirty = function() return 90 end,
                      assigned = function() return 20 end})
  luaunit.assert_equals(#sent(preview.midi_bundles(dirty, 1)), 0)
  luaunit.assert_equals(reasons(preview.midi_bundles(dirty, 1)), {"recording-dirty"})

  local unselected = view({params = {cc_param("p1", 74)}, recording_selected = false,
                           recording_dirty = function() return 90 end,
                           assigned = function() return 20 end})
  luaunit.assert_equals(#sent(preview.midi_bundles(unselected, 1)), 1)
end

function test_parameter_preview_suppresses_an_unchanged_value_when_repeat_is_off()
  local bundles = preview.midi_bundles(view({
    params = {cc_param("p1", 74)},
    assigned = function() return 20 end,
    resend_unchanged = false,
    last_sent = function() return 20 end}), 1)
  luaunit.assert_equals(#sent(bundles), 0)
  luaunit.assert_equals(reasons(bundles), {"unchanged"})
end

function test_parameter_preview_still_sends_a_changed_value_when_repeat_is_off()
  local bundles = preview.midi_bundles(view({
    params = {cc_param("p1", 74)},
    assigned = function() return 21 end,
    resend_unchanged = false,
    last_sent = function() return 20 end}), 1)
  luaunit.assert_equals(#sent(bundles), 1)
end

function test_parameter_preview_repeats_an_unchanged_value_when_repeat_is_on()
  local bundles = preview.midi_bundles(view({
    params = {cc_param("p1", 74)},
    assigned = function() return 20 end,
    resend_unchanged = true,
    last_sent = function() return 20 end}), 1)
  luaunit.assert_equals(#sent(bundles), 1)
end

function test_parameter_preview_carries_a_slide_as_a_trajectory_descriptor_without_expanding_it()
  local bundles = preview.midi_bundles(view({
    params = {cc_param("p1", 74)},
    step_lock = function() return 10 end,
    channel_slide = function() return true end,
    next_lock = function() return {step = 9, distance = 4, value = 50, should_wrap = false} end}), 5)
  local bundle = sent(bundles)[1]
  luaunit.assert_equals(bundle.value, 10)
  luaunit.assert_not_nil(bundle.slide)
  luaunit.assert_equals(bundle.slide.start_step, 5)
  luaunit.assert_equals(bundle.slide.end_step, 9)
  luaunit.assert_equals(bundle.slide.distance, 4)
  luaunit.assert_equals(bundle.slide.start_value, 10)
  luaunit.assert_equals(bundle.slide.end_value, 50)
  luaunit.assert_equals(bundle.slide.should_wrap, false)
  -- The trajectory is described, never expanded into its samples.
  luaunit.assert_nil(bundle.slide.samples)
end

function test_parameter_preview_omits_a_slide_descriptor_when_neither_slide_flag_is_set()
  local bundles = preview.midi_bundles(view({
    params = {cc_param("p1", 74)},
    step_lock = function() return 10 end,
    next_lock = function() return {step = 9, distance = 4, value = 50} end}), 5)
  luaunit.assert_nil(sent(bundles)[1].slide)
end

function test_parameter_preview_reports_the_nrpn_mode_and_address_for_an_nrpn_slot()
  local bundles = preview.midi_bundles(view({
    params = {nrpn_param("p1", 5, 6)},
    step_lock = function() return 2000 end,
    nrpn_mode = function() return "sevens" end}), 1)
  local bundle = sent(bundles)[1]
  luaunit.assert_equals(bundle.value, 2000)
  luaunit.assert_equals(bundle.nrpn_mode, "sevens")
  luaunit.assert_not_nil(bundle.address)
end

function test_parameter_preview_ignores_slots_that_step_handling_resolves_itself()
  -- Stock kinds such as trig probability are not parameter-lock sends.
  local param = cc_param("p1", 74, {id = "trig_probability"})
  local bundles = preview.midi_bundles(view({params = {param},
                                             assigned = function() return 20 end}), 1)
  luaunit.assert_equals(bundles, {})
end

function test_parameter_preview_ignores_a_slot_without_a_param_id_or_midi_address()
  local no_id = {id = "x", type = "midi", cc_msb = 74, cc_min_value = 0, cc_max_value = 127}
  local norns_slot = {param_id = "n1", id = "n1", type = "norns"}
  local bundles = preview.midi_bundles(view({params = {no_id, norns_slot},
                                             assigned = function() return 20 end}), 1)
  luaunit.assert_equals(bundles, {})
end

function test_parameter_preview_takes_no_side_effects_on_the_view_it_is_given()
  -- Every reader records its calls; the preview must only read.
  local calls = {}
  local recorded = view({
    params = {cc_param("p1", 74)},
    step_lock = function() calls[#calls + 1] = "step_lock"; return 100 end,
    would_handoff = function() calls[#calls + 1] = "would_handoff"; return false end,
    assigned = function() calls[#calls + 1] = "assigned"; return 20 end})
  preview.midi_bundles(recorded, 1)
  preview.midi_bundles(recorded, 1)
  -- Repeating the preview yields the same answer: no read committed anything.
  local first = preview.midi_bundles(recorded, 1)
  local second = preview.midi_bundles(recorded, 1)
  luaunit.assert_equals(#sent(first), #sent(second))
  luaunit.assert_equals(sent(first)[1].value, sent(second)[1].value)
end
