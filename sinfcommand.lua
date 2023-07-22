grid_controller = include("sinfcommand/lib/grid_controller")
ui_controller = include("sinfcommand/lib/ui_controller")

local fn = include("sinfcommand/lib/functions")
local fileselect = require('fileselect')
local textentry = require('textentry')
local musicutil = require("musicutil")

local as_metro = metro.init(do_autosave, 1, 1)
local autosave_timer = metro.init(prime_autosave, 20, 1)

local splash_screen_clock
local show_splash = true

clock_controller = include("sinfcommand/lib/clock_controller")
pattern_controller = include("sinfcommand/lib/pattern_controller")
midi_controller = include("sinfcommand/lib/midi_controller")


pages = {
  channel_edit_page = 1,
  channel_sequencer_page = 2,
  pattern_trigger_edit_page = 3,
  pattern_note_edit_page = 4,
  pattern_velocity_edit_page = 5
}

page_names = {
  "Channel Edit Page",
  "Channel Sequencer Page",
  "Pattern Trigger Edit Page",
  "Pattern Note Edit Page",
  "Pattern Velocity Edit Page"
}

local function load_project(pth)
  
  clock_controller:stop()

  if string.find(pth, '.ptn') ~= nil then
    print("Loading project " .. pth)
    local saved = tab.load(pth)
    if saved ~= nil then
      program = saved[2]
      if saved[1] then params:read(norns.state.data .. saved[1] .. ".pset") end
      clock_controller:reset()
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
    tab.save({ txt, program }, norns.state.data .. txt ..".ptn")
    params:write( norns.state.data .. txt .. ".pset")
  else
    print("Save cancel")
  end
end

local function load_new_project()

  local root_note = 60
  program = {
    selected_page = pages.channel_edit_page,
    selected_sequencer_pattern = 1,
    selected_pattern = 1,
    selected_channel = 1,
    scale_type = "sinfonion",
    root_note = root_note,
    default_scale = 1,
    bpm = 120,
    current_step = 1,
    scales = {
      {number = 2, scale = musicutil.generate_scale_of_length(0, "major", 7)}, 
      {number = 4, scale = musicutil.generate_scale_of_length(0, "minor", 7)}, 
      {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}
    },
    sequencer_patterns = fn.initialise_default_sequencer_patterns()
  }

end

local function do_autosave()

  if program ~= nil then
    save_project("autosave")
    grid_controller:splash_screen_off()
  end
  as_metro:stop()
  autosave_timer:stop()
end

local function prime_autosave()
  if as_metro.id then
    metro.free(as_metro.id)
  end
  if not clock_controller:is_playing() then
    as_metro = metro.init(do_autosave, 1, 1)
    
    grid_controller:splash_screen_on()
    
    as_metro:start()
    
  else
    autosave_reset() 
  end

end


local function post_splash_init()

  load_project(norns.state.data.."autosave.ptn")

  if program == nil then
    load_new_project()
  end

  grid_controller:splash_screen_off()
  clock_controller.init()
  ui_controller.init()
  grid_controller.init()
  fn.dirty_grid(true)
  fn.dirty_screen(true)
  ui_clock_id = clock.run(redraw_clock)

end

function redraw()
  screen.clear()
  screen.level(5)
  screen.font_size(8)
  ui_controller.redraw()
  screen.update()
end

function redraw_clock()
  while true do
    clock.sleep(1 / 15)
    if fn.dirty_screen() == true then
      redraw()
      fn.dirty_screen(false)
    end
  end
end

function init()
  midi_controller.init()
  grid_clock_id = clock.run(grid_controller.grid_redraw)

  grid_controller:splash_screen_on()

  params:add_separator("Pattern project management")
  params:add_trigger("save_p", "< Save project" )
  params:set_action("save_p", function(x) textentry.enter(save_project,  "new") end)
  params:add_trigger("load_p", "> Load project" )
  params:set_action("load_p", function(x) fileselect.enter(norns.state.data, load_project) end)
  params:add_trigger("new", "+ New" )
  params:set_action("new", function(x) load_new_project() end)


  post_init = metro.init(post_splash_init, 2, 1)
  post_init:start()


end



function autosave_reset() 
  if autosave_timer.id then
    metro.free(autosave_timer.id)
  end
  autosave_timer = metro.init(prime_autosave, 60, 1)
  autosave_timer:start()
end