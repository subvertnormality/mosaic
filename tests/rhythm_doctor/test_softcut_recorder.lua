package.path = './lib/?.lua;' .. package.path
local Recorder = require('rhythm_doctor.softcut_recorder')

local passed = 0
local function check(condition, message)
  if not condition then error(message, 2) end
  passed = passed + 1
end

-- A softcut that remembers every call, so the setup can be asserted rather
-- than assumed: softcut's own defaults suit a delay line, not a capture.
local function fake_softcut()
  local sc = { calls = {}, last = {} }
  local names = { 'enable', 'buffer', 'buffer_clear', 'buffer_clear_channel', 'level', 'pan',
    'level_input_cut', 'rec_level', 'pre_level', 'pre_filter_dry', 'pre_filter_lp',
    'post_filter_dry', 'post_filter_lp', 'rate', 'fade_time', 'loop_start', 'loop_end',
    'loop', 'position', 'rec', 'play', 'buffer_write_stereo' }
  for _, name in ipairs(names) do
    sc[name] = function(...)
      local arguments = { ... }
      sc.calls[#sc.calls + 1] = { name = name, arguments = arguments }
      sc.last[name] = arguments
    end
  end
  return sc
end
local function called(sc, name, a, b, c)
  for _, call in ipairs(sc.calls) do
    if call.name == name and (a == nil or call.arguments[1] == a) and
        (b == nil or call.arguments[2] == b) and (c == nil or call.arguments[3] == c) then return true end
  end
  return false
end

-- A filesystem that only holds what the test puts in it.
local function fake_files()
  local files = { content = {}, removed = {} }
  files.open = function(path, _)
    local body = files.content[path]
    if not body then return nil end
    local cursor = 0
    return {
      seek = function(_, whence) if whence == 'end' then return #body end return cursor end,
      read = function(_, what)
        if what == '*l' then return (body:gsub('\n.*', '')) end
        return body:sub(1, what)
      end,
      close = function() end,
    }
  end
  files.remove = function(path) files.removed[path] = true; files.content[path] = nil; return true end
  return files
end

local function wav(frames, rate, channels, bits)
  local function u32(v) return string.char(v % 256, (v // 256) % 256, (v // 65536) % 256, (v // 16777216) % 256) end
  local function u16(v) return string.char(v % 256, (v // 256) % 256) end
  local data = frames * channels * (bits // 8)
  return 'RIFF' .. u32(36 + data) .. 'WAVE' .. 'fmt ' .. u32(16) .. u16(1) .. u16(channels) ..
    u32(rate) .. u32(rate * channels * (bits // 8)) .. u16(channels * (bits // 8)) .. u16(bits) ..
    'data' .. u32(data)
end

local function context(options)
  options = options or {}
  local sc, files = fake_softcut(), fake_files()
  local clock = { value = 0 }
  local mixer = { levels = {} }
  mixer.level_adc_cut = function(v) mixer.levels[#mixer.levels + 1] = v end
  local shell = {}
  local recorder = Recorder.new({
    directory = '/data/captures', softcut = sc, audio = mixer,
    now = function() return clock.value end,
    execute = function(command) shell[#shell + 1] = command; return true end,
    open_file = files.open, remove = files.remove,
    adc_cut_level = function() return options.adc or 0.25 end,
    publish_timeout_seconds = options.timeout or 20,
  })
  return recorder, sc, files, clock, mixer, shell
end

local IDENTITY = { protocol_version = 1, job_id = 'rd-1', project_id = 'proj', generation = 3, analysis_revision = 2 }
local function message(command, extra)
  local out = {}
  for k, v in pairs(IDENTITY) do out[k] = v end
  out.command = command
  for k, v in pairs(extra or {}) do out[k] = v end
  return out
end

-- The capture setup, which is the part softcut's defaults get wrong.
do
  local recorder, sc, _, _, mixer = context()
  check(recorder:send(message('PREFLIGHT', { seconds = 12, mode = 'manual' })), 'preflight is accepted')
  local ready = recorder:poll()
  check(ready and ready.status == 'READY' and ready.command == 'PREFLIGHT', 'preflight answers READY')
  check(mixer.levels[1] == 1.0, 'the ADC send to softcut is opened for the capture')
  check(called(sc, 'buffer', 1, 1) and called(sc, 'buffer', 2, 2), 'each voice owns one buffer, for a stereo write')
  check(called(sc, 'buffer_clear_channel', 1) and called(sc, 'buffer_clear_channel', 2),
    'both channels are cleared whole, guard samples included')
  check(called(sc, 'level_input_cut', 1, 1, 1.0) and called(sc, 'level_input_cut', 2, 2, 1.0),
    'each input feeds its own voice')
  check(called(sc, 'level_input_cut', 2, 1, 0) and called(sc, 'level_input_cut', 1, 2, 0),
    'and does not bleed into the other')
  check(sc.last.loop[2] == 0, 'looping is off, or a long capture would wrap over itself')
  check(sc.last.loop_end[2] == Recorder.MAX_SECONDS, 'the loop window spans the longest capture')
  check(sc.last.pre_filter_dry[2] == 1.0 and sc.last.pre_filter_lp[2] == 0,
    'the record path is flat: softcut lowpasses at 16 kHz by default')
  check(sc.last.post_filter_dry[2] == 1.0 and sc.last.post_filter_lp[2] == 0, 'and so is the read path')
  check(sc.last.pre_level[2] == 0, 'a capture overwrites rather than layers')
  check(sc.last.level[2] == 0, 'nothing is monitored back out')
end

-- The protocol, which is the contract capture_controller already speaks.
do
  local recorder, sc, files, clock = context()
  recorder:send(message('PREFLIGHT', { seconds = 10, mode = 'manual' }))
  recorder:poll()
  recorder:send(message('START', { mode = 'manual' }))
  local started = recorder:poll()
  check(started and started.status == 'STARTED', 'START answers STARTED')
  check(sc.last.rec[2] == 1 and sc.last.play[2] == 1, 'the voice has to be moving to record')
  check(recorder:poll() == nil, 'an idle recorder reports nothing')
  clock.value = 4
  recorder:send(message('STOP'))
  local event = recorder:poll()
  check(event and event.command == 'EVENT' and event.status == 'COMPLETED', 'stopping completes the capture')
  check(sc.last.rec[2] == 0 and sc.last.play[2] == 0, 'and the voice stops')

  recorder:send(message('PUBLISH'))
  check(sc.last.buffer_write_stereo[1] == '/data/captures/rd-1.wav', 'the capture is written under its job id')
  check(math.abs(sc.last.buffer_write_stereo[3] - 4) < 0.001, 'only the recorded span is written')
  check(recorder:poll() == nil, 'nothing is published before the file exists')
  files.content['/data/captures/rd-1.wav'] = wav(192000, 48000, 2, 16)
  check(recorder:poll() == nil, 'a file seen once might still be growing')
  check(recorder:poll() == nil, 'a stable size starts the hash, which is not instant')
  files.content['/data/captures/rd-1.wav.sha256'] = string.rep('a', 64) .. '  /data/captures/rd-1.wav'
  local published = recorder:poll()
  check(published and published.status == 'PUBLISHED', 'the capture is published once it is whole')
  check(published.wav_path == '/data/captures/rd-1.wav', 'with its path')
  check(published.wav_sha256 == string.rep('a', 64), 'and the digest of what was written')
  check(published.frames == 192000 and published.sample_rate == 48000,
    'and a frame count read from the file, not from a clock')

  recorder:send(message('RELEASE'))
  local released = recorder:poll()
  check(released and released.status == 'RELEASED', 'release is acknowledged')
end

-- Softcut is shared, so it has to be given back.
do
  local recorder, sc, _, _, mixer = context({ adc = 0.5 })
  recorder:send(message('PREFLIGHT', { seconds = 5, mode = 'auto' })); recorder:poll()
  recorder:send(message('RELEASE')); recorder:poll()
  check(called(sc, 'enable', 1, 0) and called(sc, 'enable', 2, 0), 'both voices are handed back')
  check(mixer.levels[#mixer.levels] == 0.5, "the player's own ADC send is restored, not zeroed")
end

-- A capture that reaches its own duration completes itself.
do
  local recorder, _, _, clock = context()
  recorder:send(message('PREFLIGHT', { seconds = 3, mode = 'auto' })); recorder:poll()
  recorder:send(message('START')); recorder:poll()
  clock.value = 2.9
  check(recorder:poll() == nil, 'a capture in progress is not complete')
  clock.value = 3.0
  local event = recorder:poll()
  check(event and event.status == 'COMPLETED', 'a capture ends itself at its own duration')
end

-- Failures the controller is built to receive.
do
  local recorder = context()
  recorder:send(message('PREFLIGHT', { seconds = 0, mode = 'manual' }))
  local bad = recorder:poll()
  check(bad.status == 'FAILED' and bad.capture_error == 'INVALID_DURATION', 'a zero-length capture is refused')
  recorder:send(message('PREFLIGHT', { seconds = 5, mode = 'sideways' }))
  check(recorder:poll().capture_error == 'INVALID_DURATION', 'an unknown mode is refused')
  recorder:send(message('PREFLIGHT', { seconds = 5, mode = 'manual' })); recorder:poll()
  recorder:send(message('PREFLIGHT', { seconds = 5, mode = 'manual' }))
  check(recorder:poll().capture_error == 'BUSY', 'a second capture cannot take the input')

  local stale = message('START'); stale.generation = 99
  recorder:send(stale)
  local answer = recorder:poll()
  check(answer.status == 'STALE' and answer.capture_error == 'STALE_JOB', 'another job is answered STALE')
end

-- softcut never says when a write finished, so a write that never lands must
-- not leave the capture waiting forever.
do
  local recorder, _, _, clock = context({ timeout = 5 })
  recorder:send(message('PREFLIGHT', { seconds = 4, mode = 'manual' })); recorder:poll()
  recorder:send(message('START')); recorder:poll()
  clock.value = 4; recorder:poll()
  recorder:send(message('PUBLISH'))
  clock.value = 20
  local failed = recorder:poll()
  check(failed and failed.status == 'FAILED' and failed.capture_error == 'PUBLISH_TIMEOUT',
    'a write that never lands fails rather than hangs')
end

-- The geometry comes from the file, whatever softcut chose to write.
do
  check(Recorder.wav_geometry(wav(1000, 48000, 2, 16)) == 1000, '16-bit stereo')
  check(Recorder.wav_geometry(wav(1000, 44100, 2, 32)) == 1000, '32-bit stereo')
  local frames, rate = Recorder.wav_geometry(wav(500, 44100, 1, 16))
  check(frames == 500 and rate == 44100, 'mono, at its own rate')
  check(Recorder.wav_geometry('not a wav at all') == nil, 'rubbish is refused')
  check(Recorder.wav_geometry(nil) == nil, 'nothing is refused')
end

-- The point of speaking the existing protocol: the controller, the state
-- machine and everything above them do not know the native worker is gone.
do
  local Machine = require('rhythm_doctor.state_machine')
  local Controller = require('rhythm_doctor.capture_controller')
  local recorder, sc, files, clock = context()
  -- Stand in for softcut and sha256sum actually doing their work.
  sc.buffer_write_stereo = function(path, start, duration)
    sc.calls[#sc.calls + 1] = { name = 'buffer_write_stereo', arguments = { path, start, duration } }
    sc.last.buffer_write_stereo = { path, start, duration }
    files.content[path] = wav(math.floor(duration * 48000), 48000, 2, 16)
  end
  recorder.execute = function(command)
    local path = command:match("sha256sum '([^']+)'")
    if path then files.content[path .. '.sha256'] = string.rep('c', 64) .. '  ' .. path end
    return true
  end

  local controller, machine, saved, analysed
  machine = Machine.new{ project_id = 'integration',
    on_capture_start = function(mode, token) controller:begin(mode, token, 6) end,
    on_cancel = function(token) controller:cancel(token) end,
    on_release = function(token) controller:release(token) end,
    on_analyse = function(token) controller:analyse(token) end }
  controller = Controller.new{ machine = machine, transport = recorder,
    now = function() return clock.value end, transport_stopped = function() return true end,
    on_capture_saved = function(asset) saved = asset end,
    on_analysis_ready = function(asset, token)
      analysed = asset
      machine:receive_analysis{ project_id = token.project_id, generation = token.generation,
        analysis_revision = token.analysis_revision, error = 'TEST_ANALYSIS_STOP' }
    end }

  check(machine:start_capture('manual', true).ok, 'the machine starts a capture')
  for _ = 1, 50 do
    controller:poll()
    if controller.job and controller.job.phase == 'CAPTURING' then break end
  end
  check(controller.job.phase == 'CAPTURING', 'the controller reaches CAPTURING through the recorder')
  clock.value = 5
  check(machine:finish_capture(true, true).ok, 'the player can finish the capture')
  for _ = 1, 200 do
    controller:poll()
    if machine.resources_are_released then break end
    clock.value = clock.value + 0.05
  end
  check(saved ~= nil and analysed ~= nil, 'a capture asset reached the callbacks')
  check(saved.wav_sha256 == string.rep('c', 64), 'carrying the digest of the written file')
  check(saved.sample_rate == 48000 and saved.frames > 0, 'and its real geometry')
  check(saved.wav_path:match('%.wav$') ~= nil, 'and a WAV path')
  check(machine.resources_are_released, 'and softcut was handed back at the end')
  check(called(sc, 'enable', 1, 0), 'the voices really were released')
end

-- The runtime opens a source and expects a transport back, first time and every time.
do
  local sc, files = fake_softcut(), fake_files()
  local mixer = { levels = {} }
  mixer.level_adc_cut = function(v) mixer.levels[#mixer.levels + 1] = v end
  local host = Recorder.host({ directory = '/data/captures', softcut = sc, audio = mixer,
    now = function() return 0 end, execute = function() return true end,
    open_file = files.open, remove = files.remove, adc_cut_level = function() return 0 end })
  local first = host:open()
  check(type(first) == 'table' and type(first.send) == 'function' and type(first.poll) == 'function',
    'opening yields a transport the runtime can use')
  check(host:open() == first, 'opening again yields the same recorder, not a second claim on softcut')
  host:close()
  local refused, why = host:open()
  check(refused == nil and why ~= nil, 'a closed host refuses rather than reopening softcut')
end

print('test_softcut_recorder: ' .. passed .. ' tests passed')
