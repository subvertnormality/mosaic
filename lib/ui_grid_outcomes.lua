-- Grid outcome classifier (UI03, "Router and grid follow").
--
-- Maps one completed grid handler phase to the spec flow it resolved
-- (docs/ui-reimplementation/spec.json#/flows G01..G46), following the branch
-- ledger in docs/ui-reimplementation/source-inventory.json#/grid_registrations.
--
-- This module is pure. It never runs, re-runs or synthesises a grid handler and
-- never mutates anything: it classifies from the input and from owner state the
-- integrator captured around the ONE original handler call (lib/m_grid.lua).
--
--   local outcomes = include("mosaic/lib/ui_grid_outcomes")
--   local flow_id, extra = outcomes.classify(event)
--
-- flow_id is a flow id string ("G21"), or nil when the handler resolved a
-- retain_without_navigation branch or no ledger branch at all. extra is a table
-- whenever a ledger branch matched (also for retain branches):
--   extra.branch    primary ledger branch id
--   extra.branches  every ledger branch that fired for this phase (a phase runs
--                   several registrations, e.g. two Note-page long handlers on row 1)
--   plus flow payload: page, channel, channels, pattern, step, steps, slot,
--   slots, algorithm, from_step, to_step.
--
-- Event fields. Required for the flow (a missing field reads as false/nil):
--   phase            "pre" | "short" | "dual" | "long" | "post"
--   page_before      program page number before the handler (pages.pages.*)
--   page_after       program page number after the handler (payload of G01..G04)
--   x, y             the key; for dual the key released second (whose release fired dual)
--   held_x, held_y   dual only: the key held first (m_grid passes pressed_keys[1])
--   shift            is_key1_down during the handler
--   pressed          list of {x, y} still pressed after the handler (held scope for G08)
--   algorithm_before trigger_edit_page.get_algorithm() before the handler
--   playing_before   m_clock.is_playing() before the handler ((1,8) start vs stop)
--   playing          m_clock.is_playing() after the handler (Song queue vs immediate)
--   claimed          pre claimed the key (informational; copied into extra)
--   stop_safety      params:get("stop_safety") == 2 before the handler
--   feature_editor_open  Channel page: Merge Shape or Harmony channel page selected
--                    before the handler (channel_edit_navigation.leave_feature_editor_for_grid
--                    guard). Decides G44 vs G09 on a step tap.
--   paint_armed      Trig page: Paint button (16,8) state == 2 before the handler.
--                    The shift/centre/cancel buttons are set to 2 exactly when Paint
--                    arms and back to 1 when it commits/cancels, so this also stands
--                    for their state.
--   lane_hit         Trig page, algorithm 5: rhythm_doctor:lane_at(x, y) ~= nil before
--   step_has_trig    Trig page: trig_values[step] == 1 before the handler, for the
--                    dual's HELD step or the long press's step
--   view_at_limit    Note (14,8)/(16,8), Velocity (15,8)/(16,8): the fade button was
--                    already at its limit, so fade_button:press returned false and no
--                    offset changed. The fade buttons are page locals: the owner
--                    needs a read-only getter for the integrator to capture this.
--   gesture_dual_flow  flow id the integrator classified for a dual earlier in this
--                    same gesture (nil if none): a merge-button post after a row-2
--                    priority dual is G19, not G16/G17/G18.
--
-- Optional, sibling-branch detail only. They choose extra.branch among siblings that
-- share the SAME flow and never change flow_id:
--   recording_before        params:get("record") == 2 before (record_off vs record_on)
--   channel_muted_before    row-1 channel (x) was muted before (mute vs unmute)
--   pattern_assigned_before row-2 pattern x was in selected_patterns before
--   merge_state_before      merge button state before the press (1..3 trig, 1..4 others)
--   lock_cleared            a dual lock gesture cleared an existing lock
--   scale_slot_is_global    Scale row-3 slot value equalled default_scale before
--   scale_slot_selected     Scale row-3 slot x was selected_scale before (long press)
--   elektron_program_changes params:get("elektron_program_changes") == 2
--   paint_armed_after       Trig Paint state == 2 after (doctor preview refused /
--                           commit failed)
--   doctor_setup_open, doctor_state, doctor_finish_eligible  Rhythm Doctor adapter
--                           state before the (1,2) record pre (Adapter:record_pressed)

local outcomes = {}

local PAGE = {channel = 2, scale = 3, trig = 4, note = 5, velocity = 6, song = 7}
outcomes.PAGE = PAGE

-- Every ledger branch id -> its flow id, or false for retain_without_navigation.
local LEDGER = {
  ["m_grid.01.channel_page"] = "G01",
  ["m_grid.01.scale_page"] = "G02",
  ["m_grid.01.song_page"] = "G04",
  ["m_grid.01.pattern_trig_to_note"] = "G03",
  ["m_grid.01.pattern_note_to_velocity"] = "G03",
  ["m_grid.01.pattern_velocity_to_trig"] = "G03",
  ["m_grid.01.pattern_other_to_trig"] = "G03",
  ["m_grid.02.start"] = "G38",
  ["m_grid.02.start_with_doctor_open"] = "G43",
  ["m_grid.02.stop"] = "G38",
  ["m_grid.02.stop_blocked_by_safety"] = false,
  ["m_grid.02.record_off"] = "G38",
  ["m_grid.02.record_on"] = "G38",
  ["m_grid.03.long_stop_with_safety"] = "G38",
  ["m_grid.03.long_play_without_safety"] = false,
  ["m_grid.04.panic"] = "G38",
  ["m_grid.04.long_current_page_button"] = false,
  ["channel_edit_page.01.leave_feature_editor"] = "G44",
  ["channel_edit_page.01.k1_toggle_trig_mask"] = "G09",
  ["channel_edit_page.01.plain_tap_no_feature"] = false,
  ["channel_edit_page.02.k1_long_clear_trig_mask"] = "G09",
  ["channel_edit_page.02.plain_long_step"] = false,
  ["channel_edit_page.03.step_release_records_locks"] = "G08",
  ["channel_edit_page.04.k1_unmute"] = "G06",
  ["channel_edit_page.04.k1_mute"] = "G06",
  ["channel_edit_page.04.select_channel"] = "G05",
  ["channel_edit_page.05.long_unmute"] = "G06",
  ["channel_edit_page.05.long_mute"] = "G06",
  ["channel_edit_page.06.range_set"] = "G11",
  ["channel_edit_page.06.range_rejected"] = "G11",
  ["channel_edit_page.06.octave_lock_set"] = "G15",
  ["channel_edit_page.06.octave_lock_clear"] = "G15",
  ["channel_edit_page.06.scale_lock_set"] = "G13",
  ["channel_edit_page.06.scale_lock_clear"] = "G13",
  ["channel_edit_page.06.k1_dual_mute_toggle"] = "G06",
  ["channel_edit_page.06.two_channels_no_k1"] = false,
  ["channel_edit_page.07.pattern_added"] = "G07",
  ["channel_edit_page.07.pattern_removed"] = "G07",
  ["channel_edit_page.08.trig_merge_skip"] = "G16",
  ["channel_edit_page.08.trig_merge_only"] = "G16",
  ["channel_edit_page.08.trig_merge_all"] = "G16",
  ["channel_edit_page.09.note_merge_average"] = "G17",
  ["channel_edit_page.09.note_merge_up"] = "G17",
  ["channel_edit_page.09.note_merge_down"] = "G17",
  ["channel_edit_page.09.note_merge_pattern_wraps_to_average"] = "G17",
  ["channel_edit_page.10.velocity_merge_average"] = "G18",
  ["channel_edit_page.10.velocity_merge_up"] = "G18",
  ["channel_edit_page.10.velocity_merge_down"] = "G18",
  ["channel_edit_page.10.velocity_merge_pattern_wraps_to_average"] = "G18",
  ["channel_edit_page.11.length_merge_average"] = "G18",
  ["channel_edit_page.11.length_merge_up"] = "G18",
  ["channel_edit_page.11.length_merge_down"] = "G18",
  ["channel_edit_page.11.length_merge_pattern_wraps_to_average"] = "G18",
  ["channel_edit_page.12.trig_merge_release_hides_gesture"] = "G16",
  ["channel_edit_page.12.note_merge_release_hides_gesture"] = "G17",
  ["channel_edit_page.12.velocity_length_merge_release_hides_gesture"] = "G18",
  ["channel_edit_page.12.release_after_pattern_priority"] = "G19",
  ["channel_edit_page.13.channel_octave"] = "G14",
  ["channel_edit_page.14.note_pattern_priority"] = "G19",
  ["channel_edit_page.14.velocity_pattern_priority"] = "G19",
  ["channel_edit_page.14.length_pattern_priority"] = "G19",
  ["channel_edit_page.14.trig_merge_plus_pattern_inert"] = false,
  ["channel_edit_page.15.step_hold_shows_locks"] = "G08",
  ["note_edit_page.01.k1_row1_select_pattern"] = "G20",
  ["note_edit_page.01.set_note"] = "G28",
  ["note_edit_page.01.k1_set_note_all_banks"] = "G28",
  ["note_edit_page.02.long_row1_select_pattern"] = "G20",
  ["note_edit_page.03.bank_1"] = "G29",
  ["note_edit_page.04.bank_2"] = "G29",
  ["note_edit_page.05.bank_3"] = "G29",
  ["note_edit_page.06.bank_4"] = "G29",
  ["note_edit_page.07.note_view_down"] = "G29",
  ["note_edit_page.07.note_view_down_at_limit"] = false,
  ["note_edit_page.08.note_view_centre"] = "G29",
  ["note_edit_page.09.note_view_up"] = "G29",
  ["note_edit_page.09.note_view_up_at_limit"] = false,
  ["note_edit_page.10.long_row1_select_pattern"] = "G20",
  ["note_edit_page.10.long_view_top"] = "G29",
  ["note_edit_page.10.long_view_root"] = "G29",
  ["note_edit_page.10.long_view_bottom"] = "G29",
  ["scale_edit_page.01.range_set"] = "G35",
  ["scale_edit_page.01.range_rejected"] = "G35",
  ["scale_edit_page.01.scale_lock_set"] = "G34",
  ["scale_edit_page.01.scale_lock_clear"] = "G34",
  ["scale_edit_page.01.transpose_lock_set"] = "G34",
  ["scale_edit_page.01.transpose_lock_clear"] = "G34",
  ["scale_edit_page.02.k1_select_slot_only"] = "G32",
  ["scale_edit_page.02.set_global_scale"] = "G32",
  ["scale_edit_page.02.global_scale_off"] = "G32",
  ["scale_edit_page.03.long_clear_selected"] = "G32",
  ["scale_edit_page.03.long_select_slot"] = "G32",
  ["scale_edit_page.04.step_hold_shows_locks"] = "G34",
  ["scale_edit_page.05.step_release_restores_faders"] = "G34",
  ["scale_edit_page.06.transpose"] = "G33",
  ["song_edit_page.01.queue_slot_while_playing"] = "G36",
  ["song_edit_page.01.select_slot_stopped"] = "G36",
  ["song_edit_page.01.select_slot_stopped_elektron_pc"] = "G36",
  ["song_edit_page.02.global_length_queued"] = "G37",
  ["song_edit_page.02.global_length_immediate"] = "G37",
  ["song_edit_page.03.slot_copy_press_order"] = "G36",
  ["song_edit_page.03.non_slot_pair_refresh_only"] = false,
  ["trigger_edit_page.01.select_pattern"] = "G20",
  ["trigger_edit_page.01.select_pattern_discards_stale_doctor_preview"] = "G20",
  ["trigger_edit_page.02.toggle_trig"] = "G21",
  ["trigger_edit_page.03.pattern1_fill_euclid"] = "G24",
  ["trigger_edit_page.03.pattern1"] = "G24",
  ["trigger_edit_page.03.pattern1_inert_doctor"] = false,
  ["trigger_edit_page.04.pattern2_length_euclid"] = "G24",
  ["trigger_edit_page.04.pattern2"] = "G24",
  ["trigger_edit_page.04.pattern2_inert_doctor"] = false,
  ["trigger_edit_page.05.select_algorithm"] = "G23",
  ["trigger_edit_page.05.enter_doctor"] = "G40",
  ["trigger_edit_page.05.leave_doctor"] = "G23",
  ["trigger_edit_page.06.select_bank_mask"] = "G25",
  ["trigger_edit_page.06.bank_mask_inert"] = false,
  ["trigger_edit_page.07.record_start_capture"] = "G40",
  ["trigger_edit_page.07.record_finish"] = "G40",
  ["trigger_edit_page.07.record_cancel_prompt"] = "G40",
  ["trigger_edit_page.07.record_blocked_playing"] = "G40",
  ["trigger_edit_page.07.record_blocked_setup"] = "G40",
  ["trigger_edit_page.08.record_release_consumed"] = "G40",
  ["trigger_edit_page.09.select_lane"] = "G41",
  ["trigger_edit_page.09.select_lane_repreviews_paint"] = "G41",
  ["trigger_edit_page.09.non_lane_cell_inert"] = false,
  ["trigger_edit_page.10.arm_paint"] = "G26",
  ["trigger_edit_page.10.commit_paint"] = "G26",
  ["trigger_edit_page.10.doctor_arm_paint"] = "G42",
  ["trigger_edit_page.10.doctor_arm_paint_unavailable"] = "G42",
  ["trigger_edit_page.10.doctor_commit_paint"] = "G42",
  ["trigger_edit_page.10.doctor_commit_failed"] = "G42",
  ["trigger_edit_page.11.cancel_paint"] = "G26",
  ["trigger_edit_page.11.doctor_cancel_paint"] = "G42",
  ["trigger_edit_page.11.cancel_idle"] = false,
  ["trigger_edit_page.12.doctor_step_left"] = "G46",
  ["trigger_edit_page.12.shift_left"] = "G27",
  ["trigger_edit_page.12.left_idle"] = false,
  ["trigger_edit_page.13.doctor_phrase_start"] = "G46",
  ["trigger_edit_page.13.shift_reset"] = "G27",
  ["trigger_edit_page.13.centre_idle"] = false,
  ["trigger_edit_page.14.doctor_step_right"] = "G46",
  ["trigger_edit_page.14.shift_right"] = "G27",
  ["trigger_edit_page.14.right_idle"] = false,
  ["trigger_edit_page.15.length_forward"] = "G22",
  ["trigger_edit_page.15.length_wraps"] = "G22",
  ["trigger_edit_page.15.held_step_without_trig"] = false,
  ["trigger_edit_page.16.doctor_previous_phrase"] = "G46",
  ["trigger_edit_page.16.doctor_next_phrase"] = "G46",
  ["trigger_edit_page.16.long_shift_button_non_doctor"] = false,
  ["trigger_edit_page.17.reset_length"] = "G22",
  ["trigger_edit_page.17.reset_length_no_trig"] = false,
  ["velocity_edit_page.01.k1_row1_select_pattern"] = "G20",
  ["velocity_edit_page.01.set_velocity"] = "G30",
  ["velocity_edit_page.01.k1_set_velocity_all_banks"] = "G30",
  ["velocity_edit_page.02.long_row1_select_pattern"] = "G20",
  ["velocity_edit_page.03.bank_1"] = "G31",
  ["velocity_edit_page.04.bank_2"] = "G31",
  ["velocity_edit_page.05.bank_3"] = "G31",
  ["velocity_edit_page.06.bank_4"] = "G31",
  ["velocity_edit_page.07.velocity_view_down"] = "G31",
  ["velocity_edit_page.07.velocity_view_down_at_limit"] = false,
  ["velocity_edit_page.08.long_view_high"] = "G31",
  ["velocity_edit_page.08.long_view_low"] = "G31",
  ["velocity_edit_page.09.velocity_view_up"] = "G31",
  ["velocity_edit_page.09.velocity_view_up_at_limit"] = false,
}

outcomes.branches = {}
outcomes.retained = {}
for id, flow in pairs(LEDGER) do
  if flow then outcomes.branches[id] = flow else outcomes.retained[id] = true end
end

local function step_of(x, y) return (y - 4) * 16 + x end
local function is_step_row(y) return y ~= nil and y >= 4 and y <= 7 end

local function held_steps(event)
  local steps = {}
  for _, key in ipairs(event.pressed or {}) do
    if is_step_row(key[2]) then steps[#steps + 1] = step_of(key[1], key[2]) end
  end
  table.sort(steps)
  return steps
end

-- Page button (x = 3..6) of a page, as pages.pages_to_grid_menu_button_mappings.
local function page_button(page)
  if page == PAGE.channel then return 3 end
  if page == PAGE.scale then return 4 end
  if page == PAGE.trig or page == PAGE.note or page == PAGE.velocity then return 5 end
  if page == PAGE.song then return 6 end
  return nil
end

local function next_merge_state(before, count)
  before = before or count -- nil: assume the cycle lands on state 1
  if before >= count then return 1 end
  return before + 1
end

local ALL_BANKS = {"bank_1", "bank_2", "bank_3", "bank_4"}

-- Each phase handler returns (branch_ids, payload) for the registrations that fired.

local function menu_short(e)
  local x = e.x
  local p = e.page_before
  if x == 3 then return {"m_grid.01.channel_page"}, {page = e.page_after} end
  if x == 4 then return {"m_grid.01.scale_page"}, {page = e.page_after} end
  if x == 6 then return {"m_grid.01.song_page"}, {page = e.page_after} end
  if x == 5 then
    local id = p == PAGE.trig and "m_grid.01.pattern_trig_to_note"
      or p == PAGE.note and "m_grid.01.pattern_note_to_velocity"
      or p == PAGE.velocity and "m_grid.01.pattern_velocity_to_trig"
      or "m_grid.01.pattern_other_to_trig"
    return {id}, {page = e.page_after}
  end
  if x == 1 then
    if not e.playing_before then
      if p == PAGE.trig and e.algorithm_before == 5 then return {"m_grid.02.start_with_doctor_open"} end
      return {"m_grid.02.start"}
    end
    if not e.stop_safety or e.shift then return {"m_grid.02.stop"} end
    return {"m_grid.02.stop_blocked_by_safety"}
  end
  if x == 2 then
    return {e.recording_before and "m_grid.02.record_off" or "m_grid.02.record_on"}
  end
  return nil
end

local function menu_long(e)
  local x = e.x
  if x == 1 then
    return {e.stop_safety and "m_grid.03.long_stop_with_safety" or "m_grid.03.long_play_without_safety"}
  end
  if x >= 3 and x <= 6 then
    if page_button(e.page_before) ~= x then return {"m_grid.04.panic"} end
    return {"m_grid.04.long_current_page_button"}
  end
  return nil
end

-- Channel page ----------------------------------------------------------------

local function merge_press(e)
  local x = e.x
  if x == 14 then
    local s = next_merge_state(e.merge_state_before, 3)
    return {({"channel_edit_page.08.trig_merge_skip", "channel_edit_page.08.trig_merge_only",
      "channel_edit_page.08.trig_merge_all"})[s]}
  end
  local names = {"average", "up", "down", "pattern_wraps_to_average"}
  local s = names[next_merge_state(e.merge_state_before, 4)]
  if x == 15 then return {"channel_edit_page.09.note_merge_" .. s} end
  if e.shift then return {"channel_edit_page.11.length_merge_" .. s} end
  return {"channel_edit_page.10.velocity_merge_" .. s}
end

local channel = {}

function channel.short(e)
  local x, y = e.x, e.y
  if y == 1 then
    if e.shift then
      return {e.channel_muted_before and "channel_edit_page.04.k1_unmute" or "channel_edit_page.04.k1_mute"},
        {channel = x}
    end
    return {"channel_edit_page.04.select_channel"}, {channel = x}
  end
  if y == 2 then
    return {e.pattern_assigned_before and "channel_edit_page.07.pattern_removed" or "channel_edit_page.07.pattern_added"},
      {pattern = x}
  end
  if is_step_row(y) then
    local payload = {step = step_of(x, y)}
    if e.feature_editor_open then return {"channel_edit_page.01.leave_feature_editor"}, payload end
    if e.shift then return {"channel_edit_page.01.k1_toggle_trig_mask"}, payload end
    return {"channel_edit_page.01.plain_tap_no_feature"}, payload
  end
  if y == 8 and x >= 8 and x <= 12 then return {"channel_edit_page.13.channel_octave"} end
  if y == 8 and x >= 14 then return merge_press(e) end
  return nil
end

function channel.long(e)
  local x, y = e.x, e.y
  if is_step_row(y) then
    local payload = {step = step_of(x, y)}
    if e.shift then return {"channel_edit_page.02.k1_long_clear_trig_mask"}, payload end
    return {"channel_edit_page.02.plain_long_step"}, payload
  end
  if y == 1 then
    return {e.channel_muted_before and "channel_edit_page.05.long_unmute" or "channel_edit_page.05.long_mute"},
      {channel = x}
  end
  return nil
end

function channel.pre(e)
  if is_step_row(e.y) then
    return {"channel_edit_page.15.step_hold_shows_locks"}, {step = step_of(e.x, e.y), steps = held_steps(e)}
  end
  return nil
end

function channel.post(e)
  local x, y = e.x, e.y
  if is_step_row(y) then
    return {"channel_edit_page.03.step_release_records_locks"}, {step = step_of(x, y), steps = held_steps(e)}
  end
  if y == 8 and x >= 14 and x <= 16 then
    if e.gesture_dual_flow == "G19" then return {"channel_edit_page.12.release_after_pattern_priority"} end
    if x == 14 then return {"channel_edit_page.12.trig_merge_release_hides_gesture"} end
    if x == 15 then return {"channel_edit_page.12.note_merge_release_hides_gesture"} end
    return {"channel_edit_page.12.velocity_length_merge_release_hides_gesture"}
  end
  return nil
end

function channel.dual(e)
  local hx, hy, x, y = e.held_x, e.held_y, e.x, e.y
  if is_step_row(hy) and is_step_row(y) then
    local from, to = step_of(hx, hy), step_of(x, y)
    return {to > from and "channel_edit_page.06.range_set" or "channel_edit_page.06.range_rejected"},
      {from_step = from, to_step = to}
  end
  if y == 8 and x >= 8 and x <= 12 then
    return {e.lock_cleared and "channel_edit_page.06.octave_lock_clear" or "channel_edit_page.06.octave_lock_set"},
      {step = step_of(hx, hy)}
  end
  if y == 3 then
    return {e.lock_cleared and "channel_edit_page.06.scale_lock_clear" or "channel_edit_page.06.scale_lock_set"},
      {step = step_of(hx, hy)}
  end
  if hy == 1 and y == 1 then
    if e.shift then return {"channel_edit_page.06.k1_dual_mute_toggle"}, {channels = {hx, x}} end
    return {"channel_edit_page.06.two_channels_no_k1"}
  end
  if y == 2 and hy == 8 then
    if hx == 15 then return {"channel_edit_page.14.note_pattern_priority"}, {pattern = x} end
    if hx == 16 and e.shift then return {"channel_edit_page.14.length_pattern_priority"}, {pattern = x} end
    if hx == 16 then return {"channel_edit_page.14.velocity_pattern_priority"}, {pattern = x} end
    if hx == 14 then return {"channel_edit_page.14.trig_merge_plus_pattern_inert"} end
  end
  return nil
end

-- Scale page ------------------------------------------------------------------

local scale = {}

function scale.short(e)
  local x, y = e.x, e.y
  if y == 3 then
    if e.shift then return {"scale_edit_page.02.k1_select_slot_only"} end
    return {e.scale_slot_is_global and "scale_edit_page.02.global_scale_off" or "scale_edit_page.02.set_global_scale"}
  end
  if y == 8 and x >= 8 then return {"scale_edit_page.06.transpose"} end
  return nil
end

function scale.long(e)
  if e.y == 3 then
    return {e.scale_slot_selected and "scale_edit_page.03.long_clear_selected" or "scale_edit_page.03.long_select_slot"}
  end
  return nil
end

function scale.pre(e)
  if is_step_row(e.y) then return {"scale_edit_page.04.step_hold_shows_locks"}, {step = step_of(e.x, e.y), steps = held_steps(e)} end
  return nil
end

function scale.post(e)
  if is_step_row(e.y) then return {"scale_edit_page.05.step_release_restores_faders"}, {step = step_of(e.x, e.y), steps = held_steps(e)} end
  return nil
end

function scale.dual(e)
  local hx, hy, x, y = e.held_x, e.held_y, e.x, e.y
  if is_step_row(hy) and is_step_row(y) then
    local from, to = step_of(hx, hy), step_of(x, y)
    return {to > from and "scale_edit_page.01.range_set" or "scale_edit_page.01.range_rejected"},
      {from_step = from, to_step = to}
  end
  if y == 3 then
    return {e.lock_cleared and "scale_edit_page.01.scale_lock_clear" or "scale_edit_page.01.scale_lock_set"},
      {step = step_of(hx, hy)}
  end
  if y == 8 and x >= 8 then
    return {e.lock_cleared and "scale_edit_page.01.transpose_lock_clear" or "scale_edit_page.01.transpose_lock_set"},
      {step = step_of(hx, hy)}
  end
  return nil
end

-- Song page -------------------------------------------------------------------

local song = {}

local function slot_of(x, y) return (y - 1) * 16 + x end
local function is_slot(y) return y ~= nil and y >= 1 and y <= 6 end

function song.short(e)
  local x, y = e.x, e.y
  if is_slot(y) then
    local id
    if e.playing then id = "song_edit_page.01.queue_slot_while_playing"
    elseif e.elektron_program_changes then id = "song_edit_page.01.select_slot_stopped_elektron_pc"
    else id = "song_edit_page.01.select_slot_stopped" end
    return {id}, {slot = slot_of(x, y)}
  end
  if y == 7 and x <= 8 then
    return {e.playing and "song_edit_page.02.global_length_queued" or "song_edit_page.02.global_length_immediate"}
  end
  return nil
end

function song.dual(e)
  if is_slot(e.held_y) and is_slot(e.y) then
    return {"song_edit_page.03.slot_copy_press_order"}, {slots = {slot_of(e.held_x, e.held_y), slot_of(e.x, e.y)}}
  end
  return {"song_edit_page.03.non_slot_pair_refresh_only"}
end

-- Note and Velocity pages -----------------------------------------------------

local note = {}

function note.short(e)
  local x, y = e.x, e.y
  if y == 1 and e.shift then return {"note_edit_page.01.k1_row1_select_pattern"}, {pattern = x} end
  if y <= 7 then
    return {e.shift and "note_edit_page.01.k1_set_note_all_banks" or "note_edit_page.01.set_note"}
  end
  if x >= 9 and x <= 12 then
    return {"note_edit_page.0" .. (x - 6) .. "." .. ALL_BANKS[x - 8]}
  end
  if x == 14 then return {e.view_at_limit and "note_edit_page.07.note_view_down_at_limit" or "note_edit_page.07.note_view_down"} end
  if x == 15 then return {"note_edit_page.08.note_view_centre"} end
  if x == 16 then return {e.view_at_limit and "note_edit_page.09.note_view_up_at_limit" or "note_edit_page.09.note_view_up"} end
  return nil
end

function note.long(e)
  local x, y = e.x, e.y
  if y == 1 then
    return {"note_edit_page.02.long_row1_select_pattern", "note_edit_page.10.long_row1_select_pattern"}, {pattern = x}
  end
  if y == 8 and x == 14 then return {"note_edit_page.10.long_view_top"} end
  if y == 8 and x == 15 then return {"note_edit_page.10.long_view_root"} end
  if y == 8 and x == 16 then return {"note_edit_page.10.long_view_bottom"} end
  return nil
end

local velocity = {}

function velocity.short(e)
  local x, y = e.x, e.y
  if y == 1 and e.shift then return {"velocity_edit_page.01.k1_row1_select_pattern"}, {pattern = x} end
  if y <= 7 then
    return {e.shift and "velocity_edit_page.01.k1_set_velocity_all_banks" or "velocity_edit_page.01.set_velocity"}
  end
  if x >= 9 and x <= 12 then
    return {"velocity_edit_page.0" .. (x - 6) .. "." .. ALL_BANKS[x - 8]}
  end
  if x == 16 then
    return {e.view_at_limit and "velocity_edit_page.07.velocity_view_down_at_limit" or "velocity_edit_page.07.velocity_view_down"}
  end
  if x == 15 then
    return {e.view_at_limit and "velocity_edit_page.09.velocity_view_up_at_limit" or "velocity_edit_page.09.velocity_view_up"}
  end
  return nil
end

function velocity.long(e)
  local x, y = e.x, e.y
  if y == 1 then return {"velocity_edit_page.02.long_row1_select_pattern"}, {pattern = x} end
  if y == 8 and x == 16 then return {"velocity_edit_page.08.long_view_high"} end
  if y == 8 and x == 15 then return {"velocity_edit_page.08.long_view_low"} end
  return nil
end

-- Trig page -------------------------------------------------------------------

local trig = {}

local function doctor_generator_cell(e, inert_id)
  -- Algorithm 5: the pattern fader returns early; the lane handler owns the cell.
  local ids = {inert_id}
  if e.x >= 2 then
    if e.lane_hit then
      table.insert(ids, 1, e.paint_armed and "trigger_edit_page.09.select_lane_repreviews_paint"
        or "trigger_edit_page.09.select_lane")
    else
      ids[#ids + 1] = "trigger_edit_page.09.non_lane_cell_inert"
    end
  end
  return ids
end

function trig.short(e)
  local x, y, alg = e.x, e.y, e.algorithm_before
  if y == 1 then
    if alg == 5 and e.paint_armed then
      return {"trigger_edit_page.01.select_pattern_discards_stale_doctor_preview"}, {pattern = x}
    end
    return {"trigger_edit_page.01.select_pattern"}, {pattern = x}
  end
  if is_step_row(y) then return {"trigger_edit_page.02.toggle_trig"}, {step = step_of(x, y)} end
  if (y == 2 or y == 3) and x <= 10 then
    if alg == 5 then
      return doctor_generator_cell(e, y == 2 and "trigger_edit_page.03.pattern1_inert_doctor"
        or "trigger_edit_page.04.pattern2_inert_doctor")
    end
    if y == 2 then return {alg == 3 and "trigger_edit_page.03.pattern1_fill_euclid" or "trigger_edit_page.03.pattern1"} end
    return {alg == 3 and "trigger_edit_page.04.pattern2_length_euclid" or "trigger_edit_page.04.pattern2"}
  end
  if (y == 2 or y == 3) and x == 11 then
    if alg == 5 then return {"trigger_edit_page.09.non_lane_cell_inert"} end
    return nil
  end
  if y == 2 and x >= 12 then
    local selected = x - 11
    if alg ~= 5 and selected == 5 then return {"trigger_edit_page.05.enter_doctor"}, {algorithm = 5} end
    if alg == 5 and selected ~= 5 then return {"trigger_edit_page.05.leave_doctor"}, {algorithm = selected} end
    if alg ~= 5 then return {"trigger_edit_page.05.select_algorithm"}, {algorithm = selected} end
    return nil -- 5 -> 5: no ledger branch (no enter/leave; refresh and tooltip only)
  end
  if y == 3 and x >= 12 then
    if alg == 3 or alg == 5 then return {"trigger_edit_page.06.bank_mask_inert"} end
    local last = alg == 4 and 15 or 16 -- algorithm 4 shrinks the bank-mask fader to 4 cells
    if x <= last then return {"trigger_edit_page.06.select_bank_mask"} end
    return nil
  end
  if y == 8 and x == 16 then
    if alg == 5 then
      if e.paint_armed then
        return {e.paint_armed_after and "trigger_edit_page.10.doctor_commit_failed" or "trigger_edit_page.10.doctor_commit_paint"}
      end
      return {e.paint_armed_after == false and "trigger_edit_page.10.doctor_arm_paint_unavailable"
        or "trigger_edit_page.10.doctor_arm_paint"}
    end
    return {e.paint_armed and "trigger_edit_page.10.commit_paint" or "trigger_edit_page.10.arm_paint"}
  end
  if y == 8 and x == 14 then
    if not e.paint_armed then return {"trigger_edit_page.11.cancel_idle"} end
    return {alg == 5 and "trigger_edit_page.11.doctor_cancel_paint" or "trigger_edit_page.11.cancel_paint"}
  end
  if y == 8 and x >= 10 and x <= 12 then
    local reg = ({[10] = "12", [11] = "13", [12] = "14"})[x]
    local doctor = ({[10] = "doctor_step_left", [11] = "doctor_phrase_start", [12] = "doctor_step_right"})[x]
    local shifted = ({[10] = "shift_left", [11] = "shift_reset", [12] = "shift_right"})[x]
    local idle = ({[10] = "left_idle", [11] = "centre_idle", [12] = "right_idle"})[x]
    local name = alg == 5 and doctor or e.paint_armed and shifted or idle
    return {"trigger_edit_page." .. reg .. "." .. name}
  end
  return nil
end

function trig.long(e)
  local x, y = e.x, e.y
  if y == 8 and (x == 10 or x == 12) then
    if e.algorithm_before ~= 5 then return {"trigger_edit_page.16.long_shift_button_non_doctor"} end
    return {x == 10 and "trigger_edit_page.16.doctor_previous_phrase" or "trigger_edit_page.16.doctor_next_phrase"}
  end
  if is_step_row(y) then
    return {e.step_has_trig and "trigger_edit_page.17.reset_length" or "trigger_edit_page.17.reset_length_no_trig"},
      {step = step_of(x, y)}
  end
  return nil
end

function trig.dual(e)
  local hx, hy, x, y = e.held_x, e.held_y, e.x, e.y
  if not (is_step_row(hy) and is_step_row(y)) then return nil end
  local from, to = step_of(hx, hy), step_of(x, y)
  local payload = {step = from, from_step = from, to_step = to}
  if not e.step_has_trig then return {"trigger_edit_page.15.held_step_without_trig"}, payload end
  return {to > from and "trigger_edit_page.15.length_forward" or "trigger_edit_page.15.length_wraps"}, payload
end

function trig.pre(e)
  if e.x ~= 1 or e.y ~= 2 or e.algorithm_before ~= 5 then return nil end
  local id
  if e.playing_before or e.playing then id = "trigger_edit_page.07.record_blocked_playing"
  elseif e.doctor_setup_open then id = "trigger_edit_page.07.record_blocked_setup"
  elseif e.doctor_state == nil or e.doctor_state == "EMPTY" or e.doctor_state == "FAILED" then
    id = "trigger_edit_page.07.record_start_capture"
  elseif e.doctor_finish_eligible then id = "trigger_edit_page.07.record_finish"
  else id = "trigger_edit_page.07.record_cancel_prompt" end
  return {id}
end

function trig.post(e)
  if e.x == 1 and e.y == 2 and e.algorithm_before == 5 then return {"trigger_edit_page.08.record_release_consumed"} end
  return nil
end

local PAGE_HANDLERS = {
  [PAGE.channel] = channel,
  [PAGE.scale] = scale,
  [PAGE.trig] = trig,
  [PAGE.note] = note,
  [PAGE.velocity] = velocity,
  [PAGE.song] = song,
}

local function dispatch(event)
  local phase = event.phase
  -- press:handle / press:handle_long run the "menu" registrations first, then the
  -- registrations of the page selected before the handler (found_page is fixed on
  -- entry). Menu cells (y = 8, x = 1..6) and page cells never overlap.
  if event.y == 8 and event.x and event.x <= 6 then
    if phase == "short" then return menu_short(event) end
    if phase == "long" then return menu_long(event) end
  end
  local page = PAGE_HANDLERS[event.page_before]
  local handler = page and page[phase]
  if handler then return handler(event) end
  return nil
end

function outcomes.classify(event)
  if type(event) ~= "table" or event.x == nil or event.y == nil then return nil, nil end
  local ids, payload = dispatch(event)
  if not ids or #ids == 0 then return nil, nil end
  local extra = {}
  for k, v in pairs(payload or {}) do extra[k] = v end
  extra.branch = ids[1]
  extra.branches = ids
  extra.claimed = event.claimed == true
  local flow = nil
  for _, id in ipairs(ids) do
    local f = LEDGER[id]
    if f == nil then error("ui_grid_outcomes: unknown ledger branch " .. tostring(id)) end
    if f and not flow then flow = f; extra.branch = id end
  end
  return flow, extra
end

return outcomes
