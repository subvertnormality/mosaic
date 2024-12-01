-- mosaic v1.1.0
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

local ui_splash_screen_active = false

local redraw_clock = nil
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

local function load_project(pth)
  m_clock:stop()

  if string.find(pth, ".ptn") ~= nil then
    print("Loading project " .. pth)
    local saved = tab.load(pth)
    if saved ~= nil then
      -- Initialize program_store before setting data
      program.init()
      
      -- Set and migrate the data
      program.set(saved[2])

      clock.tempo_change_handler = function(x)
        song_edit_page_ui.refresh_tempo()
      end

      param_manager.init()
      
      for i = 1, 16 do
        param_manager.add_device_params(
          i,
          device_map.get_device(program.get().devices[i].device_map),
          program.get().devices[i].midi_channel,
          program.get().devices[i].midi_device,
          false
        )
      end

      if saved[1] then
        params:read(norns.state.data .. saved[1] .. ".pset", true)
      end

      m_clock:reset()
      ui.refresh()
      fn.dirty_grid(true)
    else
      print("No data")
    end
  end
end

local function save_project(txt)
  m_clock:stop()
  m_clock:reset()

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
  for i = 1, 16 do
    param_manager.add_device_params(
      i,
      device_map.get_device(program.get().devices[i].device_map),
      program.get().devices[i].midi_channel,
      program.get().devices[i].midi_device,
      true
    )
  end
  m_grid.refresh()
  ui.refresh()
end

local function do_autosave()
  ui_splash_screen_active = true
  if program ~= nil then
    save_project("autosave")
  end
  ui_splash_screen_active = false
  tooltip:show("Autosaved")
  fn.dirty_screen(true)
  as_metro:stop()
  autosave_timer:stop()
end

local function prime_autosave()
  if as_metro.id then
    metro.free(as_metro.id)
  end
  if not m_clock.is_playing() then
    as_metro = metro.init(do_autosave, 0.5, 1)
    as_metro:start()
  else
    autosave_reset()
  end
end

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

  params:add_group("mosaic", "MOSAIC", 32)
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
  params:add_option("global_swing_shuffle_type", "Global swing type", {"Swing", "Shuffle"}, 1)
  params:set_action(
    "global_swing_shuffle_type",
    function(x)
      song_edit_page_ui.refresh_swing_shuffle_type()
      channel_edit_page_ui.refresh_swing_shuffle_type()
    end
  )
  params:hide("global_swing_shuffle_type")

  params:add_number("global_swing", "Global swing", -50, 50, 0, nil, false)
  params:set_action(
    "global_swing",
    function(x)
      song_edit_page_ui.refresh_swing()
    end
  )
  params:hide("global_swing")

  params:add_option("global_shuffle_feel", "Global shuffle feel", {"Drunk", "Smooth", "Heavy", "Clave"}, 1)
  params:set_action(
    "global_shuffle_feel",
    function(x)
      song_edit_page_ui.refresh_shuffle_feel()
    end
  )
  params:hide("global_shuffle_feel")

  params:add_option("global_shuffle_basis", "Global shuffle basis", {"9", "7", "5", "6", "8??", "9??"}, 1)
  params:set_action(
    "global_shuffle_basis",
    function(x)
      song_edit_page_ui.refresh_shuffle_basis()
    end
  )
  params:hide("global_shuffle_basis")

  params:add_number("global_shuffle_amount", "Global shuffle amount", 0, 100, 0, nil, false)
  params:set_action(
    "global_shuffle_amount",
    function(x)
      song_edit_page_ui.refresh_shuffle_amount()
    end
  )
  params:hide("global_shuffle_amount")

  params:add_separator("Sequencer")
  params:add_option("record", "Record", {"Off", "On"}, 1)
  params:add_option("stop_safety", "Shift press to stop", {"Off", "On"}, 1)
  params:add_option("song_mode", "Song mode", {"Off", "On"}, 2)
  params:add_option("wrap_param_slides", "Wrap param slides", {"Off", "On"}, 1)
  params:set_action(
    "song_mode",
    function(x)
      song_edit_page_ui:refresh()
    end
  )
  params:add_option("reset_on_end_of_pattern_repeat", "Reset on pattern repeat", {"Off", "On"}, 1)
  params:add_option("reset_on_song_pattern_transition", "Reset on song seq change", {"Off", "On"}, 2)
  params:add_option("elektron_program_changes", "Elektron program changes", {"Off", "On"}, 1)
  params:add_number("elektron_program_change_channel", "Elektron p.change channel", 1, 16, 10, nil, false)
  params:add_separator("Parameter locks")
  params:add_option("trigless_locks", "Trigless locks", {"Off", "On"}, 2)
  params:add_separator("Quantiser")
  params:add_option("quantiser_act_on_note_masks", "Quantise note masks", {"Off", "On"}, 2)
  params:add_option("quantiser_trig_lock_hold", "Scales lock until ptn end", {"Off", "On"}, 2)
  params:add_option("all_scales_lock_to_pentatonic", "Lock all to pentatonic", {"Off", "On"}, 1)
  params:add_option("random_lock_to_pentatonic", "Lock random to pent.", {"Off", "On"}, 2)
  params:add_option("merged_lock_to_pentatonic", "Lock merged to pent.", {"Off", "On"}, 2)
  params:add_separator("Trig Editor")
  params:add_option("tresillo_amount", "Tresillo amount", {8, 16, 24, 32, 40, 48, 56, 64}, 3)
  params:set_action(
    "tresillo_amount",
    function(x)
      trigger_edit_page_ui:refresh()
    end
  )
  params:add_separator("Midi control")
  params:add_option("midi_scale_mapped_to_white_keys", "Map scale to white keys", {"Off", "On"}, 1)
  params:add_option("midi_honour_rotation", "Honour scale rotations", {"Off", "On"}, 1)
  params:add_option("midi_honour_degree", "Honour scale degree", {"Off", "On"}, 1)

  param_manager.init()

  clock.tempo_change_handler = function(x)
    song_edit_page_ui.refresh_tempo()
  end


  load_project(norns.state.data .. "autosave.ptn")

  if program == nil then
    load_new_project()
  end

  device_map.validate_devices()
  params:bang()

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
  if autosave_timer.id then
    metro.free(autosave_timer.id)
  end
  autosave_timer = metro.init(prime_autosave, 60, 1)
  autosave_timer:start()
end

function clock.transport:start()
  m_clock:start()
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
