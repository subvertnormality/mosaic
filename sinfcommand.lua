-- Patterning v0.0.1
-- Deliberate generative rhythm sequencer
--
-- llllllll.co/t/patterning
--



grid_controller = include("sinfcommand/lib/grid_controller")
ui_controller = include("sinfcommand/lib/ui_controller")
program = include("sinfcommand/lib/program")

local fn = include("sinfcommand/lib/functions")
local fileselect = require('fileselect')
local textentry = require('textentry')
local musicutil = require("musicutil")

local as_metro = metro.init(do_autosave, 1, 1)
local autosave_timer = metro.init(prime_autosave, 20, 1)

local ui_splash_screen_active = false

clock_controller = include("sinfcommand/lib/clock_controller")
pattern_controller = include("sinfcommand/lib/pattern_controller")
midi_controller = include("sinfcommand/lib/midi_controller")

local function load_project(pth)
  
  clock_controller:stop()

  if string.find(pth, '.ptn') ~= nil then
    print("Loading project " .. pth)
    local saved = tab.load(pth)
    if saved ~= nil then
      program.set(saved[2])
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
    tab.save({ txt, program.get() }, norns.state.data .. txt ..".ptn")
    params:write( norns.state.data .. txt .. ".pset")
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

  load_project(norns.state.data.."autosave.ptn")

  if program == nil then
    load_new_project()
  end

  grid_controller.splash_screen_off()
  ui_splash_screen_active = false
  ui_controller.init()
  grid_controller.init()
  fn.dirty_grid(true)
  fn.dirty_screen(true)

end

function redraw()

  screen.clear()

  if ui_splash_screen_active then
    screen.level(15)
    screen.move(60, 38)
    screen.font_face (math.random(3,8))
    screen.font_size(9)
    screen.text("P")
    screen.font_face (1)
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

function redraw_clock()
  while true do
    clock.sleep(1 / 15)
    redraw()
  end
end

function init()
  program.init()
  midi_controller.init()
  grid_clock_id = clock.run(grid_controller.grid_redraw)
  ui_clock_id = clock.run(redraw_clock)

  grid_controller.splash_screen_on()
  ui_splash_screen_active = true

  params:add_group("PATTERNING", 20)
  params:add_separator("Pattern project management")
  params:add_trigger("save_p", "< Save project" )
  params:set_action("save_p", function(x) textentry.enter(save_project,  "new") end)
  params:add_trigger("load_p", "> Load project" )
  params:set_action("load_p", function(x) fileselect.enter(norns.state.data, load_project) end)
  params:add_trigger("new", "+ New" )
  params:set_action("new", function(x) load_new_project() end)
  params:add_separator("Trig Editor")
  params:add_option("tresillo_amount", "Tresillo amount", {8, 16, 24, 32, 40, 48, 56, 64}, 3)
  params:set_action("tresillo_amount", function(x) trigger_edit_page_ui_controller:refresh() end)
  params:add_separator("Live mode utilities")
  params:add_option("dual_press_enabled", "Dual pressing", {"On", "Off"}, 1)
  params:add_separator("Prameter locks")
  params:add_option("trigless_locks", "Trigless locks", {"On", "Off"}, 1)
  params:add_separator("Quantiser")
  params:add_option("quantiser_trig_lock_hold", "Hold quantiser trigs", {"On", "Off"}, 1)


  
  post_init = metro.init(post_splash_init, 0.5, 1)
  post_init:start()


end

function enc(n,d)
  ui_controller.enc(n, d)
end

function key(n,z)
  ui_controller.key(n, z)
end



function autosave_reset() 
  if autosave_timer.id then
    metro.free(autosave_timer.id)
  end
  autosave_timer = metro.init(prime_autosave, 60, 1)
  autosave_timer:start()
end

function clock.transport:start()
  clock_controller:start()
end

function clock.transport:stop()
  clock_controller:stop()
end