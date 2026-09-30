-- Grid outcome classifier (UI03). One synthetic event per ledger branch in
-- docs/ui-reimplementation/source-inventory.json#/grid_registrations, plus
-- neighbouring cells that must not resolve the same flow.

local outcomes = include("mosaic/lib/ui_grid_outcomes")
local json = include("mosaic/lib/helpers/json")

local P = outcomes.PAGE

local function ledger()
  local handle = assert(io.open("../../docs/ui-reimplementation/source-inventory.json", "r"))
  local text = handle:read("*a")
  handle:close()
  return json.decode(text).grid_registrations
end

local function ev(page, phase, x, y, fields)
  local e = {page_before = page, page_after = page, phase = phase, x = x, y = y, pressed = {}, algorithm_before = 1}
  for k, v in pairs(fields or {}) do e[k] = v end
  return e
end

local function dual(page, hx, hy, x, y, fields)
  local e = ev(page, "dual", x, y, fields)
  e.held_x, e.held_y = hx, hy
  return e
end

-- branch id -> synthetic event meeting its guard
local CASES = {
  ["m_grid.01.channel_page"] = ev(P.song, "short", 3, 8, {page_after = P.channel}),
  ["m_grid.01.scale_page"] = ev(P.channel, "short", 4, 8, {page_after = P.scale}),
  ["m_grid.01.song_page"] = ev(P.trig, "short", 6, 8, {page_after = P.song}),
  ["m_grid.01.pattern_trig_to_note"] = ev(P.trig, "short", 5, 8, {page_after = P.note}),
  ["m_grid.01.pattern_note_to_velocity"] = ev(P.note, "short", 5, 8, {page_after = P.velocity}),
  ["m_grid.01.pattern_velocity_to_trig"] = ev(P.velocity, "short", 5, 8, {page_after = P.trig}),
  ["m_grid.01.pattern_other_to_trig"] = ev(P.scale, "short", 5, 8, {page_after = P.trig}),

  ["m_grid.02.start"] = ev(P.channel, "short", 1, 8, {playing_before = false}),
  ["m_grid.02.start_with_doctor_open"] = ev(P.trig, "short", 1, 8, {playing_before = false, algorithm_before = 5}),
  ["m_grid.02.stop"] = ev(P.channel, "short", 1, 8, {playing_before = true, stop_safety = true, shift = true}),
  ["m_grid.02.stop_blocked_by_safety"] = ev(P.channel, "short", 1, 8, {playing_before = true, stop_safety = true}),
  ["m_grid.02.record_off"] = ev(P.song, "short", 2, 8, {recording_before = true}),
  ["m_grid.02.record_on"] = ev(P.song, "short", 2, 8, {recording_before = false}),
  ["m_grid.03.long_stop_with_safety"] = ev(P.note, "long", 1, 8, {stop_safety = true}),
  ["m_grid.03.long_play_without_safety"] = ev(P.note, "long", 1, 8, {stop_safety = false}),
  ["m_grid.04.panic"] = ev(P.note, "long", 3, 8),
  ["m_grid.04.long_current_page_button"] = ev(P.velocity, "long", 5, 8),

  ["channel_edit_page.01.leave_feature_editor"] = ev(P.channel, "short", 3, 5, {feature_editor_open = true, shift = true}),
  ["channel_edit_page.01.k1_toggle_trig_mask"] = ev(P.channel, "short", 3, 5, {shift = true}),
  ["channel_edit_page.01.plain_tap_no_feature"] = ev(P.channel, "short", 3, 5),
  ["channel_edit_page.02.k1_long_clear_trig_mask"] = ev(P.channel, "long", 16, 7, {shift = true}),
  ["channel_edit_page.02.plain_long_step"] = ev(P.channel, "long", 16, 7),
  ["channel_edit_page.03.step_release_records_locks"] = ev(P.channel, "post", 1, 4),
  ["channel_edit_page.04.k1_unmute"] = ev(P.channel, "short", 4, 1, {shift = true, channel_muted_before = true}),
  ["channel_edit_page.04.k1_mute"] = ev(P.channel, "short", 4, 1, {shift = true}),
  ["channel_edit_page.04.select_channel"] = ev(P.channel, "short", 4, 1),
  ["channel_edit_page.05.long_unmute"] = ev(P.channel, "long", 9, 1, {channel_muted_before = true}),
  ["channel_edit_page.05.long_mute"] = ev(P.channel, "long", 9, 1),
  ["channel_edit_page.06.range_set"] = dual(P.channel, 2, 4, 5, 6),
  ["channel_edit_page.06.range_rejected"] = dual(P.channel, 5, 6, 2, 4),
  ["channel_edit_page.06.octave_lock_set"] = dual(P.channel, 2, 4, 9, 8),
  ["channel_edit_page.06.octave_lock_clear"] = dual(P.channel, 2, 4, 12, 8, {lock_cleared = true}),
  ["channel_edit_page.06.scale_lock_set"] = dual(P.channel, 2, 4, 7, 3),
  ["channel_edit_page.06.scale_lock_clear"] = dual(P.channel, 2, 4, 7, 3, {lock_cleared = true}),
  ["channel_edit_page.06.k1_dual_mute_toggle"] = dual(P.channel, 2, 1, 7, 1, {shift = true}),
  ["channel_edit_page.06.two_channels_no_k1"] = dual(P.channel, 2, 1, 7, 1),
  ["channel_edit_page.07.pattern_added"] = ev(P.channel, "short", 16, 2),
  ["channel_edit_page.07.pattern_removed"] = ev(P.channel, "short", 16, 2, {pattern_assigned_before = true}),
  ["channel_edit_page.08.trig_merge_skip"] = ev(P.channel, "short", 14, 8, {merge_state_before = 3}),
  ["channel_edit_page.08.trig_merge_only"] = ev(P.channel, "short", 14, 8, {merge_state_before = 1}),
  ["channel_edit_page.08.trig_merge_all"] = ev(P.channel, "short", 14, 8, {merge_state_before = 2}),
  ["channel_edit_page.09.note_merge_average"] = ev(P.channel, "short", 15, 8, {merge_state_before = 4}),
  ["channel_edit_page.09.note_merge_up"] = ev(P.channel, "short", 15, 8, {merge_state_before = 1}),
  ["channel_edit_page.09.note_merge_down"] = ev(P.channel, "short", 15, 8, {merge_state_before = 2}),
  ["channel_edit_page.09.note_merge_pattern_wraps_to_average"] = ev(P.channel, "short", 15, 8, {merge_state_before = 3}),
  ["channel_edit_page.10.velocity_merge_average"] = ev(P.channel, "short", 16, 8, {merge_state_before = 4}),
  ["channel_edit_page.10.velocity_merge_up"] = ev(P.channel, "short", 16, 8, {merge_state_before = 1}),
  ["channel_edit_page.10.velocity_merge_down"] = ev(P.channel, "short", 16, 8, {merge_state_before = 2}),
  ["channel_edit_page.10.velocity_merge_pattern_wraps_to_average"] = ev(P.channel, "short", 16, 8, {merge_state_before = 3}),
  ["channel_edit_page.11.length_merge_average"] = ev(P.channel, "short", 16, 8, {shift = true, merge_state_before = 4}),
  ["channel_edit_page.11.length_merge_up"] = ev(P.channel, "short", 16, 8, {shift = true, merge_state_before = 1}),
  ["channel_edit_page.11.length_merge_down"] = ev(P.channel, "short", 16, 8, {shift = true, merge_state_before = 2}),
  ["channel_edit_page.11.length_merge_pattern_wraps_to_average"] = ev(P.channel, "short", 16, 8, {shift = true, merge_state_before = 3}),
  ["channel_edit_page.12.trig_merge_release_hides_gesture"] = ev(P.channel, "post", 14, 8),
  ["channel_edit_page.12.note_merge_release_hides_gesture"] = ev(P.channel, "post", 15, 8),
  ["channel_edit_page.12.velocity_length_merge_release_hides_gesture"] = ev(P.channel, "post", 16, 8, {shift = true}),
  ["channel_edit_page.12.release_after_pattern_priority"] = ev(P.channel, "post", 15, 8, {gesture_dual_flow = "G19"}),
  ["channel_edit_page.13.channel_octave"] = ev(P.channel, "short", 8, 8),
  ["channel_edit_page.14.note_pattern_priority"] = dual(P.channel, 15, 8, 2, 2),
  ["channel_edit_page.14.velocity_pattern_priority"] = dual(P.channel, 16, 8, 3, 2),
  ["channel_edit_page.14.length_pattern_priority"] = dual(P.channel, 16, 8, 3, 2, {shift = true}),
  ["channel_edit_page.14.trig_merge_plus_pattern_inert"] = dual(P.channel, 14, 8, 3, 2),
  ["channel_edit_page.15.step_hold_shows_locks"] = ev(P.channel, "pre", 5, 7, {pressed = {{5, 7}}}),

  ["note_edit_page.01.k1_row1_select_pattern"] = ev(P.note, "short", 7, 1, {shift = true}),
  ["note_edit_page.01.set_note"] = ev(P.note, "short", 7, 1),
  ["note_edit_page.01.k1_set_note_all_banks"] = ev(P.note, "short", 7, 3, {shift = true}),
  ["note_edit_page.02.long_row1_select_pattern"] = ev(P.note, "long", 7, 1),
  ["note_edit_page.03.bank_1"] = ev(P.note, "short", 9, 8),
  ["note_edit_page.04.bank_2"] = ev(P.note, "short", 10, 8),
  ["note_edit_page.05.bank_3"] = ev(P.note, "short", 11, 8),
  ["note_edit_page.06.bank_4"] = ev(P.note, "short", 12, 8),
  ["note_edit_page.07.note_view_down"] = ev(P.note, "short", 14, 8),
  ["note_edit_page.07.note_view_down_at_limit"] = ev(P.note, "short", 14, 8, {view_at_limit = true}),
  ["note_edit_page.08.note_view_centre"] = ev(P.note, "short", 15, 8, {view_at_limit = true}),
  ["note_edit_page.09.note_view_up"] = ev(P.note, "short", 16, 8),
  ["note_edit_page.09.note_view_up_at_limit"] = ev(P.note, "short", 16, 8, {view_at_limit = true}),
  ["note_edit_page.10.long_row1_select_pattern"] = ev(P.note, "long", 2, 1),
  ["note_edit_page.10.long_view_top"] = ev(P.note, "long", 14, 8),
  ["note_edit_page.10.long_view_root"] = ev(P.note, "long", 15, 8),
  ["note_edit_page.10.long_view_bottom"] = ev(P.note, "long", 16, 8),

  ["scale_edit_page.01.range_set"] = dual(P.scale, 1, 4, 1, 5),
  ["scale_edit_page.01.range_rejected"] = dual(P.scale, 1, 5, 1, 4),
  ["scale_edit_page.01.scale_lock_set"] = dual(P.scale, 1, 5, 9, 3),
  ["scale_edit_page.01.scale_lock_clear"] = dual(P.scale, 1, 5, 9, 3, {lock_cleared = true}),
  ["scale_edit_page.01.transpose_lock_set"] = dual(P.scale, 1, 5, 16, 8),
  ["scale_edit_page.01.transpose_lock_clear"] = dual(P.scale, 1, 5, 8, 8, {lock_cleared = true}),
  ["scale_edit_page.02.k1_select_slot_only"] = ev(P.scale, "short", 2, 3, {shift = true}),
  ["scale_edit_page.02.set_global_scale"] = ev(P.scale, "short", 2, 3),
  ["scale_edit_page.02.global_scale_off"] = ev(P.scale, "short", 2, 3, {scale_slot_is_global = true}),
  ["scale_edit_page.03.long_clear_selected"] = ev(P.scale, "long", 2, 3, {scale_slot_selected = true}),
  ["scale_edit_page.03.long_select_slot"] = ev(P.scale, "long", 2, 3),
  ["scale_edit_page.04.step_hold_shows_locks"] = ev(P.scale, "pre", 2, 6),
  ["scale_edit_page.05.step_release_restores_faders"] = ev(P.scale, "post", 2, 6),
  ["scale_edit_page.06.transpose"] = ev(P.scale, "short", 12, 8),

  ["song_edit_page.01.queue_slot_while_playing"] = ev(P.song, "short", 1, 6, {playing = true}),
  ["song_edit_page.01.select_slot_stopped"] = ev(P.song, "short", 1, 6),
  ["song_edit_page.01.select_slot_stopped_elektron_pc"] = ev(P.song, "short", 1, 6, {elektron_program_changes = true}),
  ["song_edit_page.02.global_length_queued"] = ev(P.song, "short", 8, 7, {playing = true}),
  ["song_edit_page.02.global_length_immediate"] = ev(P.song, "short", 1, 7),
  ["song_edit_page.03.slot_copy_press_order"] = dual(P.song, 1, 1, 16, 6),
  ["song_edit_page.03.non_slot_pair_refresh_only"] = dual(P.song, 1, 1, 1, 7),

  ["trigger_edit_page.01.select_pattern"] = ev(P.trig, "short", 3, 1),
  ["trigger_edit_page.01.select_pattern_discards_stale_doctor_preview"] = ev(P.trig, "short", 3, 1, {algorithm_before = 5, paint_armed = true}),
  ["trigger_edit_page.02.toggle_trig"] = ev(P.trig, "short", 3, 4, {algorithm_before = 5}),
  ["trigger_edit_page.03.pattern1_fill_euclid"] = ev(P.trig, "short", 10, 2, {algorithm_before = 3}),
  ["trigger_edit_page.03.pattern1"] = ev(P.trig, "short", 10, 2, {algorithm_before = 4}),
  ["trigger_edit_page.03.pattern1_inert_doctor"] = ev(P.trig, "short", 10, 2, {algorithm_before = 5}),
  ["trigger_edit_page.04.pattern2_length_euclid"] = ev(P.trig, "short", 1, 3, {algorithm_before = 3}),
  ["trigger_edit_page.04.pattern2"] = ev(P.trig, "short", 1, 3, {algorithm_before = 2}),
  ["trigger_edit_page.04.pattern2_inert_doctor"] = ev(P.trig, "short", 1, 3, {algorithm_before = 5}),
  ["trigger_edit_page.05.select_algorithm"] = ev(P.trig, "short", 13, 2, {algorithm_before = 1}),
  ["trigger_edit_page.05.enter_doctor"] = ev(P.trig, "short", 16, 2, {algorithm_before = 4}),
  ["trigger_edit_page.05.leave_doctor"] = ev(P.trig, "short", 12, 2, {algorithm_before = 5}),
  ["trigger_edit_page.06.select_bank_mask"] = ev(P.trig, "short", 16, 3, {algorithm_before = 2}),
  ["trigger_edit_page.06.bank_mask_inert"] = ev(P.trig, "short", 12, 3, {algorithm_before = 3}),
  ["trigger_edit_page.07.record_start_capture"] = ev(P.trig, "pre", 1, 2, {algorithm_before = 5, doctor_state = "EMPTY"}),
  ["trigger_edit_page.07.record_finish"] = ev(P.trig, "pre", 1, 2, {algorithm_before = 5, doctor_state = "CAPTURING", doctor_finish_eligible = true}),
  ["trigger_edit_page.07.record_cancel_prompt"] = ev(P.trig, "pre", 1, 2, {algorithm_before = 5, doctor_state = "CAPTURING"}),
  ["trigger_edit_page.07.record_blocked_playing"] = ev(P.trig, "pre", 1, 2, {algorithm_before = 5, playing_before = true, playing = true}),
  ["trigger_edit_page.07.record_blocked_setup"] = ev(P.trig, "pre", 1, 2, {algorithm_before = 5, doctor_setup_open = true}),
  ["trigger_edit_page.08.record_release_consumed"] = ev(P.trig, "post", 1, 2, {algorithm_before = 5, claimed = true}),
  ["trigger_edit_page.09.select_lane"] = ev(P.trig, "short", 5, 3, {algorithm_before = 5, lane_hit = true}),
  ["trigger_edit_page.09.select_lane_repreviews_paint"] = ev(P.trig, "short", 5, 3, {algorithm_before = 5, lane_hit = true, paint_armed = true}),
  ["trigger_edit_page.09.non_lane_cell_inert"] = ev(P.trig, "short", 8, 2, {algorithm_before = 5}),
  ["trigger_edit_page.10.arm_paint"] = ev(P.trig, "short", 16, 8, {algorithm_before = 1}),
  ["trigger_edit_page.10.commit_paint"] = ev(P.trig, "short", 16, 8, {algorithm_before = 1, paint_armed = true}),
  ["trigger_edit_page.10.doctor_arm_paint"] = ev(P.trig, "short", 16, 8, {algorithm_before = 5, paint_armed_after = true}),
  ["trigger_edit_page.10.doctor_arm_paint_unavailable"] = ev(P.trig, "short", 16, 8, {algorithm_before = 5, paint_armed_after = false}),
  ["trigger_edit_page.10.doctor_commit_paint"] = ev(P.trig, "short", 16, 8, {algorithm_before = 5, paint_armed = true, paint_armed_after = false}),
  ["trigger_edit_page.10.doctor_commit_failed"] = ev(P.trig, "short", 16, 8, {algorithm_before = 5, paint_armed = true, paint_armed_after = true}),
  ["trigger_edit_page.11.cancel_paint"] = ev(P.trig, "short", 14, 8, {algorithm_before = 2, paint_armed = true}),
  ["trigger_edit_page.11.doctor_cancel_paint"] = ev(P.trig, "short", 14, 8, {algorithm_before = 5, paint_armed = true}),
  ["trigger_edit_page.11.cancel_idle"] = ev(P.trig, "short", 14, 8, {algorithm_before = 5}),
  ["trigger_edit_page.12.doctor_step_left"] = ev(P.trig, "short", 10, 8, {algorithm_before = 5}),
  ["trigger_edit_page.12.shift_left"] = ev(P.trig, "short", 10, 8, {paint_armed = true}),
  ["trigger_edit_page.12.left_idle"] = ev(P.trig, "short", 10, 8),
  ["trigger_edit_page.13.doctor_phrase_start"] = ev(P.trig, "short", 11, 8, {algorithm_before = 5, paint_armed = true}),
  ["trigger_edit_page.13.shift_reset"] = ev(P.trig, "short", 11, 8, {paint_armed = true}),
  ["trigger_edit_page.13.centre_idle"] = ev(P.trig, "short", 11, 8),
  ["trigger_edit_page.14.doctor_step_right"] = ev(P.trig, "short", 12, 8, {algorithm_before = 5}),
  ["trigger_edit_page.14.shift_right"] = ev(P.trig, "short", 12, 8, {algorithm_before = 3, paint_armed = true}),
  ["trigger_edit_page.14.right_idle"] = ev(P.trig, "short", 12, 8, {algorithm_before = 3}),
  ["trigger_edit_page.15.length_forward"] = dual(P.trig, 1, 4, 5, 4, {step_has_trig = true}),
  ["trigger_edit_page.15.length_wraps"] = dual(P.trig, 5, 7, 1, 4, {step_has_trig = true}),
  ["trigger_edit_page.15.held_step_without_trig"] = dual(P.trig, 1, 4, 5, 4),
  ["trigger_edit_page.16.doctor_previous_phrase"] = ev(P.trig, "long", 10, 8, {algorithm_before = 5}),
  ["trigger_edit_page.16.doctor_next_phrase"] = ev(P.trig, "long", 12, 8, {algorithm_before = 5}),
  ["trigger_edit_page.16.long_shift_button_non_doctor"] = ev(P.trig, "long", 12, 8, {algorithm_before = 4}),
  ["trigger_edit_page.17.reset_length"] = ev(P.trig, "long", 9, 6, {step_has_trig = true}),
  ["trigger_edit_page.17.reset_length_no_trig"] = ev(P.trig, "long", 9, 6),

  ["velocity_edit_page.01.k1_row1_select_pattern"] = ev(P.velocity, "short", 16, 1, {shift = true}),
  ["velocity_edit_page.01.set_velocity"] = ev(P.velocity, "short", 16, 1),
  ["velocity_edit_page.01.k1_set_velocity_all_banks"] = ev(P.velocity, "short", 16, 7, {shift = true}),
  ["velocity_edit_page.02.long_row1_select_pattern"] = ev(P.velocity, "long", 16, 1),
  ["velocity_edit_page.03.bank_1"] = ev(P.velocity, "short", 9, 8),
  ["velocity_edit_page.04.bank_2"] = ev(P.velocity, "short", 10, 8),
  ["velocity_edit_page.05.bank_3"] = ev(P.velocity, "short", 11, 8),
  ["velocity_edit_page.06.bank_4"] = ev(P.velocity, "short", 12, 8),
  ["velocity_edit_page.07.velocity_view_down"] = ev(P.velocity, "short", 16, 8),
  ["velocity_edit_page.07.velocity_view_down_at_limit"] = ev(P.velocity, "short", 16, 8, {view_at_limit = true}),
  ["velocity_edit_page.08.long_view_high"] = ev(P.velocity, "long", 16, 8),
  ["velocity_edit_page.08.long_view_low"] = ev(P.velocity, "long", 15, 8),
  ["velocity_edit_page.09.velocity_view_up"] = ev(P.velocity, "short", 15, 8),
  ["velocity_edit_page.09.velocity_view_up_at_limit"] = ev(P.velocity, "short", 15, 8, {view_at_limit = true}),
}

local function contains(list, value)
  for _, v in ipairs(list or {}) do if v == value then return true end end
  return false
end

local function each_ledger_branch(fn_)
  for _, registration in ipairs(ledger()) do
    for _, branch in ipairs(registration.branches) do fn_(branch, registration) end
  end
end

function test_ui_grid_outcomes_page_numbers_match_pages_module()
  luaunit.assert_equals(outcomes.PAGE.channel, pages.pages.channel_edit_page)
  luaunit.assert_equals(outcomes.PAGE.scale, pages.pages.scale_edit_page)
  luaunit.assert_equals(outcomes.PAGE.trig, pages.pages.trigger_edit_page)
  luaunit.assert_equals(outcomes.PAGE.note, pages.pages.note_edit_page)
  luaunit.assert_equals(outcomes.PAGE.velocity, pages.pages.velocity_edit_page)
  luaunit.assert_equals(outcomes.PAGE.song, pages.pages.song_edit_page)
end

function test_ui_grid_outcomes_ledger_has_64_registrations_and_164_branches()
  local registrations, branches = 0, 0
  for _, registration in ipairs(ledger()) do
    registrations = registrations + 1
    branches = branches + #registration.branches
  end
  luaunit.assert_equals(registrations, 64)
  luaunit.assert_equals(branches, 164)
end

function test_ui_grid_outcomes_every_flow_branch_is_exported_with_its_flow()
  local seen = 0
  each_ledger_branch(function(branch)
    if branch.outcome == "retain_without_navigation" then
      luaunit.assert_nil(outcomes.branches[branch.id], branch.id)
      luaunit.assert_true(outcomes.retained[branch.id] == true, branch.id)
    else
      seen = seen + 1
      luaunit.assert_equals(outcomes.branches[branch.id], branch.outcome, branch.id)
    end
  end)
  local exported = 0
  for _ in pairs(outcomes.branches) do exported = exported + 1 end
  luaunit.assert_equals(exported, seen)
end

-- One assertion per ledger branch: its synthetic event classifies to its flow
-- (nil for retain_without_navigation) and names the branch.
function test_ui_grid_outcomes_every_ledger_branch_classifies()
  local count = 0
  each_ledger_branch(function(branch)
    local event = CASES[branch.id]
    luaunit.assert_not_nil(event, "no case for " .. branch.id)
    local flow, extra = outcomes.classify(event)
    local expected = branch.outcome ~= "retain_without_navigation" and branch.outcome or nil
    luaunit.assert_equals(flow, expected, branch.id)
    luaunit.assert_not_nil(extra, branch.id)
    luaunit.assert_true(contains(extra.branches, branch.id), branch.id .. " not among " .. table.concat(extra.branches or {}, ","))
    -- Two Note-page long registrations both fire on row 1; the first is primary.
    if expected and #extra.branches == 1 then luaunit.assert_equals(extra.branch, branch.id) end
    count = count + 1
  end)
  luaunit.assert_equals(count, 164)
end

function test_ui_grid_outcomes_classify_is_pure()
  local event = ev(P.channel, "short", 4, 1, {pressed = {{4, 1}}})
  local before = json.encode(event)
  outcomes.classify(event)
  outcomes.classify(event)
  luaunit.assert_equals(json.encode(event), before)
end

function test_ui_grid_outcomes_payloads()
  local _, extra = outcomes.classify(ev(P.channel, "short", 4, 1))
  luaunit.assert_equals(extra.channel, 4)
  _, extra = outcomes.classify(ev(P.trig, "short", 5, 8, {page_after = P.note}))
  luaunit.assert_equals(extra.page, P.note)
  _, extra = outcomes.classify(ev(P.channel, "pre", 1, 5, {pressed = {{3, 4}, {1, 5}, {5, 8}}}))
  luaunit.assert_equals(extra.steps, {3, 17})
  _, extra = outcomes.classify(ev(P.song, "short", 2, 3))
  luaunit.assert_equals(extra.slot, 34)
  _, extra = outcomes.classify(ev(P.trig, "short", 14, 2, {algorithm_before = 1}))
  luaunit.assert_equals(extra.algorithm, 3)
  local flow
  flow, extra = outcomes.classify(ev(P.note, "long", 5, 1))
  luaunit.assert_equals(flow, "G20")
  luaunit.assert_equals(#extra.branches, 2)
end

function test_ui_grid_outcomes_menu_neighbours()
  -- (7,8) and (2,8) are not page buttons; (1,8)/(2,8) are never page flows.
  luaunit.assert_nil((outcomes.classify(ev(P.channel, "short", 7, 8))))
  luaunit.assert_equals((outcomes.classify(ev(P.channel, "short", 2, 8))), "G38")
  -- Page buttons do not resolve on long press or dual.
  luaunit.assert_equals((outcomes.classify(ev(P.channel, "long", 4, 8))), "G38")
  luaunit.assert_nil((outcomes.classify(ev(P.channel, "long", 2, 8))))
  luaunit.assert_nil((outcomes.classify(dual(P.channel, 3, 8, 4, 8))))
  -- Long on the current page button (Note maps to 5) is not panic.
  luaunit.assert_nil((outcomes.classify(ev(P.note, "long", 5, 8))))
  luaunit.assert_nil((outcomes.classify(ev(P.channel, "long", 3, 8))))
  -- Pre/post of menu cells resolve nothing.
  luaunit.assert_nil((outcomes.classify(ev(P.channel, "pre", 1, 8))))
  luaunit.assert_nil((outcomes.classify(ev(P.channel, "post", 3, 8))))
  -- Start without Doctor: Trig page with another algorithm, or another page with algorithm 5.
  luaunit.assert_equals((outcomes.classify(ev(P.trig, "short", 1, 8, {algorithm_before = 4}))), "G38")
  luaunit.assert_equals((outcomes.classify(ev(P.note, "short", 1, 8, {algorithm_before = 5}))), "G38")
  -- Stop without safety needs no K1.
  luaunit.assert_equals((outcomes.classify(ev(P.channel, "short", 1, 8, {playing_before = true}))), "G38")
end

function test_ui_grid_outcomes_channel_neighbours()
  luaunit.assert_nil((outcomes.classify(ev(P.channel, "short", 5, 3))))  -- row 3 alone
  luaunit.assert_nil((outcomes.classify(ev(P.channel, "short", 13, 8)))) -- between octave and merge
  luaunit.assert_equals((outcomes.classify(ev(P.channel, "short", 12, 8))), "G14")
  luaunit.assert_nil((outcomes.classify(ev(P.channel, "short", 7, 8))))
  luaunit.assert_nil((outcomes.classify(ev(P.channel, "long", 5, 2))))
  luaunit.assert_nil((outcomes.classify(ev(P.channel, "long", 14, 8))))
  luaunit.assert_nil((outcomes.classify(ev(P.channel, "pre", 1, 3))))
  luaunit.assert_nil((outcomes.classify(ev(P.channel, "post", 1, 1))))
  luaunit.assert_nil((outcomes.classify(ev(P.channel, "post", 13, 8))))
  luaunit.assert_nil((outcomes.classify(dual(P.channel, 2, 4, 13, 8)))) -- past the octave fader
  luaunit.assert_nil((outcomes.classify(dual(P.channel, 2, 4, 3, 2))))  -- step + pattern row
  luaunit.assert_nil((outcomes.classify(dual(P.channel, 2, 1, 3, 4))))  -- channel then step
  luaunit.assert_nil((outcomes.classify(dual(P.channel, 15, 8, 3, 1))))
  -- Channel cells mean nothing on another page.
  luaunit.assert_nil((outcomes.classify(ev(P.song, "short", 14, 8))))
end

function test_ui_grid_outcomes_scale_and_song_neighbours()
  luaunit.assert_nil((outcomes.classify(ev(P.scale, "short", 7, 8))))
  luaunit.assert_nil((outcomes.classify(ev(P.scale, "short", 3, 4))))
  luaunit.assert_nil((outcomes.classify(ev(P.scale, "short", 3, 2))))
  luaunit.assert_nil((outcomes.classify(ev(P.scale, "long", 3, 4))))
  luaunit.assert_nil((outcomes.classify(ev(P.scale, "pre", 3, 3))))
  luaunit.assert_nil((outcomes.classify(dual(P.scale, 1, 4, 7, 8))))
  luaunit.assert_nil((outcomes.classify(dual(P.scale, 1, 4, 7, 2))))
  luaunit.assert_nil((outcomes.classify(ev(P.song, "short", 9, 7))))
  luaunit.assert_nil((outcomes.classify(ev(P.song, "short", 9, 8))))
  luaunit.assert_nil((outcomes.classify(ev(P.song, "long", 1, 1))))
  luaunit.assert_nil((outcomes.classify(dual(P.song, 1, 7, 1, 1))))
end

function test_ui_grid_outcomes_note_and_velocity_neighbours()
  luaunit.assert_nil((outcomes.classify(ev(P.note, "short", 13, 8))))
  luaunit.assert_nil((outcomes.classify(ev(P.note, "short", 8, 8))))
  luaunit.assert_nil((outcomes.classify(ev(P.note, "long", 3, 2))))
  luaunit.assert_nil((outcomes.classify(ev(P.note, "long", 9, 8))))
  luaunit.assert_nil((outcomes.classify(dual(P.note, 1, 2, 3, 4))))
  luaunit.assert_nil((outcomes.classify(ev(P.velocity, "short", 14, 8))))
  luaunit.assert_nil((outcomes.classify(ev(P.velocity, "long", 14, 8))))
  luaunit.assert_nil((outcomes.classify(ev(P.velocity, "long", 3, 5))))
  luaunit.assert_equals((outcomes.classify(ev(P.velocity, "short", 3, 5))), "G30")
  luaunit.assert_equals((outcomes.classify(ev(P.note, "short", 3, 7))), "G28")
end

function test_ui_grid_outcomes_trig_neighbours()
  luaunit.assert_nil((outcomes.classify(ev(P.trig, "short", 11, 2))))
  luaunit.assert_nil((outcomes.classify(ev(P.trig, "short", 11, 3))))
  luaunit.assert_nil((outcomes.classify(ev(P.trig, "short", 16, 3, {algorithm_before = 4})))) -- 4-cell bank mask
  luaunit.assert_equals((outcomes.classify(ev(P.trig, "short", 15, 3, {algorithm_before = 4}))), "G25")
  luaunit.assert_nil((outcomes.classify(ev(P.trig, "short", 16, 2, {algorithm_before = 5})))) -- 5 -> 5
  luaunit.assert_nil((outcomes.classify(ev(P.trig, "short", 13, 8))))
  luaunit.assert_nil((outcomes.classify(ev(P.trig, "short", 15, 8, {paint_armed = true}))))
  luaunit.assert_nil((outcomes.classify(ev(P.trig, "short", 3, 2, {algorithm_before = 5}))))    -- no lane there
  luaunit.assert_equals((outcomes.classify(ev(P.trig, "short", 14, 2, {algorithm_before = 5}))), "G23") -- fader, not lane
  luaunit.assert_nil((outcomes.classify(ev(P.trig, "long", 11, 8, {algorithm_before = 5}))))
  luaunit.assert_nil((outcomes.classify(ev(P.trig, "long", 3, 1))))
  luaunit.assert_nil((outcomes.classify(ev(P.trig, "pre", 1, 2, {algorithm_before = 4}))))
  luaunit.assert_nil((outcomes.classify(ev(P.trig, "pre", 2, 2, {algorithm_before = 5}))))
  luaunit.assert_nil((outcomes.classify(ev(P.trig, "post", 1, 2, {algorithm_before = 3}))))
  luaunit.assert_nil((outcomes.classify(ev(P.trig, "pre", 3, 5))))
  luaunit.assert_nil((outcomes.classify(dual(P.trig, 1, 3, 5, 4, {step_has_trig = true}))))
  luaunit.assert_nil((outcomes.classify(dual(P.trig, 1, 4, 16, 8, {step_has_trig = true}))))
  -- Lane select only in algorithm 5; outside it the cell is the generator fader.
  luaunit.assert_equals((outcomes.classify(ev(P.trig, "short", 5, 3, {algorithm_before = 2, lane_hit = true}))), "G24")
  -- The Trig record cell (1,2) is claimed in pre only in algorithm 5.
  luaunit.assert_equals((outcomes.classify(ev(P.trig, "short", 1, 2, {algorithm_before = 1}))), "G24")
end

function test_ui_grid_outcomes_rejects_incomplete_events()
  luaunit.assert_nil((outcomes.classify(nil)))
  luaunit.assert_nil((outcomes.classify({phase = "short", page_before = P.channel})))
  luaunit.assert_nil((outcomes.classify(ev(99, "short", 4, 1))))
  luaunit.assert_nil((outcomes.classify(ev(P.channel, "bogus", 4, 1))))
end
