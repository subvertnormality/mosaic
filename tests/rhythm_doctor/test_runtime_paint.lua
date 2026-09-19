-- Runtime paint integration: a displayed Rhythm Doctor context reaches the
-- native source adapter only after a valid second Paint action.  This is an
-- integration regression for PLAN.md "Painting into the current pattern".
package.path = "./lib/?.lua;./lib/?/init.lua;" .. package.path

local Bank = require("rhythm_doctor.bank")
local Runtime = require("rhythm_doctor.runtime")

local checks = 0
local function check(value, message)
  checks = checks + 1
  assert(value, message or "check failed")
end
local function equal(actual, expected, message)
  check(actual == expected, (message or "values differ") .. ": " .. tostring(actual) .. " ~= " .. tostring(expected))
end
local function copy(value)
  if type(value) ~= "table" then return value end
  local out = {}
  for key, item in pairs(value) do out[key] = copy(item) end
  return out
end

local source = { revision = 7, trig_values = {}, velocity_values = {}, lengths = {} }
for step = 1, 64 do source.trig_values[step], source.velocity_values[step], source.lengths[step] = 0, 100, 0 end
local writes, reprojections = 0, 0
local worker = { open = function() return { send = function() return true end, poll = function() return nil end } end }
local runtime = Runtime.new({
  project_id = "fixture.ptn", worker = worker, now = function() return 0 end, transport_stopped = function() return true end,
  paint = {
    adapter = { trig_field = "trig_values", velocity_field = "velocity_values", length_field = "lengths", on = 1, off = 0 },
    read_source = function() return copy(source) end,
    write_source = function(_, snapshot, expected_revision)
      if expected_revision ~= source.revision then return nil, { code = "PATTERN_CHANGED" } end
      source = copy(snapshot); source.revision = expected_revision + 1; writes = writes + 1
      return copy(source)
    end,
    reproject = function() reprojections = reprojections + 1; return true end,
  },
})

local project_id = Runtime.project_identity("fixture.ptn")
local bank = assert(Bank.build({ project_id = project_id, generation = 4, analysis_revision = 2,
  sample_rate = 100, capture_start_sample = 0, capture_end_sample = 1000, origin_sample = 0, bpm = 120,
  candidates = { { lane = "CYM", sample_index = 0, velocity = 81, confidence = 1 } },
}))
runtime.machine.project_id, runtime.machine.generation, runtime.machine.analysis_revision = project_id, 4, 2
runtime.machine.state, runtime.machine.bank = "READY", bank
local context = { project_id = project_id, generation = 4, analysis_revision = 2, state = "READY", lane = "CYM",
  window_start = 0, window_revision = 1, policy = "add", shift = 0, thresholds = bank.sensitivities }
local target = { project_id = project_id, song_slot = 1, pattern_id = 2 }

local preview = assert(runtime:paint_preview(context, target))
equal(preview.target.revision, 7, "preview pins native source revision")
equal(writes, 0, "preview never writes")
assert(runtime:paint_commit(context, preview, false))
equal(source.trig_values[1], 1, "commit writes the native trig field")
equal(source.velocity_values[1], 81, "commit writes detected velocity to native field")
equal(source.lengths[1], 1, "commit writes the default hit length")
equal(writes, 1, "one confirmed paint is one source mutation")
equal(reprojections, 1, "commit reprojects shared source patterns")

local stale = assert(runtime:paint_preview(context, target))
context.window_revision = 2
local value, problem = runtime:paint_commit(context, stale, false)
check(value == nil and problem.code == "STALE_PREVIEW", "new displayed window invalidates an old preview")
equal(writes, 1, "stale preview cannot write")

runtime:project_loaded("replacement.ptn")
context.project_id = Runtime.project_identity("replacement.ptn")
context.state = "READY"
value, problem = runtime:paint_undo(context, { project_id = context.project_id, song_slot = 1, pattern_id = 2 })
check(value == nil and problem.code == "NO_UNDO", "project replacement clears session-only paint history")

print("rhythm_doctor runtime paint: " .. checks .. " checks")
