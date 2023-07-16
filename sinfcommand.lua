local grid_controller = include("sinfcommand/lib/grid_controller")
local fn = include("sinfcommand/lib/functions")
local fileselect = require('fileselect')
local textentry = require('textentry')

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


local function load_project(pth)
  
  clock_controller:stop()
  clock_controller:reset()

  if string.find(pth, '.ptn') ~= nil then
    local saved = tab.load(pth)
    if saved ~= nil then
      program = saved[2]
      if saved[1] then params:read(norns.state.data .. saved[1] .. ".pset") end

    else
        print("no data")
    end
  end

end

local function save_project(txt)

  clock_controller:stop()
  clock_controller:reset()

  if txt then
    tab.save({ txt, program }, norns.state.data .. txt ..".ptn")
    params:write( norns.state.data .. txt .. ".pset")
  else
    print("save cancel")
  end
end

function load_new_project()
  program = {
    selected_page = pages.channel_edit_page,
    selected_sequencer_pattern = 1,
    selected_pattern = 1,
    selected_channel = 1,
    scale_type = "sinfonion",
    root_note = 60,
    bpm = 120,
    current_step = 1,
    scales = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
    sequencer_patterns = fn.initialise_default_sequencer_patterns()
  }
  clock_controller.init()
  grid_clock_id = clock.run(grid_controller.grid_redraw_clock)
  fn.dirty_grid(true)
end

function init()
  midi_controller.init()

  params:add_separator("Pattern project management")
  params:add_trigger('save_p', "< Save project" )
  params:set_action('save_p', function(x) textentry.enter(save_project,  'new') end)
  params:add_trigger('load_p', "> Load project" )
  params:set_action('load_p', function(x) fileselect.enter(norns.state.data, load_project) end)
  params:add_trigger('new', "+ New" )
  params:set_action('new', function(x) load_new_project() end)

  load_new_project()

  grid_controller.init()
end