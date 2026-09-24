-- mosaic v1.3.0
-- grid-first rhythm and 
-- harmony sequencer.
--
-- llllllll.co/t/mosaic/69304
-- manual: t.ly/h-Wsw

-- Copyright Andrew Hillel 2024. See the included GNU licence for more information.

testing = false

pages = include("mosaic/lib/pages/pages")
program = include("mosaic/lib/models/program")
fn = include("mosaic/lib/helpers/functions")
scheduler = include("mosaic/lib/scheduler")
m_grid = include("mosaic/lib/m_grid")
ui = include("mosaic/lib/ui")
local ui_splash = include("mosaic/lib/ui_splash")
sinfonion = include("mosaic/lib/sinfonion_harmonic_sync")
m_midi = include("mosaic/lib/m_midi")
memory = include("mosaic/lib/memory")
recorder = include("mosaic/lib/recorder")

-- Debug
-- profiler = include("mosaic/lib/helpers/profiler")

-- p = newProfiler()

local fileselect = require("fileselect")
local textentry = require("textentry")
local as_metro = metro.init(do_autosave, 1, 1)
local autosave_timer = metro.init(prime_autosave, 60, 1)
local param_manager = include("mosaic/lib/devices/param_manager")
local application_parameters = include("mosaic/lib/application_parameters")

local project_validation = include("mosaic/lib/project_validation")
local ui_splash_screen_active = false
local project = include("mosaic/lib/project_lifecycle").new(
  as_metro, autosave_timer, param_manager, project_validation,
  function(active) ui_splash_screen_active = active end
)


local redraw_clock = nil
local grid_redraw_clock = nil
local scheduler_clock = nil
local screen_keep_alive = nil
local rhythm_doctor_poll_clock = nil

nb = require("mosaic/lib/nb/lib/nb")
m_clock = include("mosaic/lib/clock/m_clock")
local rhythm_doctor_runtime_module = include("mosaic/lib/rhythm_doctor/runtime")
local rhythm_doctor_recorder = include("mosaic/lib/rhythm_doctor/softcut_recorder")
local rhythm_doctor_analysis_worker_host = include("mosaic/lib/rhythm_doctor/analysis_worker_host")
local rhythm_doctor_ui_module = include("mosaic/lib/rhythm_doctor/ui_adapter")
local rhythm_doctor_runtime = nil
local rhythm_doctor_ui = nil
local redraw_guard = include("mosaic/lib/clock/redraw_guard")
pattern = include("mosaic/lib/pattern")
m_midi = include("mosaic/lib/m_midi")
step = include("lib/step")
device_map = include("mosaic/lib/devices/device_map")
norns_param_state_handler = include("mosaic/lib/devices/norns_param_state_handler")

g = grid.connect()

local function post_splash_init()

end

-- Read the configured analysis server, honouring the on/off switch so a player
-- can keep an address saved while working locally.
local function rhythm_doctor_server_endpoint()
  -- Called when the analysis worker opens, which is after init() has
  -- registered these parameters.
  if params == nil or type(params.get) ~= "function" then return nil end
  local ok, enabled = pcall(function() return params:get("rhythm_doctor_use_server") end)
  if not ok or enabled ~= 2 then return nil end
  local read, endpoint = pcall(function() return params:get("rhythm_doctor_server") end)
  if not read or type(endpoint) ~= "string" or endpoint:match("^%s*$") then return nil end
  return (endpoint:gsub("^%s+", ""):gsub("%s+$", ""))
end

local function init_rhythm_doctor()
  -- Capture runs through softcut, which lives inside crone and is therefore
  -- already connected to JACK. Opening a JACK client of our own is the one
  -- thing a norns cannot be relied on to allow: systemd removes the user's
  -- shared memory when their last login session ends, and JACK's registry goes
  -- with it, so nothing new can join the graph until jackd restarts.
  local worker = rhythm_doctor_recorder.host({
    directory = norns.state.data .. "rhythm-doctor-captures",
  })
  local analysis_worker = rhythm_doctor_analysis_worker_host.new({
    runtime_root = norns.state.data .. "rhythm-doctor-analysis-runtime",
    -- This optional local-computer profile is deliberately unconfigured by
    -- default.  A deployment must provide every immutable identity below;
    -- missing or partial values fail closed and never trigger a download.
    backend = os.getenv("RHYTHM_DOCTOR_ANALYSIS_BACKEND"),
    backend_sha256 = os.getenv("RHYTHM_DOCTOR_ANALYSIS_BACKEND_SHA256"),
    drum_artifact_sha256 = os.getenv("RHYTHM_DOCTOR_DRUM_ARTIFACT_SHA256"),
    bass_artifact_sha256 = os.getenv("RHYTHM_DOCTOR_BASS_ARTIFACT_SHA256"),
    -- The shipped classical-DSP backend pins its own source and template
    -- table instead of model artifacts, and needs no downloads.
    template_sha256 = os.getenv("RHYTHM_DOCTOR_TEMPLATE_SHA256"),
    -- The analysis server, if the player has configured one and switched it
    -- on. An unreachable or slow server is not an error: the capture falls
    -- back to on-device analysis and the player still gets gates.
    -- Passed as a provider, not a value. init() builds this host before the
    -- parameters holding the endpoint are registered, so reading it here
    -- always found nothing and the player silently got on-device analysis.
    -- Resolved when the worker opens instead, so the setting also takes
    -- effect on the next capture rather than the next script reload.
    remote_endpoint = rhythm_doctor_server_endpoint,
    transport_factory = function(mailbox_root, result_root)
      return include("mosaic/lib/rhythm_doctor/analysis_transport").new(mailbox_root, result_root)
    end,
  })
  rhythm_doctor_runtime = rhythm_doctor_runtime_module.new({
    project_id = norns.state.data .. "autosave.ptn",
    worker = worker,
    now = util.time,
    transport_stopped = function() return not m_clock.is_playing() end,
    analysis_worker = analysis_worker,
    -- A save asked for during a capture is deferred rather than refused, and
    -- declining it stops the autosave timers. Re-prime them once the capture
    -- has released so the save runs through the ordinary path, with its
    -- transport, inhibition and project-ownership checks intact.
    on_deferred_save = function() project.prime_autosave() end,
    paint = {
      adapter = { trig_field = "trig_values", velocity_field = "velocity_values", length_field = "lengths", on = 1, off = 0 },
      read_source = function(target)
        local song = program.get_song_pattern(target.song_slot)
        local source = song and song.patterns and song.patterns[target.pattern_id]
        if not source then return nil, { code = "SOURCE_UNAVAILABLE" } end
        local snapshot = fn.deep_copy(source)
        snapshot.revision = pattern.get_source_revision(song, target.pattern_id)
        return snapshot
      end,
      write_source = function(target, snapshot, expected_revision)
        local song = program.get_song_pattern(target.song_slot)
        if not song or not song.patterns or not song.patterns[target.pattern_id] then
          return nil, { code = "SOURCE_UNAVAILABLE" }
        end
        if pattern.get_source_revision(song, target.pattern_id) ~= expected_revision then
          return nil, { code = "PATTERN_CHANGED" }
        end
        local saved = fn.deep_copy(snapshot)
        saved.revision = nil
        song.patterns[target.pattern_id] = saved
        song.active = true
        pattern.update_source_working_patterns(song, target.pattern_id)
        saved = fn.deep_copy(saved)
        saved.revision = pattern.get_source_revision(song, target.pattern_id)
        return saved
      end,
      -- write_source schedules every channel that references the shared source.
      reproject = function() return true end,
    },
  })
  rhythm_doctor_ui = rhythm_doctor_ui_module.new({ runtime = rhythm_doctor_runtime,
    transport_stopped = function() return not m_clock.is_playing() end })
  rhythm_doctor_runtime.on_status = function(code, detail)
    rhythm_doctor_ui:set_status(code, detail)
    fn.dirty_grid(true); fn.dirty_screen(true)
  end
  trigger_edit_page.set_rhythm_doctor(rhythm_doctor_ui)
  project.set_capture_guard(rhythm_doctor_runtime)
  rhythm_doctor_poll_clock = clock.run(function()
    while true do
      clock.sleep(1/30)
      rhythm_doctor_ui:poll()
    end
  end)
end

local function draw_application_screen()
  screen.level(5)
  screen.font_size(8)
  ui.redraw()
end

function redraw()
  screen.clear()
  if fn.dirty_screen() == true then
    -- Clear the flag first: a frame that is still animating asks for the next one.
    fn.dirty_screen(false)
    if ui_splash_screen_active then
      screen.level(15)
      screen.move(60, 38)
      screen.font_face(math.random(3, 8))
      screen.font_size(12)
      screen.text("m°")
      screen.font_face(1)
      screen.update()
    elseif ui_splash.active() then
      ui_splash.draw(nil, draw_application_screen)
      screen.update()
    else
      draw_application_screen()
      screen.update()
    end
  end
end


local function blink()
  program.toggle_blink_state()
  fn.dirty_grid(true)
  clock.run(function() clock.sleep(0.4); blink() end)
end

function init()

  ui_splash_screen_active = true
  math.randomseed(os.time())
  program.init()
  m_midi.init()
  init_rhythm_doctor()
  
  grid_connected = g.device~= nil and true or false
  
  nb:init()
  if note_players then
    nb:add_param("voice_id", "NB PARAMS") -- adds a voice selector param to your script.
    nb:add_player_params() -- Adds the parameters for the selected voices to your script.
  end

  device_map.init()


  sinfonion.set_root_note(0)
  sinfonion.set_degree_nr(0)
  sinfonion.set_mode_nr(0)
  sinfonion.set_transposition(0)
  sinfonion.set_clock(0)
  sinfonion.set_beat(0)
  sinfonion.set_step(0)
  sinfonion.set_reset(0)
  sinfonion.set_chaotic_detune(0)
  sinfonion.set_harmonic_shift(0)

  crow.ii.pullup(true)

  scheduler_clock = clock.run(
    function()
      while true do
        clock.sleep(1/300)
        scheduler.update()
      end
    end
  )


  -- A screen redraw is native-heavy and cannot be interrupted, so it must not
  -- start just before a step's notes. Leave that slot to the next cycle.
  local screen_guard = redraw_guard.new(m_clock.seconds_to_next_step, util.time)
  local grid_guard = redraw_guard.new(m_clock.seconds_to_next_step, util.time)

  redraw_clock = clock.run(
    function()
      while true do
        clock.sleep(1/30)
        -- norns keeps a short K1 tap for itself; the menu change is how the UI learns of it.
        if ui_live and ui_live.installed() then ui_live.native_changed(_menu ~= nil and _menu.mode == true) end
        if fn.dirty_screen() then screen_guard.run(redraw) end
      end
    end
  )

  grid_redraw_clock = clock.run(
    function()
      while true do
        clock.sleep(1/20)
        if fn.dirty_grid() then grid_guard.run(m_grid.grid_redraw) end
      end
    end
  )

  screen_keep_alive = clock.run(
    function()
      while true do
        clock.sleep(1)
        fn.dirty_screen(true)
      end
    end
  )

  blink()

  application_parameters.register({
    save = function() textentry.enter(project.save, "new") end,
    load = function() fileselect.enter(norns.state.data, project.load) end,
    new = project.new
  })

  param_manager.init()

  clock.tempo_change_handler = function(x)
    song_edit_page_ui.refresh_tempo()
  end


  project.load(norns.state.data .. "autosave.ptn", true)

  if program == nil then
    project.new()
  end

  device_map.validate_devices()
  params:bang()

  m_midi.set_up_midi_mapping_params()

  ui.init()
  m_grid.init()
  -- A grid press also ends the splash; the press itself is handled as usual.
  local grid_key = g.key
  g.key = function(x, y, z)
    ui_splash.skip()
    grid_key(x, y, z)
  end
  m_clock.init()
  ui_splash_screen_active = false
  fn.dirty_grid(true)
  fn.dirty_screen(true)

  -- The animated splash runs once the application is ready; input ends it.
  -- MOSAIC > UI motion Off skips it along with the other decorative motion.
  if params:get("ui_motion") ~= 1 then ui_splash.start() end
  clock.run(function()
    while ui_splash.advance() do
      fn.dirty_screen(true)
      clock.sleep(1 / ui_splash.FPS)
    end
    fn.dirty_screen(true)
  end)

end

function enc(n, d)
  ui_splash.skip()
  ui.enc(n, d)
end

function key(n, z)
  ui_splash.skip()
  ui.key(n, z)
end

function autosave_reset()
  project.reset_autosave()
end

-- Every route that starts the sequencer has to tell Rhythm Doctor, or a
-- capture keeps running underneath playback. clock.transport is one route; the
-- grid Play key is another and does not pass through it. The local/external
-- distinction stays with each caller: this only announces.
function transport_started_by_user()
  if rhythm_doctor_ui then rhythm_doctor_ui:transport_started() end
end

function clock.transport:start()
  transport_started_by_user()
  m_clock:start(params:get("clock_source") == 2)
end

function clock.transport:stop()
  m_clock:stop()
  if rhythm_doctor_ui then rhythm_doctor_ui:transport_stopped() end
end

-- -- Debug
-- local outfile
-- local p

-- function start_profiler()
--   -- Determine the script's directory
--   local script_path = debug.getinfo(1, "S").source:match("^@(.*/)")
--   if not script_path then
--     script_path = "./"
--   end

--   -- Attempt to open the output file
--   outfile, err = io.open(script_path .. "profile.txt", "w+")
--   if not outfile then
--     error("Failed to open output file for profiling: " .. err)
--   end

--   -- Start the profiler
--   p = newProfiler()
--   p:start()
-- end

-- function stop_profiler()
--   if not p then
--     print("Profiler has not been started.")
--     return
--   end
--   p:stop()
--   if not outfile then
--     print("Output file is not available.")
--     return
--   end
--   p:report(outfile)
--   outfile:close()
-- end

-- Restore script-owned vport hooks before norns loads another script.
function cleanup()
  if rhythm_doctor_runtime then rhythm_doctor_runtime:cleanup() end
  m_midi.cleanup()
end
