-- Characterisation outside README.  This is the pure UI boundary described by
-- docs/rhythm-doctor/PLAN.md "User contract and coordinate convention" and
-- "Bank lifecycle, races and persistence".  Native grid/norns dispatch is
-- intentionally injected by the eventual page integration.
package.path = "./lib/?.lua;" .. package.path
local Adapter = require("rhythm_doctor.ui_adapter")

local failures, count = {}, 0
local function test(name, body)
  count = count + 1
  local ok, err = pcall(body)
  if not ok then failures[#failures + 1] = name .. ": " .. tostring(err) end
end
local function equal(actual, expected, message)
  assert(actual == expected, (message or "values differ") .. ": expected " .. tostring(expected) .. ", got " .. tostring(actual))
end
local function check(value, message) assert(value, message or "expected true") end

local function reply(code, extra)
  extra = extra or {}; extra.code, extra.ok = code, code == "OK"; return extra
end

local function context()
  local stopped, calls = true, {}
  local runtime = { machine = { state = "EMPTY", bank = nil, last_message = nil } }
  function runtime:enter() calls[#calls + 1] = { "enter" }; return reply("OK") end
  function runtime:start_capture(mode)
    calls[#calls + 1] = { "start", mode }; self.machine.state = mode == "auto" and "LISTENING" or "RECORDING"; return reply("OK")
  end
  function runtime:record_action()
    calls[#calls + 1] = { "record_action" }
    local token = { project_id = "p", generation = 1, analysis_revision = 0, operation = self.next_operation or "clear", state = self.machine.state, nonce = 2 }
    self.machine.modal = token
    return token
  end
  function runtime:confirm_modal(token, accepted)
    calls[#calls + 1] = { "confirm", token, accepted }
    self.machine.modal = nil
    return reply(accepted and "OK" or "CANCELLED")
  end
  function runtime:finish(enough)
    calls[#calls + 1] = { "finish", enough }; self.machine.state = "ANALYSING"; return reply("OK")
  end
  function runtime:transport_started() calls[#calls + 1] = { "transport_started" }; self.machine.state = "EMPTY"; return reply("OK") end
  function runtime:transport_stopped_event() calls[#calls + 1] = { "transport_stopped" }; return reply("OK") end
  function runtime:poll() calls[#calls + 1] = { "poll" }; return reply("NO_EVENT") end
  function runtime:set_window_start(start)
    calls[#calls + 1] = { "window", start }
    self.machine.bank.window_start = math.max(0, math.min(self.machine.bank.timeline_cells - 64, start))
    return reply("WINDOW_MOVED", { window_start = self.machine.bank.window_start })
  end
  function runtime:set_sensitivity(lane, value)
    calls[#calls + 1] = { "sensitivity", lane, value }
    self.machine.bank.sensitivities[lane] = value
    return reply("SENSITIVITY_UPDATED", { sensitivity = value })
  end
  function runtime:apply_alignment(draft)
    calls[#calls + 1] = { "alignment", draft }
    self.machine.state = "REANALYSING"
    return reply("OK")
  end
  local adapter = Adapter.new({ runtime = runtime, transport_stopped = function() return stopped end, mode = "manual" })
  return { adapter = adapter, runtime = runtime, calls = calls, set_stopped = function(value) stopped = value end }
end

test("Record begins a configured capture from EMPTY on key-down and owns its release", function()
  local c = context()
  local down = c.adapter:grid_key(1, 2, 1)
  equal(down.code, "OK"); equal(c.calls[1][1], "start"); equal(c.calls[1][2], "manual")
  equal(c.adapter:grid_key(1, 2, 1).code, "HELD_RECORD")
  equal(#c.calls, 1, "a held Record must not retrigger")
  equal(c.adapter:grid_key(1, 2, 0).code, "RELEASE_CONSUMED")
  equal(c.adapter:grid_key(1, 2, 0).code, "UNCLAIMED", "only the owned release is consumed")
end)

test("an incompatible runtime transition immediately dismisses the local modal token", function()
  local c = context(); c.runtime.machine.state = "LISTENING"; c.runtime.next_operation = "cancel_capture"
  c.adapter:grid_key(1, 2, 1); c.adapter:grid_key(1, 2, 0)
  check(c.adapter:screen_model().modal)
  c.runtime.machine.state, c.runtime.machine.modal = "ANALYSING", nil
  equal(c.adapter:poll().code, "NO_EVENT")
  check(not c.adapter:screen_model().modal, "completion or timeout cannot leave a stale modal")
  equal(c.adapter:key(3, 1).code, "UNCLAIMED")
end)

test("Record also retries from FAILED, while non-record keys remain outside this controller", function()
  local c = context(); c.runtime.machine.state = "FAILED"
  equal(c.adapter:grid_key(1, 2, 1).code, "OK")
  equal(c.calls[1][1], "start")
  equal(c.adapter:grid_key(8, 4, 1).code, "UNCLAIMED")
end)

test("Record opens a runtime-owned modal for an occupied bank and K3 cannot accept before Record releases", function()
  local c = context(); c.runtime.machine.state = "READY"
  equal(c.adapter:grid_key(1, 2, 1).operation, "clear")
  equal(c.adapter:key(3, 1).code, "RELEASE_PENDING")
  equal(c.adapter:grid_key(1, 2, 0).code, "RELEASE_CONSUMED")
  equal(c.adapter:key(3, 1).code, "OK")
  equal(c.calls[#c.calls][1], "confirm"); check(c.calls[#c.calls][3])
end)

test("K2 cancels a capture modal and modal keys do not leak into Finish", function()
  local c = context(); c.runtime.machine.state = "LISTENING"; c.runtime.next_operation = "cancel_capture"
  c.adapter:grid_key(1, 2, 1); c.adapter:grid_key(1, 2, 0)
  equal(c.adapter:key(2, 1).code, "CANCELLED")
  equal(c.calls[#c.calls][1], "confirm"); check(not c.calls[#c.calls][3])
  equal(c.adapter:key(3, 1).code, "MORE_AUDIO_NEEDED")
end)

test("K3 Finish is available only after enough audio and only while capturing", function()
  local c = context(); c.runtime.machine.state = "RECORDING"
  equal(c.adapter:key(3, 1).code, "MORE_AUDIO_NEEDED")
  c.adapter:set_capture_progress({ enough_audio = true, acquired_beats = 16, tempo = 120, source = "manual" })
  equal(c.adapter:key(3, 1).code, "OK")
  equal(c.calls[#c.calls][1], "finish"); check(c.calls[#c.calls][2])
end)

test("lane keys select BD, SD, CYM and BASS, ignore their releases, and leave the retired column inert", function()
  local c = context()
  for index, lane in ipairs({ "BD", "SD", "CYM", "BASS" }) do
    equal(c.adapter:grid_key(index + 2, 2, 1).code, "LANE_SELECTED")
    equal(c.adapter:screen_model().lane, lane)
    equal(c.adapter:grid_key(index + 2, 2, 0).code, "UNCLAIMED")
  end
  equal(c.adapter:grid_key(2, 2, 1).code, "UNCLAIMED", "reserved column has no legacy fader effect")
  -- Columns 6 and 7 carried OHH and BASS before those lanes were withdrawn.
  -- They must not silently select a lane now, or a player pressing where a
  -- lane used to be would get an unrelated one.
  equal(c.adapter:grid_key(7, 2, 1).code, "UNCLAIMED", "retired lane column stays inert")
end)

test("stopped setup drafts Auto/Manual, manual BPM and input, then commits only with K3", function()
  local c = context()
  local initial = c.adapter:screen_model()
  equal(initial.capture_mode, "manual")
  equal(initial.manual_bpm, 120)
  equal(initial.input_source, "STEREO")

  equal(c.adapter:enc(2, -1).code, "SETUP_FIELD_SELECTED")
  equal(c.adapter:screen_model().setup.field, "INPUT")
  equal(c.adapter:enc(3, 1).code, "SETUP_EDITED")
  equal(c.adapter:screen_model().input_source, "L")
  equal(c.adapter:enc(2, -1).code, "SETUP_FIELD_SELECTED")
  equal(c.adapter:screen_model().setup.field, "MANUAL BPM")
  equal(c.adapter:enc(3, 7).code, "SETUP_EDITED")
  equal(c.adapter:screen_model().manual_bpm, 127)
  equal(c.adapter:enc(2, -1).code, "SETUP_FIELD_SELECTED")
  equal(c.adapter:enc(3, 1).code, "SETUP_EDITED")
  equal(c.adapter:screen_model().capture_mode, "auto")
  equal(c.adapter:key(3, 1).code, "SETUP_CONFIRMED")
  local committed = c.adapter:screen_model()
  check(not committed.setup.active)
  equal(committed.capture_mode, "auto"); equal(committed.manual_bpm, 127); equal(committed.input_source, "L")
  equal(#c.calls, 0, "setup is UI state and must not start analysis or capture")
end)

test("K2 discards a setup draft, while transport running cannot select or edit setup", function()
  local c = context()
  c.adapter:enc(3, 1)
  equal(c.adapter:screen_model().capture_mode, "auto")
  equal(c.adapter:key(2, 1).code, "SETUP_CANCELLED")
  equal(c.adapter:screen_model().capture_mode, "manual")
  c.set_stopped(false)
  equal(c.adapter:enc(2, 1).code, "STOP_SEQUENCER")
  equal(c.adapter:enc(3, 1).code, "STOP_SEQUENCER")
  equal(c.adapter:screen_model().setup.active, false)
end)

test("manual BPM is bounded to the documented supported capture range", function()
  local c = context()
  c.adapter:enc(2, -1) -- INPUT
  c.adapter:enc(2, -1) -- MANUAL BPM
  c.adapter:enc(3, -1000)
  equal(c.adapter:screen_model().manual_bpm, 40)
  c.adapter:enc(3, 1000)
  equal(c.adapter:screen_model().manual_bpm, 240)
end)

test("running transport gates grid, lane changes, Finish, and presents STOP SEQUENCER", function()
  local c = context(); c.set_stopped(false); c.runtime.machine.state = "READY"
  equal(c.adapter:grid_key(1, 2, 1).code, "STOP_SEQUENCER")
  equal(c.adapter:grid_key(4, 2, 1).code, "STOP_SEQUENCER")
  equal(c.adapter:key(3, 1).code, "STOP_SEQUENCER")
  equal(#c.calls, 0)
  equal(c.adapter:screen_model().status, "STOP SEQUENCER")
end)

test("screen model is a read-only summary of status, selected-lane hits and capture diagnostics", function()
  local c = context(); c.runtime.machine.state = "READY"
  c.runtime.machine.bank = { bpm = 137, tempo_mode = "auto", timeline_cells = 97,
    lanes = { BD = { [1] = {}, [2] = {} }, SD = {}, CYM = {}, BASS = {} } }
  c.adapter:set_capture_progress({ listening_confidence = .8, acquired_beats = 19, analysis_progress = .25, source = "stereo" })
  local model = c.adapter:screen_model()
  equal(model.title, "RHYTHM DOCTOR"); equal(model.state, "READY"); equal(model.lane, "BD")
  equal(model.hit_count, 2); equal(model.tempo, 137); equal(model.tempo_source, "auto")
  equal(model.total_steps, 97); equal(model.total_bars, 6); equal(model.status, "READY")
  equal(model.listening_confidence, .8); equal(model.acquired_beats, 19); equal(model.analysis_progress, .25)
end)

test("READY browser moves one shared nonwrapping window by bars or steps", function()
  local c = context(); c.runtime.machine.state = "READY"
  c.runtime.machine.bank = { bpm = 120, timeline_cells = 97, window_start = 0,
    sensitivities = { BD = 0, SD = 0, CYM = 0 }, lanes = { BD = {}, SD = {}, CYM = {}, CYM = {}, BD = {} } }
  equal(c.adapter:screen_model().ready.field, "WINDOW BAR")
  equal(c.adapter:enc(3, 1).code, "WINDOW_MOVED"); equal(c.calls[#c.calls][2], 16)
  equal(c.adapter:enc(2, 1).field, "WINDOW STEP")
  equal(c.adapter:enc(3, 100).code, "WINDOW_MOVED"); equal(c.adapter:screen_model().window_start, 33)
  local model = c.adapter:screen_model()
  equal(model.window_end, 96); equal(model.window_start_label, "3.1.2")
  check(model.at_window_end, "window view reports its bounded end")
end)

test("READY editor applies selected-lane sensitivity and cycles paint policy without changing other lanes", function()
  local c = context(); c.runtime.machine.state = "READY"
  c.runtime.machine.bank = { bpm = 120, timeline_cells = 64, window_start = 0,
    sensitivities = { BD = .5, SD = .2, CYM = .3 }, lanes = { BD = {}, SD = {}, CYM = {}, CYM = {}, BD = {} } }
  c.adapter:enc(2, 1); c.adapter:enc(2, 1) -- sensitivity
  equal(c.adapter:screen_model().ready.field, "SENSITIVITY")
  equal(c.adapter:enc(3, 1).code, "SENSITIVITY_UPDATED")
  equal(c.runtime.machine.bank.sensitivities.BD, .55); equal(c.runtime.machine.bank.sensitivities.SD, .2)
  c.adapter:enc(2, 1)
  equal(c.adapter:enc(3, 1).code, "PAINT_POLICY_UPDATED")
  equal(c.adapter:screen_model().paint_policy, "add")
  equal(c.adapter:shift_paint(-1).code, "PAINT_SHIFTED")
  equal(c.adapter:paint_context().shift, -1)
  equal(c.adapter:reset_paint_shift().code, "PAINT_SHIFT_RESET")
  equal(c.adapter:paint_context().shift, 0)
end)

test("alignment is a K3-applied draft with explicit half/double actions and K2 cancellation", function()
  local c = context(); c.runtime.machine.state = "READY"
  c.runtime.machine.bank = { bpm = 120, timeline_cells = 96, window_start = 0, capture_start_sample = 10,
    capture_end_sample = 1000, origin_sample = 100, sample_rate = 100, source = { beat_positions = { 100, 200, 300 } },
    sensitivities = { BD = 0, SD = 0, CYM = 0 }, lanes = { BD = {}, SD = {}, CYM = {}, CYM = {}, BD = {} } }
  for _ = 1, 4 do c.adapter:enc(2, 1) end
  equal(c.adapter:enc(3, 1).code, "ALIGNMENT_OPENED")
  equal(c.adapter:screen_model().alignment.field, "HALF TEMPO")
  equal(c.adapter:key(3, 1).code, "OK")
  equal(c.calls[#c.calls][1], "alignment"); equal(c.calls[#c.calls][2].bpm, 60)
  c.runtime.machine.state = "READY"
  c.adapter:enc(3, 1); c.adapter:enc(3, 1)
  equal(c.adapter:key(2, 1).code, "ALIGNMENT_CANCELLED")
end)

test("a rejected correction says so instead of looking unchanged", function()
  -- apply_alignment can refuse - the retained audio is gone after a reload or
  -- Save As, for one - and the draft is deliberately kept so the player does
  -- not lose their work. The screen went on reading ALIGNMENT / <field>
  -- exactly as before the attempt, so the refusal was invisible: the player
  -- pressed K3 and nothing appeared to happen.
  local c = context(); c.runtime.machine.state = "READY"
  c.runtime.machine.bank = { bpm = 120, timeline_cells = 96, window_start = 0, capture_start_sample = 10,
    capture_end_sample = 1000, origin_sample = 100, sample_rate = 100, source = { beat_positions = { 100, 200, 300 } },
    sensitivities = { BD = 0, SD = 0, CYM = 0 }, lanes = { BD = {}, SD = {}, CYM = {}, BASS = {} } }
  function c.runtime:apply_alignment(draft)
    return { code = "CAPTURE_AUDIO_UNAVAILABLE", ok = false }
  end
  for _ = 1, 4 do c.adapter:enc(2, 1) end
  equal(c.adapter:enc(3, 1).code, "ALIGNMENT_OPENED")
  local before = c.adapter:screen_model().status
  equal(c.adapter:key(3, 1).code, "CAPTURE_AUDIO_UNAVAILABLE")
  local after = c.adapter:screen_model()
  check(after.alignment.active, "a refused correction keeps the draft to edit or cancel")
  -- The screen renderer draws the alignment sub-model, not the status line, so
  -- the refusal has to reach it there or it never reaches the player.
  equal(after.alignment.error, "CAPTURE AUDIO UNAVAILABLE",
    "the refusal must reach the sub-model the screen actually draws")
  check(after.status ~= before, "a refused correction must change what the screen says")
  equal(after.status, "CAPTURE AUDIO UNAVAILABLE")

  -- Editing the draft is a fresh attempt, so the refusal stops being shown.
  c.adapter:enc(3, 1)
  equal(c.adapter:screen_model().status, "ALIGNMENT / " .. c.adapter:screen_model().alignment.field)
  equal(c.adapter:screen_model().alignment.error, nil, "editing the draft clears the refusal")
end)

test("worker readiness, poll and transport-start invalidation have explicit adapter hooks", function()
  local c = context()
  equal(c.adapter:screen_model().status, "NOT READY")
  check(not c.adapter:screen_model().worker_ready)
  check(c.adapter:enter().ok); equal(c.adapter:screen_model().status, "EMPTY")
  check(c.adapter:screen_model().worker_ready)
  equal(c.adapter:poll().code, "NO_EVENT")
  c.runtime.machine.state = "READY"; c.adapter:grid_key(1, 2, 1); c.adapter:grid_key(1, 2, 0)
  check(c.adapter:transport_started().ok)
  equal(c.adapter:key(3, 1).code, "STOP_SEQUENCER", "Start leaves transport gated and dismisses its modal")
  check(c.adapter:transport_stopped().ok)
end)

if #failures > 0 then io.stderr:write(table.concat(failures, "\n") .. "\n"); os.exit(1) end
print("rhythm_doctor ui adapter: " .. count .. " tests passed")
