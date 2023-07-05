local grid_controller = {}

local Fader = include("sinfcommand/lib/controls/Fader")
local Sequencer = include("sinfcommand/lib/controls/Sequencer")
local Button = include("sinfcommand/lib/controls/Button")

press_handler = include("sinfcommand/lib/press_handler")
draw_handler = include("sinfcommand/lib/draw_handler")

local channel_edit_page_controller = include("sinfcommand/lib/pages/channel_edit_page_controller")
local trigger_edit_page_controller = include("sinfcommand/lib/pages/trigger_edit_page_controller")
local note_edit_page_controller = include("sinfcommand/lib/pages/note_edit_page_controller")
local velocity_edit_page_controller = include("sinfcommand/lib/pages/velocity_edit_page_controller")

g = grid.connect()

function g.key(x, y, z)
  if z == 1 then
    grid_controller.push[x][y].state = "pressed"

    if grid_controller.push.active ~= false then
      if grid_controller.push.active[1] ~= x or grid_controller.push.active[2] ~= y then
        grid_controller:dual_press(grid_controller.push.active[1], grid_controller.push.active[2], x, y)
      end
    end
    
    grid_controller.push.active = {x, y}

    grid_controller.counter[x][y] = clock.run(grid_controller.grid_long_press, g, x, y)
  elseif z == 0 then -- otherwise, if a grid key is released...

    if grid_controller.counter[x][y] then -- and the long press is still waiting...
      clock.cancel(grid_controller.counter[x][y]) -- then cancel the long press clock,

      if grid_controller.push[x][y].state == "long_pressed" then
        grid_controller.push[x][y].state = "inactive"
        grid_controller.push.active = false
      elseif grid_controller.push[x][y].state == "pressed" then
        grid_controller:short_press(x,y) -- and execute a short press instead.
      end
    end
  end
end

function g.remove()
  grid_controller:alert_disconnect()
end



function register_draw_handlers()
  channel_edit_page_controller:register_draw_handlers()
  trigger_edit_page_controller:register_draw_handlers()
  note_edit_page_controller:register_draw_handlers()
  velocity_edit_page_controller:register_draw_handlers()
end

function register_press_handlers()
  channel_edit_page_controller:register_press_handlers()
  trigger_edit_page_controller:register_press_handlers()
  note_edit_page_controller:register_press_handlers()
  velocity_edit_page_controller:register_press_handlers()
  press_handler:register(
  "menu",
  function(x, y)
    if (y == 8) then
      if (x < 7) then
        program.selected_page = x
        
      end
    end
  end
  )
end

function grid_controller.init()

  grid_controller.counter = {}
  grid_controller.toggled = {}
  grid_controller.push = {}
  grid_controller.disconnect_dismissed = true
  for x = 1, 16 do
    grid_controller.counter[x] = {}
    grid_controller.push[x] = {}
    for y = 1, 8 do
      grid_controller.counter[x][y] = nil
      grid_controller.push[x][y] = {}
      grid_controller.push.active = false
      grid_controller.push[x][y].state = "inactive"
    end
  end


  
  channel_edit_page_controller:init()
  trigger_edit_page_controller:init()
  note_edit_page_controller:init()
  velocity_edit_page_controller:init()

  register_draw_handlers()
  register_press_handlers()

end


function grid_controller:short_press(x, y)

  press_handler:handle(program.selected_page, x, y)
  fn.dirty_grid(true)
  fn.dirty_screen(true)
  grid_controller.push[x][y].state = "inactive"
  grid_controller.push.active = false
end


function grid_controller:grid_long_press(x, y)
  clock.sleep(.5)
  grid_controller.push[x][y].state = "long_pressed"

  fn.dirty_grid(true)
end


function grid_controller:dual_press(x, y, x2, y2)
  grid_controller.push[x2][y2].state = "inactive"

  grid_controller.push.active = false
  fn.dirty_grid(true)
end

function grid_controller:alert_disconnect()
  self.disconnect_dismissed = false
end

function grid_controller:dismiss_disconnect()
  self.disconnect_dismissed = true
end

function grid_draw_menu(selected_page)

  for i = 1, 5 do
    g:led(i, 8, 2)
  end


  g:led(selected_page, 8, 15)

  
  fn.dirty_grid(true)

end


function grid_controller:grid_redraw()
  g:all(0)

  grid_draw_menu(program.selected_page)
  draw_handler:handle(program.selected_page)

  g:refresh()
end


function grid_controller.grid_redraw_clock()
  while true do
    clock.sleep(1 / 30)
    if fn.dirty_grid() == true then
      grid_controller:grid_redraw()
      fn.dirty_grid(false)
    end
  end
end

return grid_controller
