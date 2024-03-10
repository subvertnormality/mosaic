local grid_controller = {}
local fn = include("mosaic/lib/functions")

local Fader = include("mosaic/lib/controls/Fader")
local Sequencer = include("mosaic/lib/controls/Sequencer")
local Button = include("mosaic/lib/controls/Button")

press_handler = include("mosaic/lib/press_handler")
draw_handler = include("mosaic/lib/draw_handler")
grid_abstraction = include("mosaic/lib/grid_abstraction")
grid_abstraction.init()

channel_edit_page_controller = include("mosaic/lib/pages/channel_edit_page_controller")
channel_sequencer_page_controller = include("mosaic/lib/pages/channel_sequencer_page_controller")

local trigger_edit_page_controller = include("mosaic/lib/pages/trigger_edit_page_controller")
local note_edit_page_controller = include("mosaic/lib/pages/note_edit_page_controller")
local velocity_edit_page_controller = include("mosaic/lib/pages/velocity_edit_page_controller")

local channel_edit_button = Button:new(1, 8)
local channel_sequencer_button = Button:new(2, 8)
local trigger_edit_button = Button:new(3, 8)
local note_edit_button = Button:new(4, 8)
local velocity_edit_button = Button:new(5, 8)

local splash_screen_active = true

local menu_buttons = {}

local page_names = {
  "Channel Edit Page",
  "Channel Sequencer Page",
  "Pattern Trigger Edit Page",
  "Pattern Note Edit Page",
  "Pattern Velocity Edit Page"
}

local pressed_keys = {}
local dual_in_progress = false

g = grid.connect()

function g.key(x, y, z)
  if z == 1 then
    table.insert(pressed_keys, {x, y})
    grid_controller.pre_press(x, y)
    grid_controller.counter[x][y] = clock.run(grid_controller.long_press, x, y)
  elseif z == 0 then -- otherwise, if a grid key is released...
    fn.remove_table_from_table(pressed_keys, {x, y})

    local held_button = pressed_keys[1]

    if grid_controller.counter[x][y] then -- and the long press is still waiting...
      clock.cancel(grid_controller.counter[x][y]) -- then cancel the long press clock,

      if grid_controller.long_press_active[x][y] == true then
        grid_controller.long_press_active[x][y] = false
      elseif held_button ~= nil then
        if grid_controller.counter[held_button[1]][held_button[2]] then
          clock.cancel(grid_controller.counter[held_button[1]][held_button[2]])
        end
        grid_controller.dual_press(held_button[1], held_button[2], x, y)
        dual_in_progress = true
      else
        if dual_in_progress ~= true then
          grid_controller.short_press(x, y) -- and execute a short press instead.
        end
        dual_in_progress = false
      end
    end
    grid_controller.post_press(x, y)
  end
end

function grid_controller.get_pressed_keys()
  return pressed_keys
end

function g.remove()
  grid_controller.alert_disconnect()
end

local function refresh_pages()
  channel_edit_page_controller.refresh()
  channel_sequencer_page_controller.refresh()
  channel_edit_page_ui_controller.refresh()
  -- trigger_edit_page_controller.refresh()
  -- note_edit_page_controller.refresh()
  -- velocity_edit_page_controller.refresh()
end

local function register_draw_handlers()
  channel_edit_page_controller.register_draw_handlers()
  channel_sequencer_page_controller.register_draw_handlers()
  trigger_edit_page_controller.register_draw_handlers()
  note_edit_page_controller.register_draw_handlers()
  velocity_edit_page_controller.register_draw_handlers()

  draw_handler:register_grid(
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
  channel_edit_page_controller.register_press_handlers()
  channel_sequencer_page_controller.register_press_handlers()
  trigger_edit_page_controller.register_press_handlers()
  note_edit_page_controller.register_press_handlers()
  velocity_edit_page_controller.register_press_handlers()

  press_handler:register(
    "menu",
    function(x, y)
      if (y == 8) then
        if (x < 6) then
          if program.get().selected_page ~= x then
            program.get().selected_page = x
            refresh_pages()
            grid_controller.set_menu_button_state()
            tooltip:show(page_names[program.get().selected_page])
          else
            if (not clock_controller.is_playing()) then
              clock_controller:start()
              tooltip:show("Starting playback")
            end
            grid_controller.set_menu_button_state()
          end
          grid_controller.refresh()
          fn.dirty_screen(true)
        end
      end
    end
  )
  press_handler:register_long(
    "menu",
    function(x, y)
      if (y == 8) then
        if (x < 6) then
          if program.get().selected_page ~= x then
            clock_controller.panic()
            tooltip:show("Midi Panic")
          else
            if (clock_controller.is_playing()) then
              clock_controller:stop()
              tooltip:show("Stopping playback")
            end
            grid_controller.set_menu_button_state()
          end
          grid_controller.refresh()
          fn.dirty_screen(true)
        end
      end
    end
  )
end

function grid_controller.init()
  grid_controller.counter = {}
  grid_controller.toggled = {}
  grid_controller.long_press_active = {}
  grid_controller.disconnect_dismissed = true
  for x = 1, 16 do
    grid_controller.counter[x] = {}
    grid_controller.long_press_active[x] = {}
    for y = 1, 8 do
      grid_controller.counter[x][y] = nil
      grid_controller.long_press_active[x][y] = {}
    end
  end

  menu_buttons[1] = channel_edit_button
  menu_buttons[2] = channel_sequencer_button
  menu_buttons[3] = trigger_edit_button
  menu_buttons[4] = note_edit_button
  menu_buttons[5] = velocity_edit_button

  channel_edit_page_controller.init()
  channel_sequencer_page_controller.init()
  trigger_edit_page_controller.init()
  note_edit_page_controller.init()
  velocity_edit_page_controller.init()

  grid_controller.set_menu_button_state()

  register_draw_handlers()
  register_press_handlers()
end

function grid_controller.set_menu_button_state()
  channel_edit_button:set_state((program.get().selected_page == 1) and 2 or 1)
  channel_edit_button:no_blink()
  channel_sequencer_button:set_state((program.get().selected_page == 2) and 2 or 1)
  channel_sequencer_button:no_blink()
  trigger_edit_button:set_state((program.get().selected_page == 3) and 2 or 1)
  trigger_edit_button:no_blink()
  note_edit_button:set_state((program.get().selected_page == 4) and 2 or 1)
  note_edit_button:no_blink()
  velocity_edit_button:set_state((program.get().selected_page == 5) and 2 or 1)
  velocity_edit_button:no_blink()

  if (clock_controller.is_playing()) then
    menu_buttons[program.get().selected_page]:blink()
  end
end

function grid_controller.pre_press(x, y)
  press_handler:handle_pre(program.get().selected_page, x, y)
  fn.dirty_grid(true)
  fn.dirty_screen(true)
end

function grid_controller.post_press(x, y)
  press_handler:handle_post(program.get().selected_page, x, y)
  fn.dirty_grid(true)
  fn.dirty_screen(true)
end

function grid_controller.short_press(x, y)
  press_handler:handle(program.get().selected_page, x, y)
  fn.dirty_grid(true)
  fn.dirty_screen(true)
end

function grid_controller.long_press(x, y)
  clock.sleep(1)
  grid_controller.long_press_active[x][y] = true
  press_handler:handle_long(program.get().selected_page, x, y)
  fn.dirty_grid(true)
end

function grid_controller.dual_press(x, y, x2, y2)
  press_handler:handle_dual(program.get().selected_page, x, y, x2, y2)
  fn.dirty_grid(true)
  fn.dirty_screen(true)
end

function grid_controller.redraw()
  g:all(0)

  draw_handler:handle_grid(program.get().selected_page)

  g:refresh()
end

function grid_controller.deactivate_splash_screen()
  splash_screen_active = false
end


function grid_controller.grid_redraw()
  if splash_screen_active == false then
    if fn.dirty_grid() == true then
      grid_controller.redraw()
      fn.dirty_grid(false)
    end
  end
end

function grid_controller.refresh()
  channel_edit_page_controller.refresh()
  channel_sequencer_page_controller.refresh()
  trigger_edit_page_controller.refresh()
  note_edit_page_controller.refresh()
  velocity_edit_page_controller.refresh()
end

return grid_controller
