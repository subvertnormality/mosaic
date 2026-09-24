-- README.md "Norns Menu Navigation", "Grid Menu Navigation" and "Channel
-- Editor" ("Masks", "Devices", "Clocks, Swing and Shuffle", "Memory (undo and
-- redo)", "Merge Modes") with "Trig Parameters" (slot assignment, held-step
-- trig locks), as the live norns UI drives them (lib/ui_live.lua,
-- docs/ui-reimplementation/IMPLEMENTATION.md "Router and grid follow (UI03)").
-- The task list, held-step family follow, feature-editor routing and failure
-- containment are characterisations of that spec outside the manual.
--
-- Integration: every scenario boots the real program model, lib/ui.lua with
-- every page UI and owner, and ui_live.install() (helpers/ui_live_env.lua);
-- input goes through ui.enc / ui.key and the grid notification entry points
-- ui_live.grid_hold / ui_live.grid_outcome. Each test asserts the owner/model
-- effect and the router screen, never only internal flags.

local live = include("mosaic/lib/tests/helpers/ui_live_env")

local function screen() return ui_live.state().screen end
local function channel_page() return live.channel_page() end
local function owners() return channel_edit_page_ui.adapter_owners() end

local function tap(n)
  ui.key(n, 1)
  ui.key(n, 0)
end

local function field_ids(screen_id)
  local ids = {}
  for index, d in ipairs(ui_live.describe(screen_id)) do ids[index] = d.id end
  return ids
end

local function index_of(list, value)
  for index, item in ipairs(list) do if item == value then return index end end
end

-- Moves the focus on a tasks screen to `row` with E2, as a player would.
local function choose_task(row)
  local ids = field_ids()
  local wanted = index_of(ids, row)
  luaunit.assert_not_nil(wanted, "no task row " .. row .. " on " .. screen())
  local now = index_of(ids, ui_live.state().field_id) or 1
  if wanted ~= now then ui.enc(2, wanted - now) end
  luaunit.assert_equals(ui_live.state().field_id, row)
end

-- Opens a Channel Tasks row from C01: E1+ twice reaches N01, then E2 and K3.
local function open_task(row)
  ui.enc(1, 1); ui.enc(1, 1)
  luaunit.assert_equals(screen(), "N01")
  choose_task(row)
  tap(3)
end

-- Channel E1 family --------------------------------------------------------------

function test_ui_live_channel_e1_walks_c01_c02_n01_and_back_one_boundary_at_a_time()
  live.isolated(function()
    luaunit.assert_equals(screen(), "C01")
    luaunit.assert_equals(ui_live.state().context, "Channel")
    luaunit.assert_equals(channel_page(), 1)

    ui.enc(1, 1)
    luaunit.assert_equals(screen(), "C02")
    luaunit.assert_equals(channel_page(), 2) -- the Trig Locks workspace follows
    ui.enc(1, 1)
    luaunit.assert_equals(screen(), "N01")
    ui.enc(1, 1)
    luaunit.assert_equals(screen(), "N01") -- clamped at the task list

    ui.enc(1, -1)
    luaunit.assert_equals(screen(), "C02")
    luaunit.assert_equals(channel_page(), 2)
    ui.enc(1, -1)
    luaunit.assert_equals(screen(), "C01")
    luaunit.assert_equals(channel_page(), 1)
    ui.enc(1, -1)
    luaunit.assert_equals(screen(), "C01")
  end)
end

function test_ui_live_channel_large_e1_delta_moves_exactly_one_family_boundary()
  live.isolated(function()
    ui.enc(1, 7)
    luaunit.assert_equals(screen(), "C02")
    luaunit.assert_equals(channel_page(), 2)
    ui.enc(1, 9)
    luaunit.assert_equals(screen(), "N01")
    ui.enc(1, -12)
    luaunit.assert_equals(screen(), "C02")
    ui.enc(1, -5)
    luaunit.assert_equals(screen(), "C01")
    luaunit.assert_equals(channel_page(), 1)
  end)
end

function test_ui_live_zero_encoder_delta_is_ignored()
  live.isolated(function()
    local selectors = owners().mask_selectors
    ui.enc(1, 0); ui.enc(2, 0); ui.enc(3, 0)
    luaunit.assert_equals(screen(), "C01")
    luaunit.assert_true(selectors.note:is_selected())
    luaunit.assert_nil(program.get_selected_channel().note_mask)
  end)
end

function test_ui_live_c01_e2_moves_the_owner_mask_selector_and_focus_follows()
  live.isolated(function()
    local selectors = owners().mask_selectors
    -- The first focus is the owner's own selection: Note.
    luaunit.assert_true(selectors.note:is_selected())
    luaunit.assert_equals(ui_live.state().field_id, "note")

    ui.enc(2, 1)
    luaunit.assert_equals(screen(), "C01")
    luaunit.assert_true(selectors.velocity:is_selected())
    luaunit.assert_false(selectors.note:is_selected())
    luaunit.assert_equals(ui_live.state().field_id, "velocity")

    ui.enc(2, -2)
    luaunit.assert_true(selectors.trig:is_selected())
    luaunit.assert_equals(ui_live.state().field_id, "trig")

    ui.enc(2, -1) -- the owner clamps at Trig
    luaunit.assert_true(selectors.trig:is_selected())
    luaunit.assert_equals(ui_live.state().field_id, "trig")
  end)
end

-- One scenario, on fresh state, through either input path.
local function mask_scenario(drive)
  local result
  live.isolated(function()
    program.get().selected_channel = 3
    channel_edit_page_ui.refresh()
    drive()
    local c = program.get_selected_channel()
    result = {note = c.note_mask, velocity = c.velocity_mask, trig = c.trig_mask, length = c.length_mask,
      other = program.get_channel(1, 1).note_mask, screen = screen()}
  end)
  return result
end

function test_ui_live_c01_e3_edits_the_focused_mask_on_the_selected_channel_as_the_old_enc_path()
  local old = mask_scenario(function()
    channel_edit_page_ui.enc(3, 3)
    channel_edit_page_ui.enc(2, 1)
    channel_edit_page_ui.enc(3, 2)
    channel_edit_page_ui.enc(3, -1)
  end)
  local new = mask_scenario(function()
    ui.enc(3, 3)
    ui.enc(2, 1)
    ui.enc(3, 2)
    ui.enc(3, -1)
  end)
  luaunit.assert_not_nil(new.note)
  luaunit.assert_not_nil(new.velocity)
  luaunit.assert_equals(new.note, old.note)
  luaunit.assert_equals(new.velocity, old.velocity)
  luaunit.assert_equals(new.trig, old.trig)
  luaunit.assert_equals(new.length, old.length)
  luaunit.assert_nil(new.other) -- channel 1 untouched
  luaunit.assert_equals(new.screen, "C01")
end

-- Channel Tasks ---------------------------------------------------------------------

-- Each N01 row: its screen and the legacy channel sub-page (channel_page_to_index)
-- the owner shows for it. N04 (norns settings) keeps the page it came from.
local TASK_ROWS = {
  {"masks", "C01", 1}, {"trig_params", "C02", 2}, {"output", "C06", 6}, {"harmony", "H01", 8},
  {"clock", "C04", 4}, {"merge", "C09", 6}, {"device", "C05", 5}, {"history", "C03", 3},
  {"mask_detail", "C12", 1}, {"trig_detail", "C13", 2}, {"merge_shape", "M02", 7}, {"norns", "N04", 2},
}

function test_ui_live_channel_tasks_e2_k3_enters_every_row_and_the_legacy_sub_page_follows()
  for _, row in ipairs(TASK_ROWS) do
    local id, expected_screen, expected_page = row[1], row[2], row[3]
    live.isolated(function()
      open_task(id)
      luaunit.assert_equals(screen(), expected_screen, "row " .. id)
      luaunit.assert_equals(ui_live.state().context, "Channel")
      luaunit.assert_equals(channel_page(), expected_page, "legacy page for row " .. id)
    end)
  end
end

function test_ui_live_channel_tasks_e1_from_an_entered_task_returns_to_n01()
  for _, id in ipairs({"output", "harmony", "clock", "device", "history", "mask_detail", "trig_detail", "merge_shape"}) do
    live.isolated(function()
      open_task(id)
      local entered = screen()
      ui.enc(1, 1)
      luaunit.assert_equals(screen(), "N01", "E1 from " .. entered)
      -- The focus stays on the row that was opened.
      luaunit.assert_equals(ui_live.state().field_id, id)
    end)
  end
end

function test_ui_live_channel_tasks_e3_does_not_edit_and_e2_clamps_to_the_rows()
  live.isolated(function()
    ui.enc(1, 1); ui.enc(1, 1)
    ui.enc(3, 4)
    luaunit.assert_equals(screen(), "N01")
    luaunit.assert_equals(ui_live.state().field_id, "masks")
    luaunit.assert_nil(program.get_selected_channel().note_mask)
    ui.enc(2, -9) -- clamps to the first row
    luaunit.assert_equals(ui_live.state().field_id, "masks")
    ui.enc(2, 99) -- clamps to the last row
    luaunit.assert_equals(ui_live.state().field_id, "norns")
  end)
end

-- C02 assignment (C07) ----------------------------------------------------------------

function test_ui_live_c02_k2_opens_c07_e3_moves_cursor_k3_assigns_the_e2_slot_k2_returns()
  live.isolated(function(env)
    local o = owners()
    local controls = o.parameters.adapter_controls()
    ui.enc(1, 1)
    luaunit.assert_equals(screen(), "C02")
    ui.enc(2, 2) -- slot 3
    luaunit.assert_equals(o.dials:get_selected_index(), 3)
    luaunit.assert_equals(ui_live.state().field_id, "slot_3")

    tap(2)
    luaunit.assert_equals(screen(), "C07")
    luaunit.assert_true(controls.trig_lock_page:is_sub_page_enabled())
    luaunit.assert_equals(channel_page(), 2)
    local selector = controls.param_select_vertical_scroll_selector
    local before = selector:get_selected_index()

    ui.enc(3, 1)
    luaunit.assert_equals(selector:get_selected_index(), before + 1)
    luaunit.assert_true(save_confirm.has_pending())
    local chosen = selector:get_selected_item().id
    luaunit.assert_equals(ui_live.state().field_id, tostring(chosen))
    local c = program.get_selected_channel()
    luaunit.assert_not_equals(c.trig_lock_params[3].id, chosen)

    tap(3)
    luaunit.assert_equals(c.trig_lock_params[3].id, chosen)
    luaunit.assert_not_equals(c.trig_lock_params[1].id, chosen)
    luaunit.assert_false(save_confirm.has_pending())
    luaunit.assert_equals(screen(), "C07")

    tap(2)
    luaunit.assert_equals(screen(), "C02")
    luaunit.assert_false(controls.trig_lock_page:is_sub_page_enabled())
    luaunit.assert_equals(c.trig_lock_params[3].id, chosen)
  end)
end

-- Held steps --------------------------------------------------------------------------

function test_ui_live_hold_on_c01_e3_stages_a_step_mask_lock_not_the_channel_default()
  live.isolated(function(env)
    local c = program.get_selected_channel()
    ui.enc(3, 5) -- a channel default note mask first
    local default = c.note_mask
    luaunit.assert_not_nil(default)

    live.press_steps(env, {5})
    ui_live.grid_hold({5})
    luaunit.assert_equals(screen(), "C01")
    luaunit.assert_true(ui_live.state().held)
    luaunit.assert_equals(ui_live.state().target.step_set, {5})

    ui.enc(3, 2)
    luaunit.assert_equals(screen(), "C01")
    luaunit.assert_equals(c.note_mask, default) -- the channel default is untouched
    local staged = recorder.mask_events[c.number] and recorder.mask_events[c.number][5]
    luaunit.assert_not_nil(staged, "held E3 staged no step mask for step 5")
    luaunit.assert_equals(staged.data.step, 5)
    luaunit.assert_equals(staged.data.note, owners().mask_selectors.note:get_value())
    luaunit.assert_nil(recorder.mask_events[c.number][6])

    env.pressed = {}
    ui_live.grid_hold({})
    luaunit.assert_equals(screen(), "C01")
    luaunit.assert_false(ui_live.state().held)
    luaunit.assert_equals(ui_live.state().target.step_set, {})
  end)
end

-- A norns parameter in trig lock slot 1 with channel value 10.
local function assign_slot_one(env)
  local c = program.get_selected_channel()
  local values = env.param_values
  values.p1 = 10
  env.param_objects.p1 = {id = "p1", minval = 0, maxval = 127,
    get = function() return values.p1 end, get_raw = function() return values.p1 end,
    set_raw = function(_, v) values.p1 = v end, delta = function(_, d) values.p1 = values.p1 + d end}
  -- Assignment through C07 starts the slot's lock calculator (increment_trig_lock_calculator_id).
  program.increment_trig_lock_calculator_id(c, 1)
  c.trig_lock_params[1] = {id = "p1", param_id = "p1", name = "Cutoff", type = "norns",
    short_descriptor_1 = "CUT", short_descriptor_2 = "", off_value = -1}
  channel_edit_page_ui.refresh_trig_locks()
  return c
end

-- channel_edit_page_ui.enc(3, 2) on the Trig Locks page: the value the old
-- path gives, with step 5 held (the staged lock) or with no hold (the param).
local function old_trig_lock_edit(held)
  local value
  live.isolated(function(env)
    local c = assign_slot_one(env)
    channel_edit_page_ui.select_channel_page_by_index(2)
    if held then live.press_steps(env, {5}) end
    channel_edit_page_ui.enc(3, 2)
    if held then value = recorder.trig_lock_events[c.number][5].data.value else value = env.param_values.p1 end
  end)
  return value
end
function test_ui_live_hold_on_c04_shows_the_remembered_family_and_e3_edits_the_held_step_lock()
  local expected = old_trig_lock_edit(true)
  live.isolated(function(env)
    local c = assign_slot_one(env)
    open_task("clock") -- through C02: the remembered family is Trig Params
    luaunit.assert_equals(screen(), "C04")
    luaunit.assert_equals(channel_page(), 4)

    live.press_steps(env, {5})
    ui_live.grid_hold({5})
    luaunit.assert_equals(screen(), "C02")
    luaunit.assert_equals(channel_page(), 2)

    ui.enc(3, 2)
    luaunit.assert_equals(screen(), "C02")
    luaunit.assert_equals(env.param_values.p1, 10) -- the channel value is untouched
    local staged = recorder.trig_lock_events[c.number] and recorder.trig_lock_events[c.number][5]
    luaunit.assert_not_nil(staged, "held E3 staged no trig lock for step 5")
    -- The old path (Trig Locks page, step held, E3 +2) stages the same lock.
    luaunit.assert_equals(staged.data, {parameter = 1, step = 5, value = expected})
    luaunit.assert_nil(recorder.trig_lock_events[c.number][6])

    env.pressed = {}
    ui_live.grid_hold({})
    luaunit.assert_equals(screen(), "C04")
    luaunit.assert_equals(channel_page(), 4)
    luaunit.assert_false(ui_live.state().held)
  end)
end

function test_ui_live_unheld_e3_on_c02_edits_the_channel_value_not_a_step()
  local expected = old_trig_lock_edit(false)
  live.isolated(function(env)
    local c = assign_slot_one(env)
    ui.enc(1, 1)
    luaunit.assert_equals(screen(), "C02")
    ui.enc(3, 2)
    luaunit.assert_not_equals(env.param_values.p1, 10)
    luaunit.assert_equals(env.param_values.p1, expected)
    luaunit.assert_equals(screen(), "C02")
    luaunit.assert_nil(recorder.trig_lock_events[c.number])
  end)
end

function test_ui_live_hold_shows_the_remembered_parameters_family_and_restores_the_parent()
  live.isolated(function(env)
    ui.enc(1, 1) -- C02: the remembered family is now Trig Params
    ui.enc(1, 1)
    choose_task("history")
    tap(3)
    luaunit.assert_equals(screen(), "C03")
    luaunit.assert_equals(channel_page(), 3)

    live.press_steps(env, {5, 6})
    ui_live.grid_hold({5, 6})
    luaunit.assert_equals(screen(), "C02")
    luaunit.assert_equals(channel_page(), 2)
    luaunit.assert_equals(ui_live.state().target.step_set, {5, 6})

    env.pressed = {}
    ui_live.grid_hold({})
    luaunit.assert_equals(screen(), "C03")
    luaunit.assert_equals(channel_page(), 3)
  end)
end

function test_ui_live_hold_on_an_observe_in_place_screen_stays()
  live.isolated(function(env)
    open_task("output")
    luaunit.assert_equals(screen(), "C06")
    live.press_steps(env, {9})
    ui_live.grid_hold({9})
    luaunit.assert_equals(screen(), "C06")
    luaunit.assert_equals(ui_live.state().target.step_set, {9})
    env.pressed = {}
    ui_live.grid_hold({})
    luaunit.assert_equals(screen(), "C06")
    luaunit.assert_equals(channel_page(), 6)
  end)
end

-- Feature editors -------------------------------------------------------------------------

function test_ui_live_harmony_h01_e3_edits_the_draft_k3_applies_and_k2_on_the_root_stays()
  live.isolated(function()
    local c = program.get_selected_channel()
    local editor = owners().feature_editors.harmony
    open_task("harmony")
    luaunit.assert_equals(screen(), "H01")
    luaunit.assert_equals(channel_page(), 8)
    local before = c.voicing and c.voicing.mode
    luaunit.assert_equals(ui_live.state().field_id, "mode")

    ui.enc(3, 1)
    luaunit.assert_true(editor.dirty)
    local drafted = editor.draft.mode
    luaunit.assert_not_equals(drafted, before or "off")
    luaunit.assert_equals(c.voicing and c.voicing.mode, before) -- nothing applied yet
    luaunit.assert_equals(screen(), "H01")

    tap(3)
    luaunit.assert_equals(c.voicing.mode, drafted)
    luaunit.assert_false(editor.dirty)
    luaunit.assert_equals(screen(), "H01")

    ui.enc(3, 1)
    luaunit.assert_true(editor.dirty)
    local applied = c.voicing.mode
    tap(2)
    luaunit.assert_equals(screen(), "H01")
    luaunit.assert_false(editor.dirty)
    luaunit.assert_equals(c.voicing.mode, applied)
    luaunit.assert_equals(channel_page(), 8)
  end)
end

function test_ui_live_merge_child_route_k3_opens_the_translated_screen_and_k2_returns()
  live.isolated(function()
    local c = program.get_selected_channel()
    c.selected_patterns = c.selected_patterns or {}
    c.selected_patterns[1] = true
    local editor = owners().feature_editors.merge
    open_task("merge_shape")
    luaunit.assert_equals(screen(), "M02")
    luaunit.assert_equals(editor:get_screen(), "M01")

    choose_task("rhythm")
    tap(3)
    luaunit.assert_equals(screen(), "M03")
    luaunit.assert_equals(editor:get_screen(), "M02")
    luaunit.assert_equals(channel_page(), 7)

    tap(2)
    luaunit.assert_equals(screen(), "M02")
    luaunit.assert_equals(editor:get_screen(), "M01")
    luaunit.assert_nil(c.musical_merge)
  end)
end

function test_ui_live_merge_child_k2_with_a_draft_cancels_it_and_returns()
  live.isolated(function()
    local c = program.get_selected_channel()
    c.selected_patterns = c.selected_patterns or {}
    c.selected_patterns[1] = true
    local editor = owners().feature_editors.merge
    open_task("merge_shape")
    choose_task("rhythm")
    tap(3)
    luaunit.assert_equals(screen(), "M03")
    ui.enc(3, 1)
    luaunit.assert_true(editor.dirty)

    tap(2)
    luaunit.assert_equals(screen(), "M02")
    luaunit.assert_equals(editor:get_screen(), "M01")
    luaunit.assert_false(editor.dirty)
    luaunit.assert_nil(c.musical_merge)
  end)
end

function test_ui_live_harmony_child_route_k3_opens_register_and_k2_returns()
  live.isolated(function()
    local editor = owners().feature_editors.harmony
    open_task("harmony")
    choose_task("register")
    tap(3)
    luaunit.assert_equals(screen(), "H02")
    luaunit.assert_equals(editor:get_screen(), "H02")
    luaunit.assert_equals(channel_page(), 8)

    tap(2)
    luaunit.assert_equals(screen(), "H01")
    luaunit.assert_equals(editor:get_screen(), "H01")
  end)
end

-- Grid outcomes (page buttons) --------------------------------------------------------------

local function press_page(page, flow_id, extra)
  program.set_selected_page(page) -- the grid handler has already run
  ui_live.grid_outcome(flow_id, extra)
end

function test_ui_live_grid_page_buttons_set_context_and_screen()
  live.isolated(function()
    local p = pages.pages
    press_page(p.scale_edit_page, "G02")
    luaunit.assert_equals(ui_live.state().context, "Scale")
    luaunit.assert_equals(screen(), "S01")
    luaunit.assert_equals(scale_edit_page_ui.adapter_owners().pages:get_selected_page(), 1)

    press_page(p.trigger_edit_page, "G03")
    luaunit.assert_equals(ui_live.state().context, "Trig")
    luaunit.assert_equals(screen(), "P01")

    press_page(p.song_edit_page, "G04")
    luaunit.assert_equals(ui_live.state().context, "Song")
    luaunit.assert_equals(screen(), "A03")

    press_page(p.channel_edit_page, "G01")
    luaunit.assert_equals(ui_live.state().context, "Channel")
    luaunit.assert_equals(screen(), "C01")
    luaunit.assert_equals(channel_page(), 1)
  end)
end

function test_ui_live_grid_g03_cycle_reaches_p03_and_p04_and_back_to_p01()
  live.isolated(function()
    local p = pages.pages
    press_page(p.trigger_edit_page, "G03")
    luaunit.assert_equals(screen(), "P01")
    press_page(p.note_edit_page, "G03")
    luaunit.assert_equals(ui_live.state().context, "Note")
    luaunit.assert_equals(screen(), "P03")
    press_page(p.velocity_edit_page, "G03")
    luaunit.assert_equals(ui_live.state().context, "Velocity")
    luaunit.assert_equals(screen(), "P04")
    press_page(p.trigger_edit_page, "G03")
    luaunit.assert_equals(ui_live.state().context, "Trig")
    luaunit.assert_equals(screen(), "P01")
  end)
end

function test_ui_live_grid_g01_returns_to_the_remembered_parameters_family()
  live.isolated(function()
    local p = pages.pages
    ui.enc(1, 1)
    luaunit.assert_equals(screen(), "C02")
    press_page(p.scale_edit_page, "G02")
    luaunit.assert_equals(screen(), "S01")
    press_page(p.channel_edit_page, "G01")
    luaunit.assert_equals(ui_live.state().context, "Channel")
    luaunit.assert_equals(screen(), "C02")
    luaunit.assert_equals(channel_page(), 2)
  end)
end

-- Clock and device: save_confirm ---------------------------------------------------------------

function test_ui_live_clock_k2_cancels_and_k3_applies_through_save_confirm()
  live.isolated(function(env)
    local c = program.get_selected_channel()
    open_task("clock")
    luaunit.assert_equals(screen(), "C04")
    local active = c.clock_mods and c.clock_mods.name

    ui.enc(3, 1)
    luaunit.assert_true(save_confirm.has_pending())
    luaunit.assert_equals(c.clock_mods and c.clock_mods.name, active)
    tap(2)
    luaunit.assert_false(save_confirm.has_pending())
    luaunit.assert_equals(c.clock_mods and c.clock_mods.name, active)
    luaunit.assert_equals(screen(), "C04")

    ui.enc(3, 1)
    luaunit.assert_true(save_confirm.has_pending())
    tap(3)
    luaunit.assert_false(save_confirm.has_pending())
    luaunit.assert_not_equals(c.clock_mods and c.clock_mods.name, active)
    luaunit.assert_equals(screen(), "C04")
    luaunit.assert_equals(channel_page(), 4)
  end)
end

function test_ui_live_device_k2_cancels_and_k3_applies_through_save_confirm()
  live.isolated(function()
    local selected = program.get()
    local number = selected.selected_channel
    local function routing()
      local d = selected.devices[number]
      return {d.device_map, d.midi_channel, d.midi_device}
    end
    open_task("device")
    luaunit.assert_equals(screen(), "C05")
    local before = routing()

    ui.enc(3, 1)
    luaunit.assert_true(save_confirm.has_pending())
    luaunit.assert_equals(routing(), before)
    tap(2)
    luaunit.assert_false(save_confirm.has_pending())
    luaunit.assert_equals(routing(), before)
    luaunit.assert_equals(screen(), "C05")

    ui.enc(3, 1)
    luaunit.assert_true(save_confirm.has_pending())
    tap(3)
    luaunit.assert_false(save_confirm.has_pending())
    luaunit.assert_not_equals(routing(), before)
    luaunit.assert_equals(screen(), "C05")
    luaunit.assert_equals(channel_page(), 5)
  end)
end

-- Failure containment ----------------------------------------------------------------------

local function capture_print(body)
  local lines = {}
  local real = print
  print = function(...)
    local parts = {}
    for i = 1, select("#", ...) do parts[#parts + 1] = tostring(select(i, ...)) end
    lines[#lines + 1] = table.concat(parts, " ")
  end
  local ok, err = pcall(body)
  print = real
  if not ok then error(err, 0) end
  return lines
end

function test_ui_live_unknown_grid_flow_logs_and_leaves_state_consistent()
  live.isolated(function()
    ui.enc(1, 1)
    local lines = capture_print(function() ui_live.grid_outcome("G99") end)
    luaunit.assert_equals(screen(), "C02")
    luaunit.assert_equals(ui_live.state().context, "Channel")
    luaunit.assert_equals(channel_page(), 2)
    luaunit.assert_true(#lines > 0)
    luaunit.assert_not_nil(lines[1]:match("^ui_live: "))
    -- The UI still works afterwards.
    ui.enc(1, -1)
    luaunit.assert_equals(screen(), "C01")
  end)
end

function test_ui_live_failing_owner_hook_logs_and_leaves_state_consistent()
  live.isolated(function()
    local handlers = owners().mask_handlers
    local real = handlers.handle_note_mask_change
    handlers.handle_note_mask_change = function() error("owner exploded") end
    local lines = capture_print(function() ui.enc(3, 1) end)
    handlers.handle_note_mask_change = real
    luaunit.assert_equals(screen(), "C01")
    luaunit.assert_equals(ui_live.state().field_id, "note")
    luaunit.assert_nil(program.get_selected_channel().note_mask)
    luaunit.assert_true(#lines > 0)
    luaunit.assert_not_nil(table.concat(lines, "\n"):match("owner exploded"))
    ui.enc(3, 1)
    luaunit.assert_not_nil(program.get_selected_channel().note_mask)
  end)
end

function test_ui_live_unknown_input_event_logs_and_keeps_the_screen()
  live.isolated(function()
    ui.enc(1, 1); ui.enc(1, 1)
    local lines = capture_print(function() ui.enc(7, 1) end)
    luaunit.assert_equals(screen(), "N01")
    luaunit.assert_equals(ui_live.state().context, "Channel")
    luaunit.assert_true(#lines > 0)
  end)
end

function test_ui_live_failing_descriptor_read_does_not_raise_out_of_ui_live()
  live.isolated(function()
    local selector = owners().mask_selectors.velocity
    selector.get_value = function() error("owner read exploded") end
    local ok = pcall(capture_print, function() ui.enc(1, 1) end)
    selector.get_value = nil -- the class method again
    luaunit.assert_true(ok, "an adapter describe error escaped ui_live.enc")
    luaunit.assert_equals(screen(), "C02")
  end)
end
