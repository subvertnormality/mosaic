-- Mutation killers for lib/step.lua (campaign mutation-bc0570c, wave 4 delta): the scale a
-- manually entered MIDI note uses, and the NRPN encoding a parameter lock is sent with.
-- Unless a README line is cited, an assertion is characterisation of current behaviour.
-- Every global this file replaces is restored after each test, including on failure.

local step_under_test = include("mosaic/lib/step")
-- step.lua bound the m_clock instance its own include created, which publishes itself as
-- the global; capture it before anything else re-includes the module.
local clock_of_step = m_clock

local REPLACED_GLOBALS = {"m_clock", "params", "m_midi", "device_map", "recorder", "norns_param_state_handler"}

local function with_env(body)
  local saved = {}
  for _, name in ipairs(REPLACED_GLOBALS) do saved[name] = rawget(_G, name) end
  local ok, err = pcall(function()
    program.init()
    local env = {events = {}, device = {id = "test_midi_device"}}
    local store = {}
    params = {}
    function params:get(id) local p = store[id]; if p then return p.val end end
    function params:set(id, value) store[id] = store[id] or {}; store[id].val = value end
    function params:lookup_param(id) return store[id] end
    m_midi = {}
    function m_midi.cc(msb, lsb, value, channel)
      table.insert(env.events, {kind = "cc", msb = msb, value = value, channel = channel})
    end
    function m_midi.nrpn(msb, lsb, value, channel, device, mode)
      table.insert(env.events, {kind = "nrpn", msb = msb, lsb = lsb, value = value, channel = channel, mode = mode})
    end
    device_map = {get_device = function() return env.device end}
    recorder = {trig_lock_is_dirty = function() return nil end}
    norns_param_state_handler = include("mosaic/lib/devices/norns_param_state_handler")
    m_clock = clock_of_step
    clock_of_step.init()
    clock_of_step.cancel_all_spread_actions()
    body(env)
  end)
  for _, name in ipairs(REPLACED_GLOBALS) do rawset(_G, name, saved[name]) end
  if not ok then error(err, 0) end
end

---------------------------------------------------------------------------
-- Scale of a note entered while holding a step (m_midi.lua note-on ->
-- step.manually_calculate_step_scale_number)
---------------------------------------------------------------------------

-- README 850: the applied global scale is the default for all patterns unless a global or
-- channel scale lock overrides it, and "With global scale off and no scale lock, pattern
-- degrees play as chromatic semitone offsets" (scale number 0, program.get_scale(0)).
-- Scale slot 1 is the default of a new project (lib/models/program.lua default_scale = 1).
function test_w4k_manual_scale_lookup_uses_the_global_scale_including_slot_one()
  with_env(function()
    for _, default_scale in ipairs({1, 2, 16}) do
      program.get().default_scale = default_scale
      luaunit.assert_equals(step_under_test.manually_calculate_step_scale_number(2, 4), default_scale,
        "Global scale " .. default_scale)
    end
    program.get().default_scale = 0
    luaunit.assert_equals(step_under_test.manually_calculate_step_scale_number(2, 4), 0, "Global scale off")
  end)
end

---------------------------------------------------------------------------
-- NRPN encoding of a parameter lock (step.process_params)
---------------------------------------------------------------------------

-- characterisation (docs/testing/NRPN_COMPATIBILITY.md, "Saved assignment/control choices
-- take precedence"): a lock is sent with the NRPN mode saved on its parameter assignment,
-- even when the channel's stored-control history for the routed device says otherwise.
-- Reachable: a pre-policy project migrated while channel 1's map was missing records
-- legacy-half for that device ("*"); an assignment made on another song slot after routing
-- the channel to a standard device keeps "standard" when the channel is routed back.
-- Without such history the stored mode is the assignment's own (both cases pinned).
function test_w4k_nrpn_lock_uses_the_mode_saved_on_its_assignment()
  local function sent_modes(assignment_mode, stored_history)
    local modes
    with_env(function(env)
      program.get().nrpn_stored_modes = stored_history
      local channel = program.get_channel(1, 1)
      local wp = program.initialise_default_pattern()
      wp.trig_values[1] = 1
      channel.working_pattern = wp
      channel.trig_lock_params[1] = {
        type = "midi", id = "nrpn_param", param_id = "nrpn_param_id", off_value = -1,
        nrpn_msb = 3, nrpn_lsb = 9, nrpn_min_value = 0, nrpn_max_value = 16383,
        cc_msb = 74, cc_min_value = -1, cc_max_value = 127, nrpn_lsb_mode = assignment_mode
      }
      channel.step_trig_lock_banks[1] = {[1] = 1000}
      step_under_test.process_params(channel, 1)
      modes = {}
      for _, e in ipairs(env.events) do
        luaunit.assert_equals({e.kind, e.msb, e.lsb, e.value}, {"nrpn", 3, 9, 1000})
        modes[#modes + 1] = e.mode
      end
    end)
    return modes
  end
  local legacy_history = {[1] = {test_midi_device = {["*"] = "legacy-half"}}}
  local standard_history = {[1] = {test_midi_device = {nrpn_param = "standard"}}}
  luaunit.assert_equals(sent_modes("standard", legacy_history), {"standard"})
  luaunit.assert_equals(sent_modes("legacy-half", standard_history), {"legacy-half"})
  luaunit.assert_equals(sent_modes("standard", {}), {"standard"})
end
