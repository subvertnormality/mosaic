local grid_controller = {}

local Fader = include("sinfcommand/lib/controls/Fader")
local Sequencer = include("sinfcommand/lib/controls/Sequencer")
local Button = include("sinfcommand/lib/controls/Button")

press_handler = include("sinfcommand/lib/press_handler")
draw_handler = include("sinfcommand/lib/draw_handler")

local channel_edit_page_controller = include("sinfcommand/lib/pages/channel_edit_page_controller")
local channel_sequencer_page_controller = include("sinfcommand/lib/pages/channel_sequencer_page_controller")
local trigger_edit_page_controller = include("sinfcommand/lib/pages/trigger_edit_page_controller")
local note_edit_page_controller = include("sinfcommand/lib/pages/note_edit_page_controller")
local velocity_edit_page_controller = include("sinfcommand/lib/pages/velocity_edit_page_controller")

local channel_edit_button = Button:new(1, 8)
local channel_sequencer_button = Button:new(2, 8)
local trigger_edit_button = Button:new(3, 8)
local note_edit_button = Button:new(4, 8)
local velocity_edit_button = Button:new(5, 8)

local splash_screen_active = false

local menu_buttons = {}

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

    grid_controller.counter[x][y] = clock.run(grid_controller.long_press, g, x, y)
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
  channel_sequencer_page_controller:register_draw_handlers()
  trigger_edit_page_controller:register_draw_handlers()
  note_edit_page_controller:register_draw_handlers()
  velocity_edit_page_controller:register_draw_handlers()

  draw_handler:register(
    "menu",
    function()
      channel_edit_button:draw()
      channel_sequencer_button:draw()
      trigger_edit_button:draw()
      note_edit_button:draw()
      velocity_edit_button:draw()
    end
  )
end

function register_press_handlers()
  channel_edit_page_controller:register_press_handlers()
  channel_sequencer_page_controller:register_press_handlers()
  trigger_edit_page_controller:register_press_handlers()
  note_edit_page_controller:register_press_handlers()
  velocity_edit_page_controller:register_press_handlers()

  press_handler:register(
  "menu",
  function(x, y)
    if (y == 8) then
      if (x < 6) then
        if program.selected_page ~= x then
          program.selected_page = x
          grid_controller:set_menu_button_state()
        else
          if (clock_controller:is_playing()) then
            clock_controller:stop()
          else
            clock_controller:start()
          end
          grid_controller:set_menu_button_state()
        end

      end
    end
  end
  )
  press_handler:register_long(
    "menu",
    function(x, y)
      if (y == 8) then
        if (x < 6) then
          if program.selected_page == x then
            clock_controller:reset()
          end
        end
      end
    end
    )
end

function grid_controller.splash_screen(frame) 
  for x = 1, 16 do
    for y = 1, 8 do
      local brightness = 2 * math.abs((x + y + frame) % 16 - 8)
      g:led(x, y, brightness)
    end
  end
  fn.dirty_grid(true)
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

  menu_buttons[1] = channel_edit_button
  menu_buttons[2] = channel_sequencer_button
  menu_buttons[3] = trigger_edit_button
  menu_buttons[4] = note_edit_button
  menu_buttons[5] = velocity_edit_button
  
  channel_edit_page_controller:init()
  channel_sequencer_page_controller:init()
  trigger_edit_page_controller:init()
  note_edit_page_controller:init()
  velocity_edit_page_controller:init()

  grid_controller:set_menu_button_state()
  
  register_draw_handlers()
  register_press_handlers()

end


function grid_controller:set_menu_button_state()

  channel_edit_button:set_state((program.selected_page == 1) and 2 or 1)
  channel_edit_button:no_blink()
  channel_sequencer_button:set_state((program.selected_page == 2) and 2 or 1)
  channel_sequencer_button:no_blink()
  trigger_edit_button:set_state((program.selected_page == 3) and 2 or 1)
  trigger_edit_button:no_blink()
  note_edit_button:set_state((program.selected_page == 4) and 2 or 1)
  note_edit_button:no_blink()
  velocity_edit_button:set_state((program.selected_page == 5) and 2 or 1)
  velocity_edit_button:no_blink()

  if (clock_controller:is_playing()) then
    menu_buttons[program.selected_page]:blink()
  end

end

function grid_controller:short_press(x, y)

  press_handler:handle(program.selected_page, x, y)
  fn.dirty_grid(true)
  fn.dirty_screen(true)
  grid_controller.push[x][y].state = "inactive"
  grid_controller.push.active = false
end


function grid_controller:long_press(x, y)
  clock.sleep(.5)
  grid_controller.push[x][y].state = "long_pressed"
  press_handler:handle_long(program.selected_page, x, y)
  fn.dirty_grid(true)
end


function grid_controller:dual_press(x, y, x2, y2)

  press_handler:handle_dual(program.selected_page, x, y, x2, y2)
  fn.dirty_grid(true)
  fn.dirty_screen(true)
  grid_controller.push[x2][y2].state = "inactive"
  grid_controller.push.active = false
end

function grid_controller:alert_disconnect()
  self.disconnect_dismissed = false
end


function grid_controller:dismiss_disconnect()
  self.disconnect_dismissed = true
end


function grid_controller:grid_redraw()
  g:all(0)


  draw_handler:handle(program.selected_page)

  g:refresh()
end

function grid_controller:splash_screen_off()
  splash_screen_active = false
end

function grid_controller:splash_screen_on()
  splash_screen_active = true
end

local splash_screen_frame = 1

function grid_controller.grid_redraw_clock()

  while true do
    clock.sleep(1 / 30)
    if splash_screen_active == true then
      grid_controller.splash_screen(splash_screen_frame)
      splash_screen_frame = splash_screen_frame + 1
      g:refresh()
    else
      if fn.dirty_grid() == true then
        grid_controller:grid_redraw()
        fn.dirty_grid(false)
      end
    end
  end
end

return grid_controller
