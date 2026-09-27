-- Independent Off/v1 baseline oracle for Merge Shape (docs/musical-merge-
-- extensions-plan.md §0 "Off stays exact" and the migration acceptance
-- boundary). This file is the single description of the v1 projects and of what
-- is observed. It is executed twice, by two different code bases:
--
--   * capture: in a checkout of the base revision f908a553, by
--     capture_tests.lua (run by capture.sh), which saves each project with the
--     base's own project save, reloads it with the base's own project load and
--     writes the observations as frozen fixtures;
--   * replay: in the candidate tree, by
--     lib/tests/lib/merge_v1_baseline_oracle_tests.lua, which loads the frozen
--     v1 project files with the candidate's production load, saves them as v2,
--     reloads v2 and compares every observation with the frozen base fixtures.
--
-- It must therefore use only APIs present in f908a553, and must never be
-- edited without recapturing from f908a553: the replay test checks this file's
-- sha256 against the one recorded when the fixtures were captured.
--
-- Observations (per load, each played twice: lead 0 and lead 25 ms with the
-- "pulse-advance" lock contract, so lock lookahead is installed):
--   working  every channel's working pattern after the load (values, roles,
--            reasons, sources; the embedded configuration table is omitted
--            because v2 canonicalises it; it is compared separately),
--   rebuilds every working-pattern content change during playback, with the
--            pulse it was first seen on,
--   midi     every note on, note off and CC with its pulse, channel, device and
--            the lead argument, in emission order, including Stop's releases,
--   rng      every draw from Mosaic's RNG (arguments and result), from a
--            deterministic recording generator installed as `random` and
--            `math.random`.

local scenario = {}

scenario.PULSES = 24 * 16 * 8 -- eight 16-step cycles of the /1 channels
scenario.LEAD_MS = 25

------------------------------------------------------------------------------
-- Canonical serialisation (sorted keys; integers and floats kept apart).

local function key_order(a, b)
  local ta, tb = type(a), type(b)
  if ta ~= tb then return ta < tb end
  if ta == "number" or ta == "string" then return a < b end
  return tostring(a) < tostring(b)
end

local function scalar(value)
  local kind = type(value)
  if kind == "number" then
    if math.type(value) == "integer" then return tostring(value) end
    if value ~= value then return "0/0" end
    if value == math.huge then return "math.huge" end
    if value == -math.huge then return "-math.huge" end
    local text = string.format("%.17g", value)
    if not text:find("[%.eEn]") then text = text .. ".0" end
    return text
  elseif kind == "string" then
    return string.format("%q", value)
  elseif kind == "boolean" or kind == "nil" then
    return tostring(value)
  end
  return string.format("%q", "<" .. kind .. ">")
end

function scenario.serialize(value, seen)
  if type(value) ~= "table" then return scalar(value) end
  seen = seen or {}
  if seen[value] then return '"<cycle>"' end
  seen[value] = true
  local keys = {}
  for key in pairs(value) do keys[#keys + 1] = key end
  table.sort(keys, key_order)
  local parts = {}
  for _, key in ipairs(keys) do
    local item = value[key]
    if type(item) ~= "function" and type(item) ~= "userdata" and type(item) ~= "thread" then
      parts[#parts + 1] = "[" .. scalar(key) .. "]=" .. scenario.serialize(item, seen)
    end
  end
  seen[value] = nil
  return "{" .. table.concat(parts, ",") .. "}"
end

local function copy(value)
  return load("return " .. scenario.serialize(value))()
end

------------------------------------------------------------------------------
-- The v1 projects. Built only through f908a553 APIs.

local function merge_v1(fields)
  local value = {schema_version = 1, mode = "off", anchor = nil, amount = 100, accent = 70,
    gap = 0, seed = 0, ranking_version = 1, cycles = 1, shape = "flat", percentages = {100},
    variation = "fixed", keep_anchor_pitch = false, target = {kind = "legacy"}}
  for key, item in pairs(fields or {}) do value[key] = item end
  return value
end

local function set_range(channel, first, last)
  channel.start_trig = {(first - 1) % 16 + 1, 4 + (first - 1) // 16}
  channel.end_trig = {(last - 1) % 16 + 1, 4 + (last - 1) // 16}
end

local function source(song, number, trigs, base_note, velocity)
  local value = song.patterns[number]
  for index, step in ipairs(trigs) do
    value.trig_values[step] = 1
    value.note_values[step] = (base_note + index * 2) % 8
    value.velocity_values[step] = velocity - index
    value.lengths[step] = (index % 3) + 1
  end
end

-- Probability, random note, random velocity and a MIDI CC slot on `number`,
-- with step locks on `steps`, so RNG draws and lock lookahead both happen on
-- merged (anchor and addition) steps.
local function locks(number, steps)
  local channel = program.get_channel(1, number)
  channel.trig_lock_params[1] = {id = "trig_probability", param_id = "v1b_prob_" .. number, off_value = -1}
  channel.trig_lock_params[2] = {id = "bipolar_random_note", param_id = "v1b_rnote_" .. number}
  channel.trig_lock_params[3] = {id = "random_velocity", param_id = "v1b_rvel_" .. number}
  channel.trig_lock_params[4] = {type = "midi", id = "cc74", param_id = "v1b_cc_" .. number,
    cc_msb = 74, cc_min_value = 0, cc_max_value = 127, off_value = -1}
  for index, step in ipairs(steps) do
    program.add_step_param_trig_lock_to_channel(channel, step, 1, 40 + index * 7)
    if index % 2 == 0 then program.add_step_param_trig_lock_to_channel(channel, step, 2, 2 + index % 3) end
    if index % 3 == 0 then program.add_step_param_trig_lock_to_channel(channel, step, 3, 4) end
    program.add_step_param_trig_lock_to_channel(channel, step, 4, (step * 9) % 128)
  end
end

local function base_song()
  program.init(); globals.reset(); params.reset(); memory.init()
  program.set_selected_song_pattern(1)
  local song = program.get_song_pattern(1)
  for number = 1, 16 do program.get().devices[number].midi_channel = number end
  source(song, 1, {1, 5, 9, 13}, 0, 110)
  source(song, 2, {2, 3, 6, 7, 10, 11, 14, 15}, 1, 90)
  source(song, 3, {4, 8, 12, 16}, 3, 80)
  source(song, 4, {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16}, 5, 100)
  local channels = song.channels
  channels[1].selected_patterns = {[1] = true, [2] = true}; set_range(channels[1], 1, 16)
  channels[2].selected_patterns = {[2] = true, [3] = true}; set_range(channels[2], 1, 12)
  channels[2].clock_mods = {name = "x2", value = 2, type = "clock_multiplication"}
  channels[3].selected_patterns = {[1] = true, [4] = true}; set_range(channels[3], 3, 10)
  channels[3].clock_mods = {name = "/2", value = 2, type = "clock_division"}
  channels[4].selected_patterns = {[3] = true}; set_range(channels[4], 1, 16)
  channels[5].selected_patterns = {[1] = true, [2] = true, [3] = true}; set_range(channels[5], 1, 16)
  channels[5].note_merge_mode = "up"
  locks(1, {2, 5, 6, 10, 13, 14})
  locks(2, {1, 3, 6, 7, 11})
  locks(3, {3, 4, 6, 9})
  locks(5, {1, 2, 4, 8, 16})
  return song
end

local function foundation_phrases()
  return merge_v1({mode = "foundation", anchor = 1, amount = 80, accent = 60, gap = 1, seed = 321,
    cycles = 4, shape = "custom", percentages = {25, 100, 50, 75}, variation = "per_phrase",
    keep_anchor_pitch = true, target = {kind = "degrees", degrees = {1, 3, 5}}})
end

local projects = {}

-- No channel has a merge configuration (the Off fast path).
projects[#projects + 1] = {name = "absent", build = function() base_song() end}

-- Explicit Off, with non-default recognised fields (never active while Off).
projects[#projects + 1] = {name = "explicit_off", build = function()
  local song = base_song()
  song.channels[1].musical_merge = merge_v1({mode = "off", anchor = 1, amount = 40, accent = 20,
    gap = 2, seed = 77, cycles = 2, shape = "build", percentages = {50, 100},
    variation = "per_phrase", keep_anchor_pitch = true, target = {kind = "degrees", degrees = {1, 5}}})
  song.channels[2].musical_merge = merge_v1()
  song.channels[3].musical_merge = merge_v1({anchor = 4, target = {kind = "scale"}})
end}

-- Foundation enabled: phrase cycles, per-phrase variation, pitch targets.
projects[#projects + 1] = {name = "foundation", build = function()
  local song = base_song()
  song.channels[1].musical_merge = foundation_phrases()
  song.channels[2].musical_merge = merge_v1({mode = "foundation", anchor = 2, amount = 65, accent = 0,
    gap = 0, seed = 9, cycles = 2, shape = "build", percentages = {50, 100}, variation = "fixed",
    target = {kind = "scale"}})
  song.channels[3].musical_merge = merge_v1({mode = "foundation", anchor = 4, amount = 100,
    accent = 100, gap = 2, seed = 65535, cycles = 8, shape = "answer",
    percentages = {100, 25, 100, 25, 100, 25, 100, 25}, variation = "per_phrase"})
end}

-- v1 data carrying keys v1 never gave semantics: unknown top-level and nested
-- target keys, and keys named like every new v2 field (interlock, space,
-- fragments, structure), as tables and as other types.
projects[#projects + 1] = {name = "unknown_keys", build = function()
  local song = base_song()
  local first = foundation_phrases()
  first.unknown_top = {deep = {1, 2}}
  first.future = "x"
  first.target = {kind = "degrees", degrees = {1, 3}, group_id = 9, note = "nested unknown", extra = {1}}
  first.interlock = {leader = 2, window = 3}
  first.space = {leader = 3, release = 2}
  first.fragments = {size = 16, keep_anchor = true}
  first.structure = {markers = "every_4", group_id = 1}
  song.channels[1].musical_merge = first
  local second = merge_v1({mode = "off", anchor = 3, seed = 12})
  second.interlock = true; second.space = "reserved"; second.fragments = 5; second.structure = "anchors"
  second.schema = 2; second.mode_v2 = "fragments"
  song.channels[2].musical_merge = second
  local third = merge_v1({mode = "foundation", anchor = 4, amount = 55, seed = 400,
    target = {kind = "scale", degrees = {2}, group_id = 4}})
  third.interlock = {leader = 1, window = 0}; third.fragments = {size = 4}
  song.channels[3].musical_merge = third
end}

-- Foundation + Harmony Pattern with a nonempty saved Pattern map, and a
-- Foundation chord pitch target reading an enabled Harmony Ensemble group.
projects[#projects + 1] = {name = "foundation_harmony_pattern", build = function()
  local song = base_song()
  local harmony_config = include("mosaic/lib/harmony/config")
  local pattern_harmony = include("mosaic/lib/harmony/pattern")
  local group = harmony_config.new_group(6)
  group.enabled = true
  song.voicing = {schema_version = 1, groups = {[3] = group}}
  song.channels[6].voicing = harmony_config.new_channel("ensemble"); song.channels[6].voicing.group_id = 3
  song.channels[6].selected_patterns = {[1] = true}
  song.channels[6].chord_one_mask = 2; song.channels[6].chord_two_mask = 4
  local channel = song.channels[1]
  channel.musical_merge = foundation_phrases()
  channel.voicing = harmony_config.new_channel("pattern")
  channel.voicing.pattern_maps[pattern_harmony.binding_key(channel)] = {schema_version = 1, revision = 3,
    assignments = {["0"] = "bass", ["2"] = "inner1", ["4"] = "inner2", ["6"] = "top"}}
  song.channels[2].musical_merge = merge_v1({mode = "foundation", anchor = 2, amount = 90, accent = 40,
    seed = 5, cycles = 2, shape = "fill", percentages = {25, 100}, variation = "per_phrase",
    target = {kind = "chord", group_id = 3}})
end}

scenario.projects = projects

------------------------------------------------------------------------------
-- Production project load and save, through the tree's own
-- lib/project_lifecycle.lua, with only the host UI and parameter-file edges
-- stubbed.

local function with_globals(replacements, body)
  local saved = {}
  for name, value in pairs(replacements) do saved[name] = {value = rawget(_G, name)}; rawset(_G, name, value) end
  local ok, err = pcall(body)
  for name, entry in pairs(saved) do rawset(_G, name, entry.value) end
  if not ok then error(err, 0) end
end

local function with_fields(target, replacements, body)
  local saved = {}
  for name, value in pairs(replacements) do saved[name] = {value = rawget(target, name)}; rawset(target, name, value) end
  local ok, err = pcall(body)
  for name, entry in pairs(saved) do rawset(target, name, entry.value) end
  if not ok then error(err, 0) end
end

local function noop() end

local function host(body, data_directory)
  local real_norns = rawget(_G, "norns")
  local host_norns = setmetatable({state = setmetatable({data = (data_directory or ".") .. "/"},
    {__index = type(real_norns) == "table" and real_norns.state or nil})},
    {__index = real_norns})
  local timer = {start = noop, stop = noop}
  local param_manager = {init = noop, add_device_params = noop}
  local messages = {}
  with_globals({
    testing = true,
    nb = {stop_all = noop},
    norns = host_norns,
    tab = rawget(_G, "tab") or require("tabutil"),
    norns_param_state_handler = include("mosaic/lib/devices/norns_param_state_handler"),
    tooltip = {show = function(_, message) messages[#messages + 1] = message end},
    ui = {refresh = noop},
    song_edit_page_ui = {refresh_tempo = noop},
    clock = rawget(_G, "clock") or {},
    metro = {init = function() return {start = noop, stop = noop} end, free = noop},
  }, function()
    with_fields(m_midi, {start = noop, stop = noop}, function()
      with_fields(params, {
        read = noop,
        write = function(self, path) if self.action_write then self.action_write(path) end end,
      }, function()
        local lifecycle = include("mosaic/lib/project_lifecycle").new(timer, timer, param_manager,
          include("mosaic/lib/project_validation"), noop, nil)
        body(lifecycle, messages)
      end)
    end)
  end)
end

-- include() is dofile in the harness, and m_clock.lua assigns the global
-- m_clock each time it runs. mosaic.lua includes step last, so in the
-- application the global m_clock is the instance step schedules its releases
-- on. Test files leave whichever instance they loaded last; rebind the pair the
-- way the application does for the duration of a scenario call, then restore.
local function with_application_binding(body)
  local names = {"step", "m_clock", "clock_lattice", "random"}
  local saved = {}
  for _, name in ipairs(names) do saved[name] = rawget(_G, name) end
  rawset(_G, "step", include("mosaic/lib/step"))
  local ok, err = pcall(body)
  for _, name in ipairs(names) do rawset(_G, name, saved[name]) end
  if not ok then error(err, 0) end
end

-- Saves the live project as `<directory>/<name>.ptn` through the production
-- save. Returns the path.
function scenario.save(directory, name)
  local path
  with_application_binding(function()
    host(function(lifecycle, messages)
      local ok = lifecycle.save(name)
      assert(ok == true, "save failed: " .. tostring(messages[#messages]))
      path = directory .. "/" .. name .. ".ptn"
    end, directory)
  end)
  return path
end

-- Loads a .ptn through the production load. Returns true or false, reason.
function scenario.load(path)
  local result, reason
  host(function(lifecycle, messages)
    result = lifecycle.load(path)
    if result ~= true then reason = messages[#messages] end
  end)
  return result, reason
end

------------------------------------------------------------------------------
-- Observation.

local function working_snapshot(channel)
  local working = channel.working_pattern
  if working == nil then return false end
  local value = copy(working)
  if type(value.foundation) == "table" then value.foundation.config = nil end
  return value
end

local function install_rng()
  local state = 20240907
  local draws = {}
  local function draw(m, n)
    state = (state * 1103515245 + 12345) % 2147483648
    local result
    if m == nil then result = state / 2147483648
    elseif n == nil then result = 1 + state % m
    else result = m + state % (n - m + 1) end
    draws[#draws + 1] = table.concat({tostring(m), tostring(n), tostring(result)}, ",")
    return result
  end
  return draw, draws
end

local function transport_pulse()
  if type(clock_lattice) == "table" and type(clock_lattice.transport) == "number" then
    return clock_lattice.transport
  end
  return 0
end

-- Plays the loaded project and records everything above. `lead_ms` 0 leaves
-- lookahead uninstalled; otherwise the pulse-advance contract installs it.
function scenario.play(lead_ms)
  local song = program.get_song_pattern(1)
  local observation = {lead_ms = lead_ms, working = {}, rebuilds = {}, midi = {}, rng = {}}
  -- Parameter values are not project data (.pset); leave every CC slot's
  -- assigned value Off so only locked steps send.
  for number = 1, 16 do
    for _, definition in pairs(song.channels[number].trig_lock_params or {}) do
      if type(definition) == "table" and definition.param_id then params:set(definition.param_id, -1) end
    end
  end
  pattern.update_working_patterns(song)
  local seen, last = {}, {}
  for number = 1, 17 do
    local snapshot = working_snapshot(song.channels[number])
    observation.working[number] = snapshot
    seen[number] = song.channels[number].working_pattern
    last[number] = scenario.serialize(snapshot)
  end
  local draw, draws = install_rng()
  local midi = observation.midi
  local note_on, note_off, cc = m_midi.note_on, m_midi.note_off, m_midi.cc
  local function run()
    m_midi.note_on = function(self, note, velocity, channel, device, lead, ...)
      midi[#midi + 1] = table.concat({"on", transport_pulse(), tostring(note), tostring(velocity),
        tostring(channel), tostring(device), tostring(lead)}, ",")
      return note_on(self, note, velocity, channel, device, lead, ...)
    end
    m_midi.note_off = function(self, note, velocity, channel, device, lead, ...)
      midi[#midi + 1] = table.concat({"off", transport_pulse(), tostring(note), tostring(velocity),
        tostring(channel), tostring(device), tostring(lead)}, ",")
      return note_off(self, note, velocity, channel, device, lead, ...)
    end
    m_midi.cc = function(msb, lsb, value, channel, device, ...)
      midi[#midi + 1] = table.concat({"cc", transport_pulse(), tostring(msb), tostring(lsb),
        tostring(value), tostring(channel), tostring(device)}, ",")
      return cc(msb, lsb, value, channel, device, ...)
    end
    m_midi.set_lead_time(lead_ms)
    m_clock.set_lock_contract(lead_ms > 0 and "pulse-advance" or "legacy-delay-v1")
    m_clock.init()
    m_clock:start()
    local function observe_rebuilds()
      for number = 1, 17 do
        local working = song.channels[number].working_pattern
        if working ~= seen[number] then
          seen[number] = working
          local snapshot = working_snapshot(song.channels[number])
          local text = scenario.serialize(snapshot)
          if text ~= last[number] then
            last[number] = text
            observation.rebuilds[#observation.rebuilds + 1] = {pulse = transport_pulse(), channel = number,
              working = snapshot}
          end
        end
      end
    end
    observe_rebuilds()
    for _ = 1, scenario.PULSES do
      m_clock.get_clock_lattice():pulse()
      observe_rebuilds()
    end
    midi[#midi + 1] = "stop"
    m_clock:stop()
  end
  -- testing: this scenario supplies every lattice pulse explicitly (the
  -- harness convention of lib/tests/lib/integration_tests/clock_tests.lua);
  -- without it the result would depend on what earlier tests left behind.
  with_globals({testing = true, random = draw, nb = {stop_all = noop},
    norns_param_state_handler = include("mosaic/lib/devices/norns_param_state_handler")}, function()
    with_fields(math, {random = draw}, function()
      with_fields(m_midi, {start = noop, stop = noop}, function()
        local ok, err = pcall(run)
        m_midi.note_on, m_midi.note_off, m_midi.cc = note_on, note_off, cc
        m_midi.set_lead_time(0)
        m_clock.set_lock_contract("legacy-delay-v1")
        if not ok then error(err, 0) end
      end)
    end)
  end)
  observation.rng = draws
  return observation
end

-- Loads `path` twice through the production load and plays it without and
-- with lead. Returns {lead_0 = observation, lead_25 = observation}.
function scenario.observe(path)
  local result = {}
  with_application_binding(function()
    for _, lead in ipairs({0, scenario.LEAD_MS}) do
      local ok, reason = scenario.load(path)
      assert(ok == true, "load failed for " .. path .. ": " .. tostring(reason))
      result["lead_" .. lead] = scenario.play(lead)
    end
  end)
  return result
end

return scenario
