-- mosaic v0.4
-- grid-centric, intentioned
-- generative sequencer.
--
-- llllllll.co/t/mosaic-alpha-v0-3
-- manual: t.ly/h-Wsw

testing = false

local create_default_config = include("mosaic/lib/user_config/create_default_config")

create_default_config.create_script("device_config.lua", create_default_config.default_device_config_content)
create_default_config.create_script("custom_device_map.lua", create_default_config.default_custom_device_map_content)

grid_controller = include("mosaic/lib/grid_controller")
ui_controller = include("mosaic/lib/ui_controller")
program = include("mosaic/lib/program")
sinfonion = include("mosaic/lib/sinfonion_harmonic_sync")
midi_controller = include("mosaic/lib/midi_controller")


local fn = include("mosaic/lib/functions")
local fileselect = require("fileselect")
local textentry = require("textentry")
local musicutil = require("musicutil")
local as_metro = metro.init(do_autosave, 1, 1)
local autosave_timer = metro.init(prime_autosave, 20, 1)
local device_param_manager = include("mosaic/lib/device_param_manager")

local ui_splash_screen_active = false

nb = require("mosaic/lib/nb/lib/nb")
clock_controller = include("mosaic/lib/clock_controller")
pattern_controller = include("mosaic/lib/pattern_controller")
midi_controller = include("mosaic/lib/midi_controller")
step_handler = include("lib/step_handler")
device_map = include("mosaic/lib/device_map")

local function load_project(pth)
  clock_controller:stop()

  if string.find(pth, ".ptn") ~= nil then
    print("Loading project " .. pth)
    local saved = tab.load(pth)
    if saved ~= nil then
      program.set(saved[2])
      if saved[1] then
        params:read(norns.state.data .. saved[1] .. ".pset")
      end
      clock_controller:reset()
      ui_controller.refresh()
      fn.dirty_grid(true)
    else
      print("No data")
    end
  end
end

local function save_project(txt)
  clock_controller:stop()
  clock_controller:reset()

  if txt then
    print("Saving project as " .. txt)
    tab.save({txt, program.get()}, norns.state.data .. txt .. ".ptn")
    params:write(norns.state.data .. txt .. ".pset")
  else
    print("Save cancel")
  end
end

local function load_new_project()
  program.init()
  grid_controller.refresh()
  ui_controller.refresh()
end

local function do_autosave()
  if program ~= nil then
    save_project("autosave")
  end
  grid_controller.splash_screen_off()
  ui_splash_screen_active = false
  fn.dirty_screen(true)
  as_metro:stop()
  autosave_timer:stop()
end

local function prime_autosave()
  if as_metro.id then
    metro.free(as_metro.id)
  end
  if not clock_controller.is_playing() then
    as_metro = metro.init(do_autosave, 0.5, 1)

    grid_controller.splash_screen_on()
    ui_splash_screen_active = true

    as_metro:start()
  else
    autosave_reset()
  end
end

local function post_splash_init()
  device_param_manager.init()
  load_project(norns.state.data .. "autosave.ptn")

  if program == nil then
    load_new_project()
  end
  for i = 1, 16 do
    device_param_manager.add_device_params(
      i,
      device_map.get_device(program.get().devices[i].device_map),
      program.get().devices[i].midi_channel,
      program.get().devices[i].midi_device,
      false
    )
  end
  device_map.validate_devices()
  params:bang()
  grid_controller.splash_screen_off()
  ui_splash_screen_active = false
  ui_controller.init()
  grid_controller.init()
  fn.dirty_grid(true)
  fn.dirty_screen(true)
  crow.ii.jf.mode(1)
end

function redraw()
  screen.clear()

  if ui_splash_screen_active then
    screen.level(15)
    screen.move(60, 38)
    screen.font_face(math.random(3, 8))
    screen.font_size(12)
    screen.text("m°")
    screen.font_face(1)
    screen.update()
    return
  end

  if fn.dirty_screen() == true then
    screen.level(5)
    screen.font_size(8)
    ui_controller.redraw()
    screen.update()
    fn.dirty_screen(false)
  end
end

function redraw_metro()
  redraw()
end

function init()
  math.randomseed(os.time())
  program.init()
  midi_controller.init()
  
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


  local grid_clock_id = metro.init()
  grid_clock_id.event = grid_controller.grid_redraw
  grid_clock_id.time = 1 / 30
  grid_clock_id.count = -1
  grid_clock_id:start()

  local ui_clock_id = metro.init()
  ui_clock_id.event = redraw_metro
  ui_clock_id.time = 1 / 20
  ui_clock_id.count = -1
  ui_clock_id:start()

  grid_controller.splash_screen_on()
  ui_splash_screen_active = true

  params:add_group("mosaic", "MOSAIC", 14)
  params:add_separator("Pattern project management")
  params:add_trigger("save_p", "< Save project")
  params:set_action(
    "save_p",
    function(x)
      textentry.enter(save_project, "new")
    end
  )
  params:add_trigger("load_p", "> Load project")
  params:set_action(
    "load_p",
    function(x)
      fileselect.enter(norns.state.data, load_project)
    end
  )
  params:add_trigger("new", "+ New")
  params:set_action(
    "new",
    function(x)
      load_new_project()
    end
  )
  params:add_separator("Trig Editor")
  params:add_option("tresillo_amount", "Tresillo amount", {8, 16, 24, 32, 40, 48, 56, 64}, 3)
  params:set_action(
    "tresillo_amount",
    function(x)
      trigger_edit_page_ui_controller:refresh()
    end
  )
  params:add_separator("Sequencer")
  params:add_option("song_mode", "Song mode", {"On", "Off"}, 1)
  params:set_action(
    "song_mode",
    function(x)
      channel_sequencer_page_ui_controller:refresh()
    end
  )
  params:add_option("reset_on_end_of_pattern", "Reset when pattern ends", {"On", "Off"}, 2)
  params:add_option("dual_press_enabled", "Dual pressing", {"On", "Off"}, 1)
  params:add_separator("Prameter locks")
  params:add_option("trigless_locks", "Trigless locks", {"On", "Off"}, 1)
  params:add_separator("Quantiser")
  params:add_option("quantiser_trig_lock_hold", "Hold quantiser trigs", {"On", "Off"}, 1)

  device_param_manager.init()

  clock.tempo_change_handler = function(x)
    channel_sequencer_page_ui_controller.refresh_tempo()
  end

  post_init = metro.init(post_splash_init, 0.5, 1)
  post_init:start()
end

function enc(n, d)
  ui_controller.enc(n, d)
end

function key(n, z)
  ui_controller.key(n, z)
end

function autosave_reset()
  if autosave_timer.id then
    metro.free(autosave_timer.id)
  end
  autosave_timer = metro.init(prime_autosave, 20, 1)
  autosave_timer:start()
end

function clock.transport:start()
  clock_controller:start()
end

function clock.transport:stop()
  clock_controller:stop()
end
