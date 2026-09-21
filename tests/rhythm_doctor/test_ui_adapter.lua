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

test("the Record key stops a capture that has enough audio, without reaching for K3", function()
  -- Record starts the take, so Record ends it. Having to cross to K3 to stop
  -- something the grid started is the kind of split a player has to memorise.
  local c = context(); c.runtime.machine.state = "RECORDING"
  c.adapter:set_capture_progress({ enough_audio = true, acquired_beats = 16, tempo = 120, source = "manual" })
  equal(c.adapter:grid_key(1, 2, 1).code, "OK")
  equal(c.calls[#c.calls][1], "finish", "Record must finish the capture itself")
  check(c.calls[#c.calls][2], "and finish it as a complete take")
  for _, call in ipairs(c.calls) do
    check(call[1] ~= "record_action", "no modal: the player asked to stop, not to discard")
  end
  equal(c.adapter:grid_key(1, 2, 0).code, "RELEASE_CONSUMED", "the release is still consumed")
end)

test("the Record key still offers to discard a take that has too little audio", function()
  -- Finishing early is not possible, so the gesture keeps its old meaning
  -- rather than silently doing nothing: abandoning a bad take stays reachable.
  local c = context(); c.runtime.machine.state = "RECORDING"; c.runtime.next_operation = "cancel_capture"
  local value = c.adapter:grid_key(1, 2, 1)
  equal(value.operation, "cancel_capture", "Record offers to abandon the take")
  equal(c.calls[#c.calls][1], "record_action")
end)

test("the screen says the Record key can finish, because that is now true", function()
  local c = context(); c.runtime.machine.state = "RECORDING"
  c.adapter:set_capture_progress({ enough_audio = true, acquired_beats = 16, tempo = 120, source = "manual" })
  local model = c.adapter:screen_model()
  check(model.status:find("REC") ~= nil, "the status must name the Record key: " .. tostring(model.status))
  check(#model.status <= 19, "the status row shares the screen with the doctor: " .. tostring(model.status))
end)

test("a tempo the detector never found is not shown as one it did", function()
  -- The backend returns a default of 120 when it finds no usable periodicity.
  -- Presenting that as AUTO tells the player the grid was measured from their
  -- playing, and every trig is painted onto it.
  local c = context()
  c.runtime.machine.state = "READY"
  c.runtime.machine.bank = { bpm = 120, tempo_mode = "auto", tempo_detected = false,
    timeline_cells = 64, window_start = 0, sensitivities = {}, candidates = {}, lanes = {} }
  local model = c.adapter:screen_model()
  check(model.tempo_source ~= "auto", "a default tempo must not read as auto detection")
  equal(model.tempo_detected, false, "the model carries the fact for the renderer")
  check(#string.format("%.1f BPM / %s", model.tempo, model.tempo_source) <= 19,
    "the tempo row shares the screen with the doctor")

  c.runtime.machine.bank.tempo_detected = true
  equal(c.adapter:screen_model().tempo_source, "auto", "a real detection still reads as auto")

  c.runtime.machine.bank.tempo_mode, c.runtime.machine.bank.tempo_detected = "manual", false
  equal(c.adapter:screen_model().tempo_source, "manual", "a tempo the player set is theirs, not a fallback")
end)

test("lane keys select BD, SD and CYM, ignore their releases, and leave the retired columns inert", function()
  local c = context()
  for index, lane in ipairs({ "BD", "SD", "CYM" }) do
    equal(c.adapter:grid_key(index + 2, 2, 1).code, "LANE_SELECTED")
    equal(c.adapter:screen_model().lane, lane)
    equal(c.adapter:grid_key(index + 2, 2, 0).code, "UNCLAIMED")
  end
  equal(c.adapter:grid_key(2, 2, 1).code, "UNCLAIMED", "reserved column has no legacy fader effect")
  -- Columns 6 and 7 carried BASS and OHH before those lanes were withdrawn.
  -- They must not silently select a lane now, or a player pressing where a
  -- lane used to be would get an unrelated one.
  equal(c.adapter:grid_key(6, 2, 1).code, "UNCLAIMED", "the withdrawn BASS column stays inert")
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

-- The sequencer has to be stopped to record, because capture takes over the
-- audio input and analysis rewrites the bank underneath whatever is on the
-- screen. Reading a bank that has already been analysed needs none of that,
-- and the rest of the Trigger Editor lets you paint while the sequencer runs.
test("running transport gates capture but leaves an analysed bank usable", function()
  local c = context(); c.set_stopped(false); c.runtime.machine.state = "READY"
  equal(c.adapter:grid_key(1, 2, 1).code, "STOP_SEQUENCER", "Record still needs a stopped sequencer")
  equal(c.adapter:key(3, 1).code, "STOP_SEQUENCER", "and so does finishing a capture")
  equal(#c.calls, 0, "nothing reached the recorder")
  equal(c.adapter:grid_key(4, 2, 1).code, "LANE_SELECTED", "choosing a lane reads the bank and is allowed")
  equal(c.adapter:screen_model().status, "READY",
    "a usable bank must not report itself as blocked")
end)

-- Everything that only reads a finished bank, or writes to a pattern the way
-- every other algorithm does, stays available while the sequencer runs.
test("an analysed bank browses, adjusts and paints while the sequencer plays", function()
  local c = context()
  local bank = {
    version = 4, project_id = "p", bpm = 120, sample_rate = 48000,
    capture_start_sample = 0, capture_end_sample = 1920000, origin_sample = 0,
    timeline_cells = 320, samples_per_cell = 6000, window_start = 0,
    phrase_start_cell = 8, phrase_confidence = .75,
    lane_names = { "BD", "SD", "CYM" },
    sensitivities = { BD = .5, SD = .5, CYM = .5 }, lanes = { BD = {}, SD = {}, CYM = {} },
    candidates = {}, source = { beat_positions = { 0, 24000, 48000, 72000 } },
  }
  c.runtime.machine.state, c.runtime.machine.bank = "READY", bank
  local Bank = require('rhythm_doctor.bank')
  c.runtime.set_window_start = function(_, value)
    local low, high = Bank.window_bounds(bank)
    bank.window_start = math.max(low, math.min(high, math.floor(value)))
    return { ok = true, code = "WINDOW_MOVED" }
  end
  local sensitivity = nil
  c.runtime.set_sensitivity = function(_, lane, value)
    sensitivity = { lane = lane, value = value }
    bank.sensitivities[lane] = value
    return { ok = true, code = "SENSITIVITY_UPDATED" }
  end

  c.set_stopped(false)
  equal(c.adapter:select_lane("SD").code, "LANE_SELECTED", "lanes are selectable while playing")
  equal(c.adapter:nudge_window(1).code, "WINDOW_MOVED", "the window steps while playing")
  equal(bank.window_start, 1)
  equal(c.adapter:page_window(1).code, "WINDOW_MOVED", "and pages while playing")
  equal(c.adapter:jump_to_phrase_start().code, "WINDOW_MOVED", "and returns to the phrase start")
  equal(bank.window_start, 8)
  equal(c.adapter:shift_paint(1).code, "PAINT_SHIFTED", "a preview can be nudged while playing")
  equal(c.adapter:reset_paint_shift().code, "PAINT_SHIFT_RESET")

  -- Sensitivity and paint policy read the bank and change what the preview
  -- would contain; neither touches the recorder.
  c.adapter.ready_field = 3
  equal(c.adapter:enc(3, 1).code, "SENSITIVITY_UPDATED", "sensitivity is adjustable while playing")
  equal(sensitivity.lane, "SD")
  c.adapter.ready_field = 4
  equal(c.adapter:enc(3, 1).code, "PAINT_POLICY_UPDATED", "so is the paint policy")
  c.adapter.ready_field = 1
  equal(c.adapter:enc(3, 1).code, "WINDOW_MOVED", "and the window encoder still moves")

  -- Re-analysis rewrites the bank and needs the recorder, so it stays gated
  -- even though the rest of the READY editor is open.
  c.adapter.ready_field = 5
  equal(c.adapter:enc(3, 1).code, "STOP_SEQUENCER", "alignment re-analyses and must wait for a stop")
  equal(c.adapter.alignment_draft, nil, "and opens no draft while playing")
  equal(c.adapter:set_capture_mode("auto").code, "STOP_SEQUENCER", "capture setup stays gated")
  equal(c.adapter:record_pressed().code, "STOP_SEQUENCER", "and Record stays gated")
end)

-- A preview armed while stopped used to be thrown away the moment the
-- sequencer started, which made "arm paint, start playing, commit" impossible
-- even once painting itself was allowed.
test("starting the sequencer keeps an armed paint preview but drops capture drafts", function()
  local c = context()
  c.runtime.machine.state = "READY"
  c.adapter.active_paint_preview = { marker = true }
  c.adapter.setup_draft = { capture_mode = "auto" }
  c.adapter.alignment_draft = { bpm = 120 }
  c.adapter:transport_started()
  equal(c.adapter.active_paint_preview ~= nil, true, "the armed preview survives the start")
  equal(c.adapter.setup_draft, nil, "a capture setup draft does not")
  equal(c.adapter.alignment_draft, nil, "and neither does an alignment draft")
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

-- A capture failure is the one message a player is most likely to meet, and a
-- raw protocol code neither fits the screen nor says what to do about it.
do
  local Adapter = require('rhythm_doctor.ui_adapter')
  local function check(condition, message) assert(condition, message) end
  check(Adapter.readable("BUSY") == "ALREADY CAPTURING",
    "pressing Record during a capture must say what is going on")
  check(Adapter.readable("PUBLISH_TIMEOUT") == "SAVE TIMED OUT",
    "a capture that never lands must say so in words")
  check(#Adapter.readable("INPUT_RESOURCE_BUSY") < #"INPUT_RESOURCE_BUSY",
    "the message must be shorter than the code it replaces")
  for code, text in pairs(Adapter.MESSAGES) do
    check(#text <= 18, code .. " is too wide for the status row: " .. text)
    check(text:match("^[A-Z0-9 /]+$") ~= nil, code .. " must stay in the screen's own vocabulary")
  end

  -- The map is only worth having if it covers what the recorder can actually
  -- say. It was written for a JACK worker that no longer exists, so almost
  -- every real failure fell through to its raw protocol code.
  local source = assert(io.open("./lib/rhythm_doctor/softcut_recorder.lua")):read("*a")
  local emitted = {}
  for code in source:gmatch("capture_error = '([A-Z_]+)'") do emitted[code] = true end
  check(next(emitted) ~= nil, "the recorder must emit some failure codes to check against")
  for code in pairs(emitted) do
    check(Adapter.MESSAGES[code] ~= nil,
      "the recorder can report " .. code .. " and the screen has no words for it")
  end
  for code in pairs(Adapter.MESSAGES) do
    check(emitted[code] ~= nil,
      "nothing can report " .. code .. " any more; the phrasing is for a worker that is gone")
  end
  -- An unmapped code stays visible rather than being swallowed.
  check(Adapter.readable("SOME_NEW_PROBLEM") == "SOME NEW PROBLEM", "unknown codes are opened out")
  check(Adapter.readable(nil) == "FAILED", "a missing code still says something")
  print('ui_adapter readable status: 5 tests passed')
end

-- Phrase navigation. The centre button returns to the calculated start of the
-- four-bar phrase and the side buttons page through the recording from there.
do
  local c = context()
  local bank = {
    version = 3, project_id = "p", bpm = 120, sample_rate = 48000,
    -- Five phrases of recording, so paging has somewhere to go: a timeline
    -- only one window longer than the window itself clamps on the first press
    -- and proves nothing about the step size.
    capture_start_sample = 0, capture_end_sample = 1920000, origin_sample = 0,
    timeline_cells = 320, samples_per_cell = 6000, window_start = 0,
    phrase_start_cell = 8, phrase_confidence = .75,
    sensitivities = { BD = 0, SD = 0, CYM = 0 }, lanes = { BD = {}, SD = {}, CYM = {} },
    candidates = {}, source = { beat_positions = { 0, 24000, 48000, 72000 } },
  }
  c.runtime.machine.state, c.runtime.machine.bank = "READY", bank
  local moved = nil
  -- Mirrors Runtime, which routes every window move through the bank's bounds.
  -- A stub that simply recorded the request would let the adapter appear to
  -- scroll off the end of the timeline and the test would never notice.
  local Bank = require('rhythm_doctor.bank')
  c.runtime.set_window_start = function(_, value)
    local low, high = Bank.window_bounds(bank)
    moved = math.max(low, math.min(high, math.floor(value)))
    bank.window_start = moved
    return { ok = true, code = "WINDOW_MOVED" }
  end

  equal(c.adapter:jump_to_phrase_start().code, "WINDOW_MOVED", "the centre button moves the window")
  equal(moved, 8, "the centre button lands on the calculated phrase start")

  c.adapter:page_window(1)
  equal(moved, 72, "paging forward advances a whole four-bar phrase")
  c.adapter:page_window(-1)
  equal(moved, 8, "paging back returns by the same phrase")

  -- The window rule is the bank's, so paging cannot leave the timeline.
  for _ = 1, 10 do c.adapter:page_window(1) end
  equal(moved, 256, "paging forward stops at the last whole window")
  for _ = 1, 10 do c.adapter:page_window(-1) end
  equal(moved, 0, "paging back stops at the timeline start")

  -- A press of a browse button is worth one step, the same as a press of the
  -- same button in every other algorithm. Paging a whole phrase is the held
  -- gesture, so the two must not be the same size.
  c.adapter:nudge_window(1)
  equal(moved, 1, "one press moves a single step")
  c.adapter:nudge_window(1)
  equal(moved, 2, "and presses accumulate one step at a time")
  c.adapter:nudge_window(-1)
  equal(moved, 1, "a press the other way steps back by one")
  equal(c.adapter:nudge_window(0).code, "WINDOW_MOVED", "a zero step is accepted and goes nowhere")
  equal(moved, 1)
  equal(c.adapter:nudge_window(.5).code, "INVALID_SHIFT", "a fractional step is refused")
  equal(c.adapter:nudge_window("1").code, "INVALID_SHIFT", "and so is a non-number")
  for _ = 1, 3 do c.adapter:nudge_window(-1) end
  equal(moved, 0, "stepping back stops at the timeline start")

  -- Every move reports where it landed and whether it actually went anywhere.
  -- Clamping makes a refused move and an absorbed one both look like success,
  -- and a caller that cannot tell them apart tells the player it advanced
  -- while the window stood still at the end of the recording.
  local held = c.adapter:nudge_window(-1)
  equal(held.moved, false, "a move absorbed by the timeline start reports no movement")
  equal(held.window_start, 0, "and still says where the window is")
  equal(held.window_label, "1.1.1", "named the way the screen names a position")
  local stepped = c.adapter:nudge_window(1)
  equal(stepped.moved, true, "a move that lands somewhere new says so")
  equal(stepped.window_label, "1.1.2")
  local paged = c.adapter:page_window(1)
  equal(paged.moved, true)
  equal(paged.window_start, 65, "a phrase is sixty-four cells wide")
  local phrase = c.adapter:jump_to_phrase_start()
  equal(phrase.moved, true)
  equal(phrase.window_start, 8, "the centre button returns to the detected phrase start")
  equal(c.adapter:jump_to_phrase_start().moved, false,
    "and pressing it again reports that the window was already there")

  -- Every browse gesture retires the paint preview: a preview describes the
  -- window it was taken from and cannot outlive it.
  local revision = c.adapter.window_revision
  c.adapter:nudge_window(1)
  equal(c.adapter.window_revision > revision, true, "a step invalidates the preview")
  revision = c.adapter.window_revision
  c.adapter:page_window(1)
  equal(c.adapter.window_revision > revision, true, "a phrase page invalidates the preview")
  revision = c.adapter.window_revision
  c.adapter:jump_to_phrase_start()
  equal(c.adapter.window_revision > revision, true, "returning to the phrase start invalidates the preview")

  -- Browsing is a stopped-transport action, like every other window move.
  -- Browsing reads a finished bank, so it keeps working while the sequencer
  -- runs; only capture and re-analysis need a stop.
  c.set_stopped(false)
  equal(c.adapter:nudge_window(1).code, "WINDOW_MOVED", "a step still works while the sequencer runs")
  equal(c.adapter:page_window(1).code, "WINDOW_MOVED")
  equal(c.adapter:jump_to_phrase_start().code, "WINDOW_MOVED")
  c.set_stopped(true)

  -- The alignment editor opens on the detected phrase start rather than on the
  -- first beat of the capture, so confirming without editing keeps the
  -- detector's answer instead of silently replacing it with beat one.
  c.adapter.ready_field = 5
  c.adapter:enc(3, 1)
  equal(c.adapter.alignment_draft ~= nil, true, "the alignment editor opens")
  equal(c.adapter.alignment_draft.start_beat, 3, "START BEAT opens on the beat holding the phrase start")
end

-- Ten lanes from the remote server must reach ten grid buttons. "Mosaic
-- assigns all data to more buttons than DSP" is the whole point of the server;
-- a grid hard-coded to three columns would silently discard seven lanes.
do
  local c = context()
  local remote = { "KICK", "SNARE", "TOMS", "HIHAT", "CYMBALS",
                   "BASS", "GUITAR", "PIANO", "VOCALS", "OTHER" }
  local sensitivities, lanes = {}, {}
  for _, lane in ipairs(remote) do sensitivities[lane] = 0; lanes[lane] = {} end
  c.runtime.machine.state = "READY"
  c.runtime.machine.bank = {
    version = 4, project_id = "p", bpm = 120, sample_rate = 48000,
    capture_start_sample = 0, capture_end_sample = 480000, origin_sample = 0,
    timeline_cells = 80, samples_per_cell = 6000, window_start = 0,
    phrase_start_cell = 0, phrase_confidence = 0,
    lane_names = remote, sensitivities = sensitivities, lanes = lanes,
    candidates = {}, source = {},
  }
  -- Ten lanes across two rows of five. The cells are asked for rather than
  -- assumed, so this proves every declared lane is reachable wherever the
  -- layout puts it.
  local cells = c.adapter:lane_cells()
  equal(#cells, #remote, "every remote lane has a cell")
  for index, lane in ipairs(remote) do
    local cell = cells[index]
    equal(cell.lane, lane)
    local result = c.adapter:grid_key(cell.x, cell.y, 1)
    equal(result.code, "LANE_SELECTED", lane .. " is selectable at " .. cell.x .. "," .. cell.y)
    equal(c.adapter.lane, lane, lane .. " becomes the selected lane")
  end
  equal(c.adapter:grid_key(8, 2, 1).code, "UNCLAIMED", "the column past the lane block stays inert")
  equal(c.adapter:grid_key(8, 3, 1).code, "UNCLAIMED")

  -- With no bank the grid still offers the lanes the device itself produces,
  -- so the page is usable before anything has been recorded.
  c.runtime.machine.state, c.runtime.machine.bank = "EMPTY", nil
  equal(c.adapter:grid_key(5, 2, 1).code, "LANE_SELECTED", "the default lane set is addressable")
  equal(c.adapter:grid_key(6, 2, 1).code, "UNCLAIMED", "and stops at three columns")
  equal(c.adapter:grid_key(3, 3, 1).code, "UNCLAIMED", "with no second row in use")
end

-- The blocks above run after this file's first report. `equal` raises rather
-- than collecting, so they do fail loudly, but the pcall-based `test` helper
-- collects into `failures` -- and nothing reads it past line 343. Re-check it
-- here so a failure in an appended block cannot pass silently.
-- The lane row ran from column 3 rightwards without a limit, so a ten lane
-- analysis reached column 12 -- where the algorithm fader starts. Pressing
-- the tenth lane also moved the algorithm fader and threw the player out of
-- Rhythm Doctor. Lanes now occupy two rows of five, clear of the faders at
-- columns 12..16.
do
  local Adapter = require('rhythm_doctor.ui_adapter')
  local c = context()
  local ten = { "KICK", "SNARE", "HIHAT", "TOMS", "CYMBALS", "RIDE", "CLAP", "PERC", "BASS", "OTHER" }
  c.runtime.machine.state = "READY"
  c.runtime.machine.bank = { lane_names = ten, lanes = {}, sensitivities = {} }

  local cells = c.adapter:lane_cells()
  equal(#cells, 10, "every declared lane gets a cell")
  equal(cells[1].x, 3); equal(cells[1].y, 2); equal(cells[1].lane, "KICK")
  equal(cells[5].x, 7); equal(cells[5].y, 2, "the first five sit on row two")
  equal(cells[6].x, 3); equal(cells[6].y, 3, "the sixth wraps to row three")
  equal(cells[10].x, 7); equal(cells[10].y, 3, "and the tenth is the last cell of row three")
  for _, cell in ipairs(cells) do
    check(cell.x >= 3 and cell.x <= 7,
      "lane column " .. cell.x .. " would collide with the algorithm or bank-mask fader")
    check(cell.y == 2 or cell.y == 3, "lanes use only the two rows they own")
  end

  equal(c.adapter:lane_at(3, 2), "KICK", "the grid resolves a press on row two")
  equal(c.adapter:lane_at(7, 3), "OTHER", "and on row three")
  equal(c.adapter:lane_at(8, 2), nil, "a column past the lane block is not a lane")
  equal(c.adapter:lane_at(12, 2), nil, "the algorithm fader is never a lane")
  equal(c.adapter:lane_at(12, 3), nil, "and neither is the bank-mask fader")
  equal(c.adapter:lane_at(1, 2), nil, "Record is not a lane")
  equal(c.adapter:lane_at(3, 4), nil, "the sequencer rows are not lanes")

  equal(c.adapter:grid_key(7, 3, 1).code, "LANE_SELECTED", "the tenth lane is selectable")
  equal(c.adapter:screen_model().lane, "OTHER")
  equal(c.adapter:grid_key(12, 2, 1).code, "UNCLAIMED",
    "a press on the algorithm fader must never be claimed as a lane")

  -- A short lane set leaves the rest of the block dark rather than lighting
  -- cells that do nothing.
  c.runtime.machine.bank = { lane_names = { "BD", "SD", "CYM" }, lanes = {}, sensitivities = {} }
  equal(#c.adapter:lane_cells(), 3)
  equal(c.adapter:lane_at(6, 2), nil, "an unused column in the block is inert")
  equal(c.adapter:lane_at(3, 3), nil, "and so is the whole second row")

  -- Two rows of five is the ceiling; a backend declaring more must not spill.
  local twelve = {}
  for i = 1, 12 do twelve[i] = "L" .. i end
  c.runtime.machine.bank = { lane_names = twelve, lanes = {}, sensitivities = {} }
  equal(#c.adapter:lanes(), 10, "the addressable lane set stops at ten")
  equal(#c.adapter:lane_cells(), 10, "and so does the grid block")
  equal(Adapter.MAX_LANE_COLUMNS, 10, "ten is five columns on each of two rows")
end

if #failures > 0 then io.stderr:write(table.concat(failures, "\n") .. "\n"); os.exit(1) end
print("rhythm_doctor ui adapter: phrase navigation and remote lane columns checked")

-- The grid page asks the adapter for the lane set. It used to keep its own
-- hardcoded {"BD","SD","CYM"}, so a ten lane analysis lit three columns, the
-- rest were inert, and the selected lane defaulted to a lane the bank did not
-- contain -- the capture succeeded and nothing could be selected.
do
  local c = context()
  equal(#c.adapter:lanes(), 3, "with no bank the device's own lanes are offered")
  equal(c.adapter:lanes()[1], "BD", "and BD is first")

  local remote = { "BASS", "CYMBALS", "GUITAR", "HIHAT", "KICK",
                   "OTHER", "PIANO", "SNARE", "TOMS", "VOCALS" }
  local sens, lanes = {}, {}
  for _, lane in ipairs(remote) do sens[lane] = 0; lanes[lane] = {} end
  c.runtime.machine.state = "READY"
  c.runtime.machine.bank = {
    version = 4, project_id = "p", bpm = 125, sample_rate = 48000,
    capture_start_sample = 0, capture_end_sample = 1749407, origin_sample = 1920,
    timeline_cells = 303, samples_per_cell = 5760, window_start = 0,
    phrase_start_cell = 37, phrase_confidence = .06,
    lane_names = remote, sensitivities = sens, lanes = lanes, candidates = {}, source = {},
  }
  equal(#c.adapter:lanes(), 10, "a ten lane bank offers ten lanes")
  for index, lane in ipairs(remote) do
    equal(c.adapter:lanes()[index], lane, "lane " .. index .. " is " .. lane)
  end

  -- Never more lanes than the two rows of five have room for.
  local many = {}
  for i = 1, 20 do many[i] = "L" .. i end
  c.runtime.machine.bank.lane_names = many
  equal(#c.adapter:lanes(), 10, "the lane set is capped at the cells that exist")
end

-- A remote analysis replaces the whole lane set, so the lane the adapter was
-- last working on can stop existing without anyone touching it. Reading a
-- stale lane asks the bank for a window it does not have.
do
  local c = context()
  local remote = { "BASS", "CYMBALS", "GUITAR", "HIHAT", "KICK",
                   "OTHER", "PIANO", "SNARE", "TOMS", "VOCALS" }
  local sens, lanes = {}, {}
  for _, lane in ipairs(remote) do sens[lane] = .5; lanes[lane] = {} end
  c.runtime.machine.state = "READY"
  c.runtime.machine.bank = {
    version = 4, project_id = "p", bpm = 125, sample_rate = 48000,
    capture_start_sample = 0, capture_end_sample = 1749407, origin_sample = 1920,
    timeline_cells = 303, samples_per_cell = 5760, window_start = 0,
    phrase_start_cell = 37, phrase_confidence = .06,
    lane_names = remote, sensitivities = sens, lanes = lanes, candidates = {}, source = {},
  }
  -- The adapter still holds "BD" from construction; the bank has no such lane.
  equal(c.adapter.lane, "BD", "the stored lane is still the device default")
  local model = c.adapter:screen_model()
  equal(model.lane, "BASS", "the screen shows a lane the bank actually holds")
  equal(model.sensitivity, .5, "and its sensitivity resolves instead of coming back nil")
  local ctx = c.adapter:paint_context()
  equal(ctx.lane, "BASS", "and paint works on that lane too")
end
