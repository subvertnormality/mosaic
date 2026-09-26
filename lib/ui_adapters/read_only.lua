-- Read-only provider (docs/ui-reimplementation spec.json#/providers/read_only, UI02).
--
-- Describes the status/inspection screens from the model sources the existing
-- pages already read. Nothing here writes music state, runs a solver or draws
-- a random value. The only edit is view_channel (field_contracts.viewer): E3
-- calls the page's own grid_viewer:next_channel()/prev_channel() and never
-- writes program.selected_channel.
--
-- Each describe() takes ONE capture: the selected song/channel, the held grid
-- step (rows 4..7) and one lib/harmony/inspection snapshot. Every descriptor
-- of that describe reads that capture, so stages from different event ids are
-- never mixed (a stage whose event id differs from the plan reads STALE), and
-- an empty inspection reads NO EVENT.
--
-- owners (every entry optional; each defaults to the global the page reads):
--   pages = {channel=, trig=, note=, velocity=, scale=, song=}
--     each is that page UI's adapter_owners() table, or a function returning
--     it. Used: channel.note_displays (C06 Note Dashboard selectors) and
--     <page>.grid_viewer (view_channel). Default: <page>_edit_page_ui.adapter_owners().
--   program, m_grid, m_clock, params, step, device_map, trigger_edit_page
--   inspection   lib/harmony/inspection (default: include()).
--
-- target fields read: context (P05 and snapshot routes: which grid context
-- owns the viewer: Trig, Note, Velocity, Scale or Song).
local musicutil = require("musicutil")

return function(ui_adapters, owners)
  owners = owners or {}

  local PAGE_GLOBALS = {channel = "channel_edit_page_ui", trig = "trigger_edit_page_ui", note = "note_edit_page_ui",
    velocity = "velocity_edit_page_ui", scale = "scale_edit_page_ui", song = "song_edit_page_ui"}
  local CONTEXT_PAGE = {Trig = "trig", Note = "note", Velocity = "velocity", Scale = "scale", Song = "song"}

  local function src(name)
    if owners[name] ~= nil then return owners[name] end
    return _ENV[name]
  end

  local inspection = owners.inspection or include("mosaic/lib/harmony/inspection")

  local function page(key)
    local value = owners.pages and owners.pages[key]
    if type(value) == "function" then return value() end
    if value ~= nil then return value end
    local ui = _ENV[PAGE_GLOBALS[key]]
    return ui and ui.adapter_owners and ui.adapter_owners() or nil
  end

  -- Formatting --------------------------------------------------------------

  local function two(n) return string.format("%02d", n) end
  local function step_label(s) return "STEP" .. two(s) end
  local function note_name(v) return musicutil.note_num_to_name(v, true) end
  local function signed(v) return v > 0 and ("+" .. v) or tostring(v) end
  local function yes_no(v) return v and "YES" or "NO" end

  local function pattern_list(channel)
    local numbers = {}
    for i = 1, 16 do
      if channel and channel.selected_patterns and channel.selected_patterns[i] then numbers[#numbers + 1] = two(i) end
    end
    return #numbers > 0 and table.concat(numbers, " ") or "NONE", numbers
  end

  local function playing()
    local clock = src("m_clock")
    return clock and clock.is_playing and clock.is_playing() or false
  end

  local function transport() return playing() and "PLAYING" or "STOPPED" end

  local function unavailable(id, label, reason)
    return {id = id, label = label, kind = "unavailable", value = "NONE", enabled = false,
      domain = {reason = reason or "no_owner_source"}}
  end

  local function readonly(id, label, value, domain)
    return {id = id, label = label, kind = "readonly", value = value, domain = domain}
  end

  -- Capture: one per describe --------------------------------------------------

  local function held_steps()
    local grid = src("m_grid")
    local keys = grid and grid.get_pressed_keys and grid.get_pressed_keys() or {}
    local steps = {}
    -- The page's own step layout when the grid owner knows it (note/velocity
    -- faders address the page shown); a key in rows 4..7 keeps its position.
    if grid and grid.held_steps then
      for _, step in ipairs(grid.held_steps()) do
        local entry = {step = step}
        for _, key in ipairs(keys) do
          if key[2] >= 4 and key[2] <= 7 and fn.calc_grid_count(key[1], key[2]) == step then entry.x, entry.y = key[1], key[2] end
        end
        steps[#steps + 1] = entry
      end
      return steps
    end
    for _, key in ipairs(keys) do
      if key[2] >= 4 and key[2] <= 7 then steps[#steps + 1] = {step = fn.calc_grid_count(key[1], key[2]), x = key[1], y = key[2]} end
    end
    return steps
  end

  -- The Note Dashboard's own inspection: first held step in rows 4..7, else
  -- the latest event, of the selected channel in the selected song pattern.
  local function capture(channel_number)
    local program = src("program")
    local held = held_steps()
    local song = program.get_selected_song_pattern()
    local number = channel_number or program.get().selected_channel
    local inspected = held[1] and held[1].step or nil
    return {song = song, channel_number = number, held = held, inspected_step = inspected,
      snapshot = inspection.snapshot(song, number, inspected)}
  end

  local function stage_pitch(snapshot, stage)
    local planned = snapshot.planned
    if not stage then return "-" end
    if planned and stage.event_id ~= nil and stage.event_id ~= planned.event_id then return "STALE" end
    return tostring(stage.pitch or "-")
  end

  -- Viewer (field_contracts.viewer) ------------------------------------------------

  local function viewer_for(context)
    local key = CONTEXT_PAGE[context]
    local owner = key and page(key)
    return owner and owner.grid_viewer or nil
  end

  local function doctor_owns_encoders(context)
    if context ~= "Trig" then return false end
    local trig = src("trigger_edit_page")
    return trig ~= nil and trig.get_algorithm ~= nil and trig.get_algorithm() == 5
  end

  local function view_channel(context)
    local viewer = viewer_for(context)
    if not viewer then return nil end
    return {id = "view_channel", label = "View channel", kind = "inspection", value = two(viewer.selected_channel),
      enabled = not doctor_owns_encoders(context),
      domain = {min = 1, max = 16, step = 1, context = context, channel = viewer.selected_channel},
      edit = function(delta)
        for _ = 1, math.abs(delta) do
          if delta > 0 then viewer:next_channel() else viewer:prev_channel() end
        end
        return viewer.selected_channel
      end}
  end

  local function viewed_channel(context)
    local viewer = viewer_for(context)
    local program = src("program")
    if not viewer then return nil end
    return program.get_channel(program.get().selected_song_pattern, viewer.selected_channel), viewer.selected_channel
  end

  -- Readers, one per screen ----------------------------------------------------------

  local readers = {}

  -- C06: the Note Dashboard's value selectors, shown exactly as value_selector:draw
  -- shows them, and the held-step provenance line from the capture.
  function readers.C06(_, cap)
    local displays = (page("channel") or {}).note_displays
    if not displays then return nil, "no_owner" end
    local function shown(selector)
      if selector.value then return tostring(selector.view_transform_func(selector.value)) end
      return "0"
    end
    local voices, raw = {}, {}
    for i = 1, 4 do voices[i] = shown(displays.chords[i]); raw[i] = displays.chords[i].value end
    local snap = cap.snapshot
    local planned = snap.planned
    -- The note and only the chord voices that play (an unplayed slot shows X).
    local played = {shown(displays.note)}
    for i = 1, 4 do if voices[i] ~= "X" then played[#played + 1] = voices[i] end end
    local provenance = {event_id = planned and planned.event_id, held = cap.inspected_step ~= nil}
    local step = cap.inspected_step or (planned and planned.step)
    local descriptors = {
      readonly("note", "Note", table.concat(played, " "), {raw = displays.note.value, voices = voices, chord_raw = raw}),
      readonly("vel_len", "Vel / Len", shown(displays.velocity) .. " / " .. shown(displays.length),
        {velocity = displays.velocity.value, length = displays.length.value}),
      readonly("step", "Step", step and (step_label(step) .. (provenance.held and " HELD" or "")) or "NO EVENT",
        {step = step, held = provenance.held, event_id = provenance.event_id}),
    }
    if not planned then
      -- Nothing has played: the owner's default note (C-2) is not an event.
      descriptors[1].value, descriptors[2].value = "NO EVENT", "NO EVENT"
      for _, f in ipairs({{"degree", "Degree"}, {"pitch", "Pitch"}, {"sent", "Sent"}}) do
        descriptors[#descriptors + 1] = readonly(f[1], f[2], "NO EVENT", provenance)
      end
      return descriptors
    end
    -- How the note got its pitch, in the player's terms: the pattern degree
    -- (and what merging made of it), the pitch in the scale (and the harmony's
    -- pitch when it moved it), and the note actually sent.
    local function degree(v) return v and signed(v) or "-" end
    local degree_text = degree(planned.source)
    if planned.merge ~= nil and planned.merge ~= planned.source then degree_text = degree_text .. " > " .. degree(planned.merge) .. " MERGED" end
    local pitch_text = planned.scale and note_name(planned.scale) or "-"
    if planned.harmony and planned.scale and planned.harmony ~= planned.scale then
      pitch_text = pitch_text .. " > " .. note_name(planned.harmony) .. " HARMONY"
    end
    local SILENT = {muted = "MUTED", rest = "REST", missing_output = "NO OUTPUT"}
    local sent
    if SILENT[planned.bypass or ""] then
      sent = SILENT[planned.bypass]
    elseif snap.emitted and snap.emitted.pitch and (snap.emitted.event_id == nil or snap.emitted.event_id == planned.event_id) then
      sent = note_name(snap.emitted.pitch)
    else
      sent = "NOT YET"
    end
    descriptors[#descriptors + 1] = readonly("degree", "Degree", degree_text,
      {source = planned.source, merge = planned.merge, event_id = planned.event_id})
    descriptors[#descriptors + 1] = readonly("pitch", "Pitch", pitch_text,
      {scale = planned.scale, harmony = planned.harmony, output = planned.output, event_id = planned.event_id,
        scheduled = stage_pitch(snap, snap.scheduled), bypass = planned.bypass})
    descriptors[#descriptors + 1] = readonly("sent", "Sent", sent,
      {emitted = snap.emitted and snap.emitted.pitch, bypass = planned.bypass, event_id = planned.event_id})
    return descriptors
  end

  -- C08: the source stages of the same inspected event.
  function readers.C08(_, cap)
    local program = src("program")
    local channel = program.get_selected_channel()
    local snap = cap.snapshot
    local planned = snap.planned
    if not planned then
      return {readonly("pattern_note", "Pattern note", "NO EVENT"), readonly("note_mask", "Note mask", "NO EVENT"),
        readonly("quantiser", "Quantiser", "NO EVENT"), readonly("result", "Result", "NO EVENT")}
    end
    local id = {event_id = planned.event_id, step = planned.step}
    local mask = planned.step and channel.step_note_masks and channel.step_note_masks[planned.step]
    if mask == nil then mask = channel.note_mask end
    local emitted = snap.emitted
    local result
    if emitted and emitted.event_id == planned.event_id and emitted.pitch then
      result = note_name(emitted.pitch) .. " " .. emitted.pitch
    elseif emitted then result = "STALE" else result = "NOT PLAYED" end
    return {
      -- Stored pattern data is a relative degree, never labelled as a note.
      readonly("pattern_note", "Pattern note", tostring(planned.source or "NONE"), id),
      readonly("note_mask", "Note mask", (mask == nil or mask == -1) and "NONE" or note_name(mask), {raw = mask}),
      readonly("quantiser", "Quantiser", planned.bypass and "BYPASSED" or
        (planned.scale and (note_name(planned.scale) .. " " .. planned.scale) or "NONE"), id),
      readonly("result", "Result", result, id)
    }
  end

  -- C09: the selected channel's legacy merge modes, as stored.
  -- Merge modes as the manual names them: SKIP, AVERAGE, PAT 3 (never an engine id).
  local function merge_mode(mode)
    if mode == nil then return "NONE" end
    local number = tostring(mode):match("^pattern_number_(%d+)$")
    if number then return "PAT " .. number end
    return (tostring(mode):gsub("_", " "):upper())
  end

  -- The modes each merge button cycles, then the held button + pattern modes.
  local MERGE_OPTIONS = {trig = {"skip", "only", "all"}}
  do
    local shaped = {"average", "up", "down"}
    for n = 1, 16 do shaped[#shaped + 1] = "pattern_number_" .. n end
    MERGE_OPTIONS.note, MERGE_OPTIONS.velocity, MERGE_OPTIONS.length = shaped, shaped, shaped
  end

  -- A merge mode row: E3 steps through the modes the grid can set (clamped),
  -- and the channel page applies it as its merge button does.
  local function merge_mode_field(channel, kind, id, label)
    local options, current = MERGE_OPTIONS[kind], channel[kind .. "_merge_mode"]
    local index = 1
    for k, option in ipairs(options) do if option == current then index = k end end
    -- Merge Shape (Foundation) decides the trigs: the saved trig merge mode is
    -- kept for when it is off, and the row says which is in charge.
    local shown = merge_mode(current)
    if kind == "trig" and channel.musical_merge and channel.musical_merge.mode == "foundation" then
      shown = "SHAPE (" .. shown .. ")"
    end
    return {id = id, label = label, kind = "value", value = shown,
      domain = {raw = current, min = 1, max = #options, index = index},
      edit = function(delta)
        local owner = src("channel_edit_page")
        if not (owner and owner.set_merge_mode) then return nil end
        local step = math.max(1, math.min(#options, index + (delta > 0 and 1 or -1)))
        if step ~= index then owner.set_merge_mode(kind, options[step]) end
        return merge_mode(options[step])
      end}
  end

  function readers.C09()
    local channel = src("program").get_selected_channel()
    local patterns, numbers = pattern_list(channel)
    return {
      -- Patterns are assigned on the grid's pattern row.
      readonly("patterns", "Patterns", patterns, {patterns = numbers}),
      merge_mode_field(channel, "trig", "trig_mode", "Trig mode"),
      merge_mode_field(channel, "note", "note_mode", "Note mode"),
      merge_mode_field(channel, "velocity", "velocity_mode", "Velocity mode"),
      merge_mode_field(channel, "length", "length_mode", "Length mode")
    }
  end

  local function scale_number(n)
    if n == nil then return "NONE" end
    if n == 0 then return "OFF" end
    return two(n)
  end

  -- S03: the global scale track (channel 17). Last applied numbers only; the
  -- mutating scale resolver is never called.
  function readers.S03(_, cap)
    local program = src("program")
    local data = program.get()
    local track = program.get_channel(data.selected_song_pattern, 17)
    local current = program.get_current_step_for_channel(17)
    local first, last = program.get_channel_step_bounds(track)
    return {
      readonly("playing_scale", "Playing scale", scale_number(program.get_channel_step_scale_number(17))),
      readonly("edit_scale", "Edit scale", scale_number(data.selected_scale)),
      readonly("step_range", "Step / range", (current and two(current) or "NONE") .. " / " .. two(first) .. ".." .. two(last),
        {step = current, first = first, last = last}),
      readonly("transpose", "Transpose", signed(program.get_transpose())),
      -- A held scale-track step's own scale lock (G34), else NONE.
      readonly("step_lock", "Step lock", cap.inspected_step and
        (step_label(cap.inspected_step) .. " " .. scale_number(program.get_step_scale_trig_lock(track, cap.inspected_step)))
        or "NONE", {step = cap.inspected_step})
    }
  end

  -- S04: scale precedence for the selected channel (channel lock > global lock >
  -- default), read without running step.calculate_step_scale_number.
  function readers.S04()
    local program, step = src("program"), src("step")
    local data = program.get()
    local channel = program.get_selected_channel()
    local track = program.get_channel(data.selected_song_pattern, 17)
    local channel_lock = step and step.get_local_scale_override and step.get_local_scale_override(channel.number) or nil
    local global_lock = program.get_step_scale_trig_lock(track, program.get_current_step_for_channel(17))
    if global_lock == 0 then global_lock = nil end
    local function bypassed(value, by) return value .. (by and " BYPASSED" or "") end
    return {
      readonly("channel_lock", "Channel lock", scale_number(channel_lock), {raw = channel_lock}),
      readonly("global_lock", "Global lock", bypassed(scale_number(global_lock), global_lock and channel_lock), {raw = global_lock}),
      readonly("selected_scale", "Selected scale", bypassed(scale_number(data.default_scale), channel_lock or global_lock),
        {raw = data.default_scale}),
      readonly("effective_scale", "Effective scale", scale_number(program.get_channel_step_scale_number(channel.number)))
    }
  end

  local function held_in_row(cap, y)
    for _, key in ipairs(cap.held) do if key.y == y then return key.step end end
    return nil
  end

  local function selected_pattern() return src("program").get_selected_pattern() end

  function readers.P01(_, cap)
    local viewer = view_channel("Trig")
    if not viewer then return nil, "no_viewer" end
    local pattern = selected_pattern()
    local descriptors = {viewer}
    for row = 1, 4 do
      local first = (row - 1) * 16 + 1
      local s = held_in_row(cap, row + 3)
      descriptors[#descriptors + 1] = readonly("focus_" .. two(first) .. "_" .. two(first + 15),
        "Focus " .. two(first) .. ".." .. two(first + 15), s and step_label(s) or "NONE",
        {step = s, trig = s and pattern.trig_values[s] == 1 or nil})
    end
    return descriptors
  end

  function readers.P03(_, cap)
    local view = view_channel("Note")
    if not view then return nil, "no_viewer" end
    local pattern = selected_pattern()
    local s = cap.inspected_step
    local viewer = viewer_for("Note")
    local channel = viewer and viewer.selected_channel or 1
    local result = "NONE"
    if s then
      local snap = inspection.snapshot(cap.song, channel, s)
      if snap.emitted and snap.planned and snap.emitted.event_id == snap.planned.event_id and snap.emitted.pitch then
        result = note_name(snap.emitted.pitch) .. " LAST"
      elseif snap.planned then result = "PENDING" else result = "NO EVENT" end
    end
    return {
      view,
      readonly("relative_note", "Relative note", s and signed(pattern.note_values[s]) or "NONE", {step = s}),
      readonly("length", "Length", s and (pattern.lengths[s] .. " steps") or "NONE", {step = s}),
      -- The spec id is fixed; the label names the viewed channel.
      readonly("in_ch02", "In CH" .. two(channel), result, {step = s, channel = channel})
    }
  end

  function readers.P04(_, cap)
    local view = view_channel("Velocity")
    if not view then return nil, "no_viewer" end
    local program = src("program")
    local pattern = selected_pattern()
    local s = cap.inspected_step
    local data = program.get()
    local users = {}
    for c = 1, 16 do
      local channel = program.get_channel(data.selected_song_pattern, c)
      if channel.selected_patterns and channel.selected_patterns[data.selected_pattern] then users[#users + 1] = "CH" .. two(c) end
    end
    return {
      view,
      readonly("velocity", "Velocity", s and tostring(pattern.velocity_values[s]) or "NONE", {step = s}),
      readonly("used_by", "Used by", #users > 0 and table.concat(users, " ") or "NONE", {channels = users})
    }
  end

  function readers.P05(target)
    local context = target and target.context
    if not CONTEXT_PAGE[context] then return nil, "missing_context" end
    local channel, number = viewed_channel(context)
    if not channel then return nil, "no_viewer" end
    local program = src("program")
    local first, last = program.get_channel_step_bounds(channel)
    local current = program.get_current_step_for_channel(number)
    local patterns, numbers = pattern_list(channel)
    return {
      view_channel(context),
      readonly("range", "Range", two(first) .. ".." .. two(last), {first = first, last = last}),
      readonly("playhead", "Playhead", current and two(current) or "NONE", {step = current}),
      readonly("patterns", "Patterns", patterns, {patterns = numbers}),
      readonly("muted", "Muted", yes_no(channel.mute))
    }
  end

  -- A03: song playback. The queued jump is kept inside song_transition and
  -- only reachable through calculate_next_selected_song_pattern, which also
  -- answers the automatic next, so it cannot be shown apart.
  -- A03: song playback on one dashboard. The queued manual jump is kept inside
  -- song_transition and cannot be read apart from the automatic next, so Next
  -- shows what the engine will play next.
  function readers.A03()
    local program, params, step = src("program"), src("params"), src("step")
    local current = program.get().selected_song_pattern
    local song_mode = params:get("song_mode") == 2
    local song = program.get_selected_song_pattern()
    local next_number = song_mode and step.calculate_next_selected_song_pattern() or nil
    -- repeat_count read directly: program.get_repeat_count() writes a default.
    local pass, repeats = program.get().repeat_count, song.repeats
    return {
      readonly("playing", "Playing", "SONG " .. two(current), {slot = current}),
      readonly("next", "Next", next_number and ("SONG " .. two(next_number)) or "HOLD", {slot = next_number}),
      readonly("pass", "Pass", tostring(pass or 1) .. " / " .. tostring(repeats or 1), {pass = pass, repeats = repeats}),
      readonly("global_length", "Global length", tostring(song.global_pattern_length or 64),
        {length = song.global_pattern_length}),
      readonly("mode", "Song mode", song_mode and "AUTO" or "MANUAL", {song_mode = song_mode})
    }
  end

  function readers.F02()
    local channel = src("program").get_selected_channel()
    return {
      readonly("active_rate", "Active rate", tostring(channel.clock_mods and channel.clock_mods.name or "NONE")),
      unavailable("queued_rate", "Queued rate", "queue_not_readable"),
      -- channel_edit_clock_controls queues a clock change for the pattern end while playing.
      readonly("applies_at", "Applies at", playing() and "Pattern end" or "Immediately"),
      readonly("state", "State", transport())
    }
  end

  function readers.F03(_, cap)
    local steps = {}
    for _, key in ipairs(cap.held) do steps[#steps + 1] = step_label(key.step) end
    return {
      unavailable("grid", "Grid", "connection_state_not_exposed"),
      readonly("held_steps", "Held steps", #steps > 0 and table.concat(steps, " ") or "NONE"),
      unavailable("controls", "Controls"),
      readonly("playback", "Playback", transport())
    }
  end

  function readers.F04()
    return {
      unavailable("reason", "Reason", "rejection_not_exposed"),
      readonly("playback", "Playback", transport()),
      unavailable("autosave", "Autosave", "inhibition_not_exposed"),
      unavailable("recovery", "Recovery")
    }
  end

  function readers.F05(_, cap)
    local program, device_map = src("program"), src("device_map")
    local channel = program.get_selected_channel()
    local patterns, numbers = pattern_list(channel)
    local mask = channel.note_mask
    local planned = cap.snapshot.planned
    local output = "NO EVENT"
    if planned then
      local emitted = cap.snapshot.emitted
      output = (emitted and emitted.event_id == planned.event_id) and "EMITTED" or tostring(planned.bypass or planned.status or "PLANNED")
    end
    local device_id = program.get().devices[channel.number] and program.get().devices[channel.number].device_map
    local device = "NONE"
    if device_id and device_id ~= "none" then
      local found = device_map and device_map.get_device and device_map.get_device(device_id)
      device = found and found.name or tostring(device_id)
    end
    return {
      readonly("patterns", "Patterns", patterns, {patterns = numbers}),
      readonly("note_mask", "Note mask", (mask == nil or mask == -1) and "NONE" or note_name(mask), {raw = mask}),
      readonly("output", "Output", output, {event_id = planned and planned.event_id, status = planned and planned.status}),
      readonly("device", "Device", device, {device_map = device_id})
    }
  end

  function readers.F07()
    local params = src("params")
    return {
      readonly("take", "Take", params:get("record") == 2 and "RECORDING" or "OFF"),
      unavailable("onset", "Onset", "midi_input_state_not_exposed"),
      unavailable("held_notes", "Held notes", "midi_input_state_not_exposed"),
      unavailable("length", "Length", "midi_input_state_not_exposed")
    }
  end

  local ALGORITHMS = {{"drum", "Drum"}, {"tresillo", "Tresillo"}, {"euclidean", "Euclidean"},
    {"numeric", "Numeric"}, {"rhythm_doctor", "Rhythm Doctor"}}

  -- P06: the trig algorithm picker. The algorithm in use reads SELECTED; K3
  -- selects the chosen row exactly as its grid fader key does.
  function readers.P06()
    local trig = src("trigger_edit_page")
    local algorithm = trig and trig.get_algorithm and trig.get_algorithm() or nil
    local descriptors = {}
    for n, a in ipairs(ALGORITHMS) do
      descriptors[#descriptors + 1] = {id = a[1], label = a[2], kind = "action",
        value = algorithm == n and "SELECTED" or "", domain = {algorithm = n, selected = algorithm == n},
        invoke = function()
          if not (trig and trig.select_algorithm) then return {ok = false, code = "no_owner"} end
          if algorithm == n then return {ok = true, status = "SELECTED"} end
          return {ok = trig.select_algorithm(n) == true}
        end}
    end
    return descriptors
  end

  local function signed_shift(n)
    if n == nil then return "NONE" end
    if n > 0 then return "+" .. n end
    return tostring(n)
  end

  -- P07: the paint preview the grid is showing (trigger_edit_page.paint_state).
  function readers.P07()
    local trig = src("trigger_edit_page")
    local state = trig and trig.paint_state and trig.paint_state()
    if not state then return nil, "no_owner" end
    return {
      readonly("preview", "Preview", state.painting and "PAINTING" or "OFF", {painting = state.painting}),
      readonly("algorithm", "Algorithm", ALGORITHMS[state.algorithm] and ALGORITHMS[state.algorithm][2] or "NONE",
        {algorithm = state.algorithm}),
      readonly("shift", "Shift", signed_shift(state.shift), {shift = state.shift}),
      readonly("trigs", "Trigs", state.painting and tostring(state.trigs) or "NONE", {trigs = state.trigs})
    }
  end

  function readers.P08(_, cap)
    local pattern = selected_pattern()
    local s = cap.inspected_step
    local length = s and pattern.lengths[s]
    return {
      readonly("toggle", "Toggle", s and (step_label(s) .. (pattern.trig_values[s] == 1 and " ON" or " OFF")) or "NONE", {step = s}),
      readonly("length", "Length", s and (two(s) .. ".." .. two(s + length - 1)) or "NONE", {step = s, length = length}),
      readonly("reset_length", "Reset length", s and step_label(s) or "NONE", {step = s}),
      readonly("pattern_select", "Pattern select", "PAT" .. two(src("program").get().selected_pattern))
    }
  end

  -- Protocol -------------------------------------------------------------------------

  local impl = {}

  function impl.describe(route, target)
    local screen_id = route:match("^snapshot:(.+)$") or route
    local reader = readers[screen_id]
    if not reader then return nil, "no_reader" end
    return reader(target, capture())
  end

  -- Immutable inspection snapshot for the selected channel (or target.channel),
  -- as the Note Dashboard captures it. A requested event id that is no longer
  -- the inspected one is reported stale, never merged.
  function impl.snapshot(target, event_id)
    local cap = capture(target and target.channel)
    local planned = cap.snapshot.planned
    local outcome = ui_adapters.outcome({provider = "read_only", target = target, snapshot = cap.snapshot,
      inspected_step = cap.inspected_step, channel = cap.channel_number, event_id = planned and planned.event_id})
    if not planned then outcome.status = "NO EVENT" end
    if event_id ~= nil and (not planned or planned.event_id ~= event_id) then outcome.stale = true end
    return outcome
  end

  return ui_adapters.new("read_only", impl)
end
