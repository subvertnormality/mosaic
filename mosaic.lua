-- mosaic v1.2.12
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

nb = require("mosaic/lib/nb/lib/nb")
m_clock = include("mosaic/lib/clock/m_clock")
pattern = include("mosaic/lib/pattern")
m_midi = include("mosaic/lib/m_midi")
step = include("lib/step")
device_map = include("mosaic/lib/devices/device_map")
norns_param_state_handler = include("mosaic/lib/devices/norns_param_state_handler")

g = grid.connect()

local function post_splash_init()

end

function redraw()
  screen.clear()
  if fn.dirty_screen() == true then
    if ui_splash_screen_active then
      screen.level(15)
      screen.move(60, 38)
      screen.font_face(math.random(3, 8))
      screen.font_size(12)
      screen.text("m°")
      screen.font_face(1)
      screen.update()
    
    else
      screen.level(5)
      screen.font_size(8)
      ui.redraw()
      screen.update()
    end

    fn.dirty_screen(false)
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


  redraw_clock = clock.run(
    function()
      while true do
        clock.sleep(1/30)
        if fn.dirty_screen() then
          redraw()
        end
      end
    end
  )

  grid_redraw_clock = clock.run(
    function()
      while true do
        clock.sleep(1/20)
        if fn.dirty_grid() then
          m_grid.grid_redraw()
        end
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
  m_clock.init()
  ui_splash_screen_active = false
  fn.dirty_grid(true)
  fn.dirty_screen(true)

end

function enc(n, d)
  ui.enc(n, d)
end

function key(n, z)
  ui.key(n, z)
end

function autosave_reset()
  project.reset_autosave()
end

function clock.transport:start()
  m_clock:start(params:get("clock_source") == 2)
end

function clock.transport:stop()
  m_clock:stop()
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
