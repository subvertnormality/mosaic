-- Runtime bridge integration checks, characterisation outside README.
package.path = './lib/?.lua;' .. package.path
local Runtime = require('rhythm_doctor.runtime')
local Bank = require('rhythm_doctor.bank')

local failures, count = {}, 0
local function test(name, body)
  count = count + 1
  local ok, err = pcall(body)
  if not ok then failures[#failures + 1] = name .. ': ' .. tostring(err) end
end
local function equal(actual, expected, message)
  assert(actual == expected, (message or 'values differ') .. ': expected ' .. tostring(expected) .. ', got ' .. tostring(actual))
end
local function check(value, message) assert(value, message or 'expected true') end

local function transport()
  local self = { sent = {}, replies = {}, closed = false }
  function self:send(message) self.sent[#self.sent + 1] = message; return true end
  function self:poll() if #self.replies == 0 then return nil end return table.remove(self.replies, 1) end
  function self:close() self.closed = true end
  return self
end
local function response(request, status)
  return { protocol_version = request.protocol_version, job_id = request.job_id, project_id = request.project_id,
    generation = request.generation, analysis_revision = request.analysis_revision, command = request.command, status = status }
end
local function context()
  local socket, worker, statuses = transport(), { opens = 0, closes = 0 }, {}
  function worker:open() self.opens = self.opens + 1; return socket end
  function worker:close() self.closes = self.closes + 1 end
  local runtime = Runtime.new({ project_id = 'project-a', worker = worker, now = function() return 0 end,
    transport_stopped = function() return true end, on_status = function(code) statuses[#statuses + 1] = code end })
  return runtime, socket, worker, statuses
end

test('enter opens injected nonblocking worker exactly once and record owns controller', function()
  local runtime, socket, worker = context()
  check(runtime:enter().ok)
  check(runtime:enter().ok)
  equal(worker.opens, 1)
  check(runtime:start_capture('manual').ok)
  equal(socket.sent[1].command, 'PREFLIGHT')
end)

test('failed worker startup cannot put the machine into a capture state', function()
  local worker = { open = function() return nil, 'no socket' end }
  local runtime = Runtime.new({ project_id = 'project-a', worker = worker, now = function() return 0 end,
    transport_stopped = function() return true end })
  equal(runtime:start_capture('manual').code, 'WORKER_UNAVAILABLE')
  equal(runtime.machine.state, 'EMPTY')
end)

test('mode entry retries a background worker from bounded polls', function()
  local socket, opens, now = transport(), 0, 0
  local worker = { open = function()
    opens = opens + 1
    if opens < 3 then return nil, 'worker starting' end
    return socket
  end }
  local runtime = Runtime.new({ project_id = 'project-a', worker = worker, now = function() return now end,
    transport_stopped = function() return true end })
  equal(runtime:enter().code, 'WORKER_UNAVAILABLE')
  runtime:poll(); equal(opens, 1, 'rapid polls do not thrash worker connection setup')
  now = .25; runtime:poll(); equal(runtime.machine.state, 'EMPTY')
  now = .50; runtime:poll(); equal(opens, 3)
  check(runtime:start_capture('manual').ok)
end)

test('cleanup waits for native release acknowledgement before closing worker', function()
  local runtime, socket, worker = context()
  runtime:start_capture('manual')
  local preflight = socket.sent[#socket.sent]
  socket.replies[#socket.replies + 1] = response(preflight, 'READY')
  runtime:poll()
  local started = socket.sent[#socket.sent]
  socket.replies[#socket.replies + 1] = response(started, 'STARTED')
  runtime:poll()
  equal(runtime:cleanup().code, 'RELEASING')
  equal(worker.closes, 0)
  local release = socket.sent[#socket.sent]
  equal(release.command, 'RELEASE')
  socket.replies[#socket.replies + 1] = response(release, 'RELEASED')
  runtime:poll()
  equal(worker.closes, 1)
  check(socket.closed)
end)

test('project replacement is deferred by the machine then receives the new identity', function()
  local runtime, socket = context()
  runtime:start_capture('manual')
  local called = false
  equal(runtime:prepare_project_change(function() called = true end).code, 'DEFERRED')
  local release = socket.sent[#socket.sent]
  socket.replies[#socket.replies + 1] = response(release, 'RELEASED')
  runtime:poll()
  check(called)
  check(runtime:project_loaded('project-b').ok)
  equal(runtime.machine.project_id, Runtime.project_identity('project-b'))
end)

test('READY controls clamp the shared window, rebuild one lane sensitivity, and start alignment reanalysis', function()
  local runtime = select(1, context())
  local bank = assert(Bank.build({ project_id = runtime.machine.project_id, generation = 0, analysis_revision = 0,
    sample_rate = 100, capture_start_sample = 0, capture_end_sample = 1000, origin_sample = 0, bpm = 120,
    sensitivities = { BD = .2, SD = .2, CYM = .2 },
    candidates = { { lane = 'BD', sample_index = 10, velocity = 80, confidence = .3 } } }))
  runtime.machine.state, runtime.machine.bank = 'READY', bank
  equal(runtime:set_window_start(999).code, 'WINDOW_MOVED')
  equal(runtime.machine.bank.window_start, 16, 'longest 64-cell view is retained')
  equal(runtime:set_sensitivity('BD', .4).code, 'SENSITIVITY_UPDATED')
  equal(runtime.machine.bank.sensitivities.BD, .4); equal(runtime.machine.bank.sensitivities.SD, .2)
  -- No capture job backs this hand-built bank, so the reanalysis cannot be
  -- dispatched. It must say so and keep the ready bank rather than parking in
  -- REANALYSING waiting for a reply that can never come. The dispatched path
  -- is covered by test_capture_controller's reanalysis lease case.
  local value = runtime:apply_alignment({ bpm = 60, start_beat = 1, fine_start_ms = 0, origin_sample = 0 })
  check(not value.ok, 'an undispatchable correction must not report success')
  equal(runtime.machine.state, 'READY')
  check(runtime.machine.bank ~= nil, 'the ready bank must survive')
  equal(runtime.machine.analysis_revision, 1, 'the attempted lease still consumed a revision')
end)

test('runtime answers the complete project-lifecycle capture-guard interface', function()
  -- project_lifecycle.save_project calls capture_guard:autosave() or
  -- capture_guard:manual_save() UNCONDITIONALLY once a guard is installed,
  -- unlike every other guard hook, which it probes with `and guard.method`.
  -- mosaic.lua installs this runtime as that guard, so a runtime missing
  -- either method makes every project save raise
  -- "attempt to call a nil value" at project_lifecycle.lua:116.
  -- Reproduced by behaviour cases M-MEMORY-007 and M-SAVE-LENGTH-001 in both
  -- timing lanes.
  local runtime = context()
  for _, method in ipairs({ 'autosave', 'manual_save', 'prepare_project_change',
                            'project_loaded', 'serialize_project', 'restore_project' }) do
    check(type(runtime[method]) == 'function', 'runtime must implement guard method ' .. method)
  end
  local auto = runtime:autosave()
  check(type(auto) == 'table', 'autosave must return a decision table')
  equal(auto.code, 'SAVE_NOW', 'an idle runtime must permit autosave')
  local manual = runtime:manual_save()
  check(type(manual) == 'table', 'manual_save must return a decision table')
  equal(manual.code, 'SAVE_NOW', 'an idle runtime must permit a manual save')
end)

test('a recording becomes finishable once it is long enough for a bank window', function()
  -- Nothing in the application ever called set_capture_progress, so
  -- enough_audio was permanently nil: K3 Finish always answered
  -- MORE_AUDIO_NEEDED and no recording could reach analysis.
  local Bank = require('rhythm_doctor.bank')
  local clock = 0
  local socket, worker = transport(), { opens = 0, closes = 0 }
  function worker:open() self.opens = self.opens + 1; return socket end
  function worker:close() self.closes = self.closes + 1 end
  local runtime = Runtime.new({ project_id = 'project-a', worker = worker,
    now = function() return clock end, transport_stopped = function() return true end })
  local idle = runtime:capture_progress()
  check(type(idle) == 'table', 'capture progress must always be a table')
  equal(idle.enough_audio, false, 'an unstarted capture is not finishable')

  check(runtime:enter().ok)
  runtime:start_capture('manual')
  runtime:_capture_start('manual', runtime.machine.token)
  runtime:capture_acquiring()
  local needed = Bank.minimum_capture_seconds(Bank.SLOWEST_SUPPORTED_BPM)
  check(type(needed) == 'number' and needed > 0, 'bank must state the capture length it needs')

  clock = needed / 2
  equal(runtime:capture_progress().enough_audio, false, 'half a window is not enough audio')
  clock = needed
  equal(runtime:capture_progress().enough_audio, true, 'a full window is enough audio')
end)

test('the bank states the capture length its own window rule requires', function()
  local Bank = require('rhythm_doctor.bank')
  equal(Bank.minimum_capture_seconds(120), Bank.WINDOW_CELLS * 15 / 120)
  -- A slower tempo needs a longer capture for the same number of cells.
  check(Bank.minimum_capture_seconds(60) > Bank.minimum_capture_seconds(120))
  equal(Bank.minimum_capture_seconds(0), nil, 'an out-of-range tempo has no answer')
  equal(Bank.minimum_capture_seconds('x'), nil)
end)

test('finish is offered only once a bank is buildable at any supported tempo', function()
  -- Eligibility used the assumed 120 BPM, so Finish lit at eight seconds. A
  -- recording of slower music then failed NOT_ENOUGH_ALIGNED_AUDIO after the
  -- user had already committed, losing the take.
  local Bank = require('rhythm_doctor.bank')
  local clock = 0
  local socket, worker = transport(), {}
  function worker:open() return socket end
  function worker:close() end
  local runtime = Runtime.new({ project_id = 'project-slow', worker = worker,
    now = function() return clock end, transport_stopped = function() return true end })
  check(runtime:enter().ok)
  runtime:start_capture('manual')
  runtime:_capture_start('manual', runtime.machine.token)
  runtime:capture_acquiring()

  local slowest = Bank.minimum_capture_seconds(Bank.SLOWEST_SUPPORTED_BPM)
  check(type(slowest) == 'number', 'the bank must state its slowest supported tempo')
  check(slowest > Bank.minimum_capture_seconds(Bank.DEFAULT_BPM),
    'the slowest supported tempo must need more audio than the assumed one')

  clock = Bank.minimum_capture_seconds(Bank.DEFAULT_BPM)
  equal(runtime:capture_progress().enough_audio, false,
    'audio sufficient only at the assumed tempo must not offer Finish')
  clock = slowest
  equal(runtime:capture_progress().enough_audio, true,
    'audio sufficient at every supported tempo must offer Finish')

  -- A bank really does build from exactly that span at the slowest tempo.
  local bank = Bank.build({ project_id = 'project-slow', generation = 1, analysis_revision = 1,
    sample_rate = 44100, capture_start_sample = 0,
    capture_end_sample = math.floor(44100 * slowest), origin_sample = 0,
    bpm = Bank.SLOWEST_SUPPORTED_BPM, tempo_mode = 'AUTOMATIC',
    sensitivities = {}, candidates = {},
    detector = { backend_id = 'x', backend_sha256 = string.rep('a', 64),
                 template_sha256 = string.rep('b', 64) } })
  check(bank ~= nil, 'the advertised span must actually build a bank')
end)

test('preflight time is not counted as captured audio', function()
  -- The clock started when Record was pressed, so worker launch and JACK
  -- preflight were credited as recorded audio and Finish was offered before
  -- that much sound had been acquired.
  local Bank = require('rhythm_doctor.bank')
  local clock = 0
  local socket, worker = transport(), {}
  function worker:open() return socket end
  function worker:close() end
  local runtime = Runtime.new({ project_id = 'project-preflight', worker = worker,
    now = function() return clock end, transport_stopped = function() return true end })
  check(runtime:enter().ok)
  runtime:start_capture('manual')
  runtime:_capture_start('manual', runtime.machine.token)

  local needed = Bank.minimum_capture_seconds(Bank.SLOWEST_SUPPORTED_BPM)
  clock = 5  -- five seconds spent in preflight, no audio acquired yet
  equal(runtime:capture_progress().captured_seconds, 0,
    'no audio is captured before the recorder reports it started')
  runtime:capture_acquiring()
  clock = 5 + needed / 2
  equal(runtime:capture_progress().captured_seconds, needed / 2,
    'captured audio is measured from the moment acquisition began')
  equal(runtime:capture_progress().enough_audio, false)
  clock = 5 + needed
  equal(runtime:capture_progress().enough_audio, true)
end)

test('an autosave deferred during capture runs once the capture releases', function()
  -- The state machine recorded the deferred save and invoked on_deferred_save
  -- when resources were released, but nothing in the application ever supplied
  -- that callback. The autosave timers had already been stopped, so the save
  -- was simply lost until some later edit primed them again.
  local clock, saves = 0, {}
  local socket, worker = transport(), {}
  function worker:open() return socket end
  function worker:close() end
  local runtime = Runtime.new({ project_id = 'project-save', worker = worker,
    now = function() return clock end, transport_stopped = function() return true end,
    on_deferred_save = function(project_id) saves[#saves + 1] = project_id end })
  check(runtime:enter().ok)
  runtime:start_capture('manual')
  runtime:_capture_start('manual', runtime.machine.token)

  local decision = runtime:autosave()
  check(decision.code ~= 'SAVE_NOW', 'a save must not run while a capture is active')
  equal(#saves, 0, 'the deferred save must not run before the capture releases')

  local token = runtime.machine:job_token()
  runtime.machine:capture_failed(token, 'CAPTURE_FAILED')
  runtime.machine:resources_released(token, true)
  equal(#saves, 1, 'the deferred save was lost when the capture released')

  -- Releasing again must not save a second time.
  runtime.machine:resources_released(token, true)
  equal(#saves, 1, 'the deferred save ran more than once')
end)

test('a correction with no retained capture fails instead of hanging', function()
  -- After a reload or Save As the bank is READY but no capture job survives,
  -- so the reanalysis dispatch is stale and nothing will ever answer. The
  -- dispatch result was discarded, leaving the bank stuck in REANALYSING with
  -- no way back.
  local Bank = require('rhythm_doctor.bank')
  local Machine = require('rhythm_doctor.state_machine')
  local clock = 0
  local socket, worker = transport(), {}
  function worker:open() return socket end
  function worker:close() end
  local runtime = Runtime.new({ project_id = 'project-reload', worker = worker,
    now = function() return clock end, transport_stopped = function() return true end })
  check(runtime:enter().ok)

  local bank = assert(Bank.build{ project_id = runtime.machine.project_id, generation = 1,
    analysis_revision = 1, sample_rate = 8000, capture_start_sample = 0,
    capture_end_sample = 64000, origin_sample = 0, bpm = 120 })
  check(runtime.machine:restore_ready_bank(bank).ok, 'the saved bank must restore')
  equal(runtime.machine.state, Machine.READY)

  local outcome = runtime:apply_alignment({ bpm = 90, start_beat = 1, fine_start_ms = 0 })
  check(not outcome.ok, 'a correction that cannot be dispatched must not report success')
  -- The player sees this code on the screen, so it has to say what actually
  -- went wrong. CORRECTION_FAILED tells them nothing they can act on; the
  -- retained audio is gone and they need to record again.
  equal(outcome.code, 'CAPTURE_AUDIO_UNAVAILABLE',
    'the refusal must name the reason, not just that it failed')
  check(runtime.machine.state ~= Machine.REANALYSING,
    'the bank was left stuck in REANALYSING with no pending analysis')
  check(runtime.machine.bank ~= nil, 'the ready bank must survive a failed correction')
  -- No capture job holds this lease, so nothing will ever acknowledge its
  -- release. Leaving it outstanding blocks saves, the next capture and any
  -- project change just as surely as the REANALYSING hang did.
  check(runtime.machine.resources_are_released,
    'the undispatchable correction left its lease unreleased')
  equal(runtime:autosave().code, 'SAVE_NOW', 'saving must be possible again')
end)

test('a correction does not leak its tempo into later captures or other projects', function()
  -- The confirmed alignment was stored once and never cleared, and the
  -- analysis controller sends it with every ANALYSE. Once the backend began
  -- honouring it, a correction made on one capture silently forced its tempo
  -- and origin onto every capture recorded afterwards, in any project.
  local clock = 0
  local socket, worker = transport(), {}
  function worker:open() return socket end
  function worker:close() end
  local runtime = Runtime.new({ project_id = 'project-leak', worker = worker,
    now = function() return clock end, transport_stopped = function() return true end })
  check(runtime:enter().ok)

  local bank = assert(Bank.build{ project_id = runtime.machine.project_id, generation = 0,
    analysis_revision = 0, sample_rate = 8000, capture_start_sample = 0,
    capture_end_sample = 64000, origin_sample = 0, bpm = 120 })
  runtime.machine.state, runtime.machine.bank = 'READY', bank
  runtime:apply_alignment({ bpm = 77, start_beat = 1, fine_start_ms = 0, origin_sample = 4410 })
  check(runtime.alignment ~= nil, 'the correction must be held for its own lease')

  -- A brand new capture has its own musical timing and must be analysed on
  -- its own terms.
  runtime:start_capture('manual')
  runtime:_capture_start('manual', runtime.machine:job_token())
  equal(runtime.alignment, nil, "a new capture inherited the previous capture's correction")
end)

test('a correction does not survive loading another project', function()
  local clock = 0
  local socket, worker = transport(), {}
  function worker:open() return socket end
  function worker:close() end
  local runtime = Runtime.new({ project_id = 'project-one', worker = worker,
    now = function() return clock end, transport_stopped = function() return true end })
  check(runtime:enter().ok)
  local bank = assert(Bank.build{ project_id = runtime.machine.project_id, generation = 0,
    analysis_revision = 0, sample_rate = 8000, capture_start_sample = 0,
    capture_end_sample = 64000, origin_sample = 0, bpm = 120 })
  runtime.machine.state, runtime.machine.bank = 'READY', bank
  runtime:apply_alignment({ bpm = 77, start_beat = 1, fine_start_ms = 0, origin_sample = 4410 })
  runtime:project_loaded('/data/another.ptn')
  equal(runtime.alignment, nil, "another project inherited the first project's correction")
end)

if #failures > 0 then io.stderr:write(table.concat(failures, '\n') .. '\n'); os.exit(1) end
print('rhythm_doctor runtime: ' .. count .. ' tests passed')
