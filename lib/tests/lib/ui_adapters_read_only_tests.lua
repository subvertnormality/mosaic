-- Characterisation of the UI02 read_only provider (docs/ui-reimplementation
-- spec.json#/providers/read_only, #/field_contracts/viewer,
-- #/provider_protocol/read_only_snapshot). README.md: "On the Norns screen,
-- you'll find the channel grid visualizer. Use E2 to select the current
-- channel" (now E3 on View channel) and the Note Dashboard of the Channel page.
-- Everything else here pins current behaviour and is a characterisation
-- outside the manual.

local ui_adapters = include("mosaic/lib/ui_adapters")
local read_only_factory = include("mosaic/lib/ui_adapters/read_only")
local harness = include("mosaic/lib/tests/helpers/channel_adapter_harness")
local isolation = include("mosaic/lib/tests/helpers/ui_adapters_isolation")

local function target(route, extra)
  local t = {source_route = route, screen = route}
  for k, v in pairs(extra or {}) do t[k] = v end
  return t
end

local function values(outcome)
  local map = {}
  for _, d in ipairs(outcome.descriptors or {}) do map[d.id] = d.value end
  return map
end

local function ids(outcome)
  local out = {}
  for _, d in ipairs(outcome.descriptors or {}) do out[#out + 1] = d.id end
  return out
end

-- C06: the real Channel page and its Note Dashboard ---------------------------------

-- A fresh Channel page (channel_adapter_harness) on the Note Dashboard, with a
-- read_only adapter over its adapter_owners() and the real inspection module.
local function dashboard(body)
  harness.isolated(function(env)
    harness.start(env)
    env.owners = env.ui.adapter_owners()
    env.inspection = include("mosaic/lib/harmony/inspection")
    env.inspection.reset()
    env.adapter = read_only_factory(env.ui_adapters, {pages = {channel = env.owners}, inspection = env.inspection})
    env.song = program.get_selected_song_pattern()
    env.draw = function()
      local log = {}
      screen = isolation.screen(log)
      env.owners.channel_pages:select_page(env.owners.channel_page_to_index["Note Dashboard"])
      env.draws.channel_edit_page()
      return table.concat(log, "\n") .. "\n"
    end
    body(env)
  end)
end

function test_ui_adapters_read_only_c06_values_are_what_the_note_dashboard_draws()
  dashboard(function(env)
    env.ui.set_note_dashboard_values({note = 64, velocity = 96, length = 0.25, chords = {67, 0, 74}})
    local frame = env.draw()
    local outcome = env.adapter:describe("C06", "C06", target("C06"))
    luaunit.assert_true(outcome.ok)
    local v = values(outcome)
    local musicutil = require("musicutil")
    local voices = {musicutil.note_num_to_name(67, true), musicutil.note_num_to_name(0, true),
      musicutil.note_num_to_name(74, true), "X"}
    luaunit.assert_equals(v.root, musicutil.note_num_to_name(64, true))
    -- MIDI note 0 is a played voice; an unplayed slot is X (bugs.json dashboard-chord-slots)
    luaunit.assert_equals(v.chord, table.concat(voices, " "))
    luaunit.assert_equals(v.velocity, "96")
    luaunit.assert_equals(v.length, "0.25")
    for _, text in ipairs({v.root, v.velocity, v.length, voices[1], voices[2], voices[3], voices[4]}) do
      luaunit.assert_str_contains(frame, " " .. text .. "\n")
    end
  end)
end

function test_ui_adapters_read_only_c06_provenance_is_the_dashboard_line_from_one_snapshot()
  dashboard(function(env)
    env.inspection.plan(env.song, harness.SELECTED, {step = 5, source = 3, merge = 2, scale = 64, harmony = 64, output = 65})
    env.inspection.scheduled(env.song, harness.SELECTED, 65, "a")
    env.inspection.emitted(env.song, harness.SELECTED, 66, "a")
    local frame = env.draw()
    local v = values(env.adapter:describe("C06", "C06", target("C06")))
    luaunit.assert_equals(v.inspected_step, "STEP05")
    luaunit.assert_equals(v.provenance, "SRC3 M2 S64 H64")
    luaunit.assert_equals(v.planned_pitch, "65")
    luaunit.assert_equals(v.scheduled_pitch, "65")
    luaunit.assert_equals(v.emitted_pitch, "66")
    luaunit.assert_equals(v.bypass, "NONE")
    luaunit.assert_str_contains(frame, v.provenance)
    luaunit.assert_str_contains(frame, "P" .. v.planned_pitch .. " S" .. v.scheduled_pitch .. " E" .. v.emitted_pitch)
  end)
end

function test_ui_adapters_read_only_c06_held_step_inspects_that_step_not_the_latest()
  dashboard(function(env)
    env.inspection.plan(env.song, harness.SELECTED, {step = 5, source = 1, output = 60})
    env.inspection.plan(env.song, harness.SELECTED, {step = 6, source = 2, output = 62, bypass = "muted"})
    local latest = values(env.adapter:describe("C06", "C06", target("C06")))
    luaunit.assert_equals(latest.inspected_step, "STEP06")
    luaunit.assert_equals(latest.bypass, "muted")
    env.pressed = {{5, 4}}
    local held = values(env.adapter:describe("C06", "C06", target("C06")))
    luaunit.assert_equals(held.inspected_step, "STEP05")
    luaunit.assert_equals(held.planned_pitch, "60")
    luaunit.assert_equals(held.scheduled_pitch, "-")
    luaunit.assert_equals(held.bypass, "NONE")
    luaunit.assert_str_contains(env.draw(), "P60 S- E-")
  end)
end

function test_ui_adapters_read_only_c06_reads_no_event_when_the_inspection_is_empty()
  dashboard(function(env)
    local v = values(env.adapter:describe("C06", "C06", target("C06")))
    for _, id in ipairs({"inspected_step", "provenance", "planned_pitch", "scheduled_pitch", "emitted_pitch", "bypass"}) do
      luaunit.assert_equals(v[id], "NO EVENT", id)
    end
    luaunit.assert_equals(v.chord, "X X X X")
    luaunit.assert_equals(ids(env.adapter:describe("C06", "C06", target("C06"))), ui_adapters.spec.screens.C06.fields)
  end)
end

function test_ui_adapters_read_only_c06_takes_one_snapshot_per_describe_and_marks_mixed_stages_stale()
  dashboard(function(env)
    local calls = 0
    local fake = {snapshot = function()
      calls = calls + 1
      return {planned = {event_id = 4, step = 2, output = 60}, scheduled = {event_id = 3, pitch = 59},
        emitted = {event_id = 4, pitch = 60}}
    end}
    local adapter = read_only_factory(env.ui_adapters, {pages = {channel = env.owners}, inspection = fake})
    local v = values(adapter:describe("C06", "C06", target("C06")))
    luaunit.assert_equals(calls, 1)
    luaunit.assert_equals(v.scheduled_pitch, "STALE")
    luaunit.assert_equals(v.emitted_pitch, "60")
  end)
end

-- Program-backed screens -------------------------------------------------------------

local function sequencer_stub() return {new = function() return {draw = function() end} end} end

-- Real program state; fresh note/velocity/trig/scale/song viewers from the page UIs.
local function model_env(body)
  local env = {pressed = {}, params = {song_mode = 2, record = 1}, playing = false, algorithm = 1}
  isolation.isolated({
    sequencer = sequencer_stub(),
    m_grid = {get_pressed_keys = function() return env.pressed end},
    m_clock = {is_playing = function() return env.playing end, get_clock_divisions = function() return {} end},
    tooltip = {show = function() end},
    draw = {register_ui = function() end},
  }, function()
    program.init()
    env.params_owner = {get = function(_, id) return env.params[id] end}
    env.trig_page = {get_algorithm = function() return env.algorithm end}
    env.pages = {
      note = include("mosaic/lib/pages/note_edit_page/note_edit_page_ui"),
      velocity = include("mosaic/lib/pages/velocity_edit_page/velocity_edit_page_ui"),
      trig = include("mosaic/lib/pages/trigger_edit_page/trigger_edit_page_ui")
    }
    local owner_pages = {}
    for key, ui in pairs(env.pages) do owner_pages[key] = ui.adapter_owners() end
    owner_pages.scale = {grid_viewer = include("mosaic/lib/ui_components/grid_viewer"):new(0, 3)}
    owner_pages.song = {grid_viewer = include("mosaic/lib/ui_components/grid_viewer"):new(0, 3)}
    env.owner_pages = owner_pages
    env.inspection = include("mosaic/lib/harmony/inspection")
    env.inspection.reset()
    env.adapter = read_only_factory(ui_adapters, {pages = owner_pages, params = env.params_owner,
      trigger_edit_page = env.trig_page, inspection = env.inspection, step = step or include("mosaic/lib/step"),
      device_map = {get_device = function(id) return {name = "Dev " .. id} end}})
    body(env)
  end)
end

local VIEW_CONTEXT = {P01 = "Trig", P03 = "Note", P04 = "Velocity", S03 = "Scale", P05 = "Trig"}

function test_ui_adapters_read_only_every_screen_field_id_is_described()
  model_env(function(env)
    env.pressed = {{5, 4}}
    for id, screen in pairs(ui_adapters.spec.screens) do
      -- C06 needs the Channel page's Note Dashboard owners (covered above).
      if screen.provider == "read_only" and id ~= "C06" then
        local outcome = env.adapter:describe(id, screen.existing_route, target(screen.existing_route, {context = VIEW_CONTEXT[id]}))
        luaunit.assert_true(outcome.ok, id .. " " .. tostring(outcome.code))
        luaunit.assert_equals(ids(outcome), screen.fields, id)
      end
    end
    for _, id in ipairs({"F02", "F03", "F04", "F05", "F07"}) do
      local outcome = env.adapter:describe(id, "snapshot:" .. id, target("snapshot:" .. id))
      luaunit.assert_true(outcome.ok, id)
      luaunit.assert_equals(ids(outcome), ui_adapters.spec.screens[id].fields, id)
    end
  end)
end

function test_ui_adapters_read_only_describe_never_mutates_or_draws_randomness()
  model_env(function(env)
    env.pressed = {{5, 4}, {7, 6}}
    -- song_transition.calculate_next_selected_song_pattern (A03) goes through
    -- program.get_repeat_count(), which writes its default of 1 on first read.
    -- Playback reads it every step, so a running program always has it.
    program.set_repeat_count(1)
    -- Likewise the selected song pattern is created by its accessor on first
    -- read (every page draw reads it); start from a created one.
    program.get_selected_song_pattern()
    local function serialise(value, seen)
      if type(value) ~= "table" then return tostring(value) end
      seen = seen or {}
      if seen[value] then return "<cycle>" end
      seen[value] = true
      local keys = {}
      for k in pairs(value) do keys[#keys + 1] = k end
      table.sort(keys, function(a, b) return tostring(a) < tostring(b) end)
      local parts = {}
      for _, k in ipairs(keys) do parts[#parts + 1] = tostring(k) .. "=" .. serialise(value[k], seen) end
      seen[value] = nil
      return "{" .. table.concat(parts, ",") .. "}"
    end
    local before = serialise(program.get())
    local random = math.random
    math.random = function() error("read_only consumed RNG") end
    local ok, err = pcall(function()
      for id, screen in pairs(ui_adapters.spec.screens) do
        if screen.provider == "read_only" and id ~= "C06" then
          env.adapter:describe(id, screen.existing_route, target(screen.existing_route, {context = VIEW_CONTEXT[id]}))
        end
      end
    end)
    math.random = random
    luaunit.assert_true(ok, tostring(err))
    luaunit.assert_true(serialise(program.get()) == before, "describe changed program state")
  end)
end

function test_ui_adapters_read_only_program_screens_read_the_model()
  model_env(function(env)
    local data = program.get()
    local channel = program.get_selected_channel()
    channel.selected_patterns = {[1] = true, [3] = true}
    channel.trig_merge_mode = "only"
    channel.note_mask = 64
    data.devices[channel.number].device_map = "fixed"
    local c09 = values(env.adapter:describe("C09", "C09", target("C09")))
    luaunit.assert_equals(c09.patterns, "01 03")
    luaunit.assert_equals(c09.trig_mode, "ONLY")
    luaunit.assert_equals(c09.note_vel, "AVERAGE / AVERAGE")
    local f05 = values(env.adapter:describe("F05", "F05", target("F05")))
    luaunit.assert_equals(f05.patterns, "01 03")
    luaunit.assert_equals(f05.note_mask, require("musicutil").note_num_to_name(64, true))
    luaunit.assert_equals(f05.output, "NO EVENT")
    luaunit.assert_equals(f05.device, "Dev fixed")
    local pattern = program.get_selected_pattern()
    pattern.note_values[5], pattern.lengths[5], pattern.velocity_values[5], pattern.trig_values[5] = 2, 4, 0, 1
    env.pressed = {{5, 4}}
    local p03 = values(env.adapter:describe("P03", "P03", target("P03")))
    luaunit.assert_equals(p03.relative_note, "+2")
    luaunit.assert_equals(p03.length, "4 steps")
    luaunit.assert_equals(p03.in_ch02, "NO EVENT")
    local p04 = values(env.adapter:describe("P04", "P04", target("P04")))
    luaunit.assert_equals(p04.velocity, "0")
    luaunit.assert_equals(p04.used_by, "CH01")
    local p08 = values(env.adapter:describe("P08", "P08", target("P08")))
    luaunit.assert_equals(p08.toggle, "STEP05 ON")
    luaunit.assert_equals(p08.length, "05..08")
    luaunit.assert_equals(p08.pattern_select, "PAT01")
    local p01 = values(env.adapter:describe("P01", "P01", target("P01")))
    luaunit.assert_equals(p01.focus_01_16, "STEP05")
    luaunit.assert_equals(p01.focus_17_32, "NONE")
    local a03 = values(env.adapter:describe("A03", "A03", target("A03")))
    luaunit.assert_equals(a03.automatic, "01 > 01")
    luaunit.assert_equals(a03.manual, "NONE")
    env.params.song_mode = 1
    luaunit.assert_equals(values(env.adapter:describe("A03", "A03", target("A03"))).manual, "01 HOLD")
    local s03 = values(env.adapter:describe("S03", "S03", target("S03")))
    luaunit.assert_equals(s03.edit_scale, "01")
    luaunit.assert_equals(s03.transpose, "0")
    local p06 = env.adapter:describe("P06", "P06", target("P06"))
    luaunit.assert_true(p06.descriptors[1].selected)
    luaunit.assert_false(p06.descriptors[2].selected)
  end)
end

-- field_contracts.viewer ----------------------------------------------------------

local function viewer_parity(context, page_key, route)
  local old, new
  model_env(function(env)
    env.pages[page_key].enc(2, 3)
    env.pages[page_key].enc(2, -1)
    old = {view = env.owner_pages[page_key].grid_viewer.selected_channel, selected = program.get().selected_channel}
  end)
  model_env(function(env)
    local t = target(route, {context = context})
    luaunit.assert_true(env.adapter:edit("view_channel", 3, t).ok)
    luaunit.assert_true(env.adapter:edit("view_channel", -1, t).ok)
    new = {view = env.owner_pages[page_key].grid_viewer.selected_channel, selected = program.get().selected_channel}
    luaunit.assert_equals(values(env.adapter:describe(route, route, t)).view_channel, "03")
  end)
  luaunit.assert_equals(new, old)
  luaunit.assert_equals(old, {view = 3, selected = 1})
end

function test_ui_adapters_read_only_view_channel_e3_matches_the_old_note_e2()
  viewer_parity("Note", "note", "P03")
end

function test_ui_adapters_read_only_view_channel_e3_matches_the_old_velocity_e2()
  viewer_parity("Velocity", "velocity", "P04")
end

function test_ui_adapters_read_only_view_channel_e3_matches_the_old_trig_e2()
  viewer_parity("Trig", "trig", "P01")
end

function test_ui_adapters_read_only_view_channel_clamps_and_p05_moves_its_own_context_viewer()
  model_env(function(env)
    local t = target("P05", {context = "Song"})
    env.adapter:edit("view_channel", 40, t)
    luaunit.assert_equals(env.owner_pages.song.grid_viewer.selected_channel, 16)
    luaunit.assert_equals(env.owner_pages.scale.grid_viewer.selected_channel, 1)
    env.adapter:edit("view_channel", -40, t)
    luaunit.assert_equals(env.owner_pages.song.grid_viewer.selected_channel, 1)
    luaunit.assert_equals(program.get().selected_channel, 1)
    local missing = env.adapter:describe("P05", "P05", target("P05"))
    luaunit.assert_false(missing.ok)
    luaunit.assert_equals(missing.code, "missing_context")
  end)
end

function test_ui_adapters_read_only_doctor_owns_the_trig_encoders_on_algorithm_five()
  model_env(function(env)
    env.algorithm = 5
    local t = target("P01")
    local d = env.adapter:describe("P01", "P01", t).descriptors[1]
    luaunit.assert_equals(d.id, "view_channel")
    luaunit.assert_false(d.enabled)
    local outcome = env.adapter:edit("view_channel", 1, t)
    luaunit.assert_equals(outcome.code, "disabled")
    luaunit.assert_equals(env.owner_pages.trig.grid_viewer.selected_channel, 1)
  end)
end

-- Protocol ------------------------------------------------------------------------

function test_ui_adapters_read_only_rejects_foreign_routes_stale_generation_and_readonly_edits()
  model_env(function(env)
    for _, route in ipairs({"N01", "snapshot:C06", "C01"}) do
      local outcome = env.adapter:describe(route, route, target(route))
      luaunit.assert_false(outcome.ok, route)
      luaunit.assert_equals(outcome.code, "foreign_route")
      luaunit.assert_nil(outcome.descriptors)
    end
    local stale = env.adapter:edit("view_channel", 1, target("P03"), 9)
    luaunit.assert_equals(stale.code, "stale_generation")
    luaunit.assert_equals(env.owner_pages.note.grid_viewer.selected_channel, 1)
    luaunit.assert_equals(env.adapter:edit("relative_note", 1, target("P03")).code, "wrong_kind")
    luaunit.assert_equals(env.adapter:edit("queued_rate", 1, target("F02")).code, "disabled")
  end)
end

function test_ui_adapters_read_only_snapshot_is_immutable_and_flags_a_moved_event()
  model_env(function(env)
    local song = program.get_selected_song_pattern()
    local empty = env.adapter:snapshot(target("C06"))
    luaunit.assert_equals(empty.status, "NO EVENT")
    env.inspection.plan(song, 1, {step = 3, output = 60})
    local snap = env.adapter:snapshot(target("C06"))
    luaunit.assert_equals(snap.event_id, 1)
    snap.snapshot.planned.output = 99
    luaunit.assert_equals(env.adapter:snapshot(target("C06")).snapshot.planned.output, 60)
    env.inspection.plan(song, 1, {step = 4, output = 62})
    luaunit.assert_true(env.adapter:snapshot(target("C06"), 1).stale)
  end)
end
