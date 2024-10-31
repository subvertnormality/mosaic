local grid_controller = {}

local fader = include("mosaic/lib/controls/fader")
local sequencer = include("mosaic/lib/controls/sequencer")
local button = include("mosaic/lib/controls/button")

press_handler = include("mosaic/lib/press_handler")
draw_handler = include("mosaic/lib/draw_handler")
grid_abstraction = include("mosaic/lib/grid_abstraction")
grid_abstraction.init()

channel_edit_page_controller = include("mosaic/lib/pages/channel_edit_page/channel_edit_page_controller")
song_edit_page_controller = include("mosaic/lib/pages/song_edit_page/song_edit_page_controller")
scale_edit_page_controller = include("mosaic/lib/pages/scale_edit_page/scale_edit_page_controller")
trigger_edit_page_controller = include("mosaic/lib/pages/trigger_edit_page/trigger_edit_page_controller")
note_edit_page_controller = include("mosaic/lib/pages/note_edit_page/note_edit_page_controller")
velocity_edit_page_controller = include("mosaic/lib/pages/velocity_edit_page/velocity_edit_page_controller")

local play_stop_button = button:new(1, 8)
local pattern_edit_button = button:new(
  program.pages_to_grid_menu_button_mappings.trigger_edit_page, 
  8, 
  {{"off", 2}, {"trig", 5}, {"note", 10}, {"velocity", 15}}
)
local channel_edit_button = button:new(program.pages_to_grid_menu_button_mappings.channel_edit_page, 8)
local scale_edit_button = button:new(program.pages_to_grid_menu_button_mappings.scale_edit_page, 8)
local song_edit_button = button:new(program.pages_to_grid_menu_button_mappings.song_edit_page, 8)

local throttle_time = 0.1

local menu_buttons = {}


local pressed_keys = {}
local dual_in_progress = false

local function sync_current_channel_state()
  if program.get().previous_channel == 17 then
    program.get().previous_channel = 1
  end
  if (program.get_selected_page() == program.pages.scale_edit_page) then
    if program.get().selected_channel ~= 17 then 
      program.get().previous_channel = program.get().selected_channel
    end
    program.get().selected_channel = 17
  else
    if program.get().selected_channel == 17 then
      program.get().selected_channel = program.get().previous_channel or 1
    end
  end
end

function grid.add(new_grid) -- must be grid.add, not g.add (this is a function of the grid class)
  g = grid.connect(new_grid.port) -- connect script to the new grid
  grid_connected = true -- a grid has been connected!
  fn.dirty_grid(true) -- enable flag to redraw grid, because data has changed
end

function grid_controller.get_pressed_keys()
  return pressed_keys
end

local function register_draw_handlers()
  trigger_edit_page_controller.register_draw_handlers()
  note_edit_page_controller.register_draw_handlers()
  velocity_edit_page_controller.register_draw_handlers()
  channel_edit_page_controller.register_draw_handlers()
  scale_edit_page_controller.register_draw_handlers()
  song_edit_page_controller.register_draw_handlers()


  draw_handler:register_grid(
    "menu",
    function()
      play_stop_button:draw()
      pattern_edit_button:draw()
      channel_edit_button:draw()
      scale_edit_button:draw()
      song_edit_button:draw()
    end
  )
end


local function register_press_handlers()
  channel_edit_page_controller.register_press_handlers()
  scale_edit_page_controller.register_press_handlers()
  trigger_edit_page_controller.register_press_handlers()
  note_edit_page_controller.register_press_handlers()
  velocity_edit_page_controller.register_press_handlers()
  song_edit_page_controller.register_press_handlers()

  press_handler:register(
    "menu",
    function(x, y)
      if (y == 8) then
        if 
          x >= program.pages_to_grid_menu_button_mappings.trigger_edit_page and 
          x <= program.pages_to_grid_menu_button_mappings.song_edit_page 
        then
          if (x ~= program.pages_to_grid_menu_button_mappings.trigger_edit_page) then
            if program.get_selected_page() ~= program.grid_menu_to_page_mappings[x] then
              program.set_selected_page(program.grid_menu_to_page_mappings[x])
            end
          elseif (x == program.pages_to_grid_menu_button_mappings.trigger_edit_page) then
            if program.get_selected_page() == program.pages.trigger_edit_page then
              program.set_selected_page(program.pages.note_edit_page)
            elseif program.get_selected_page() == program.pages.note_edit_page then
              program.set_selected_page(program.pages.velocity_edit_page)
            elseif program.get_selected_page() == program.pages.velocity_edit_page then
              program.set_selected_page(program.pages.trigger_edit_page)
            else
              program.set_selected_page(program.pages.trigger_edit_page)
            end
          end

          sync_current_channel_state()
          program.grid_menu_buttons_to_controller_mappings[
            program.pages_to_grid_menu_button_mappings[
              program.page_numbers_to_ids[program.get_selected_page()]
            ]
          ].refresh()
          grid_controller.set_menu_button_state()
          tooltip:show(program.page_names[program.get_selected_page()])
          fn.dirty_screen(true)
          fn.dirty_grid(true)
        end
      end
    end
  )
  press_handler:register(
    "menu",
    function(x, y)
      if (y == 8) then
        if (x == 1) then
          if not clock_controller.is_playing() then
            clock.transport:start()
            tooltip:show("Starting playback")
          else
            local should_stop = params:get("stop_safety") ~= 2 or is_key3_down
            if should_stop then
              clock.transport:stop()
              tooltip:show("Stopping playback")
            end
          end
          grid_controller.set_menu_button_state()
          channel_edit_page_controller.refresh_faders()
        end
      end
    end
  )
  press_handler:register_long(
    "menu",
    function(x, y)
      if (y == 8) then
        if (x == 1) then
          if params:get("stop_safety") == 2 then
            clock.transport:stop()
            tooltip:show("Stopping playback")
            grid_controller.set_menu_button_state()
          end
        end
      end
    end
  )
  press_handler:register_long(
    "menu",
    function(x, y)
      if (y == 8) then
        if 
          x >= program.pages_to_grid_menu_button_mappings.trigger_edit_page and 
          x <= program.pages_to_grid_menu_button_mappings.song_edit_page 
        then
          if program.pages_to_grid_menu_button_mappings[program.page_numbers_to_ids[program.get_selected_page()]] ~= x then
            tooltip:show("Midi Panic")
            clock_controller.panic()
          end
        end
      end
    end
  )
end

function grid_controller.init()
  program.initialise_grid_menu_buttons_to_controller_mappings()
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

  menu_buttons[1] = play_stop_button
  menu_buttons[2] = pattern_edit_button
  menu_buttons[3] = channel_edit_button
  menu_buttons[4] = scale_edit_button
  menu_buttons[5] = song_edit_button


  sync_current_channel_state()

  channel_edit_page_controller.init()
  scale_edit_page_controller.init()
  trigger_edit_page_controller.init()
  note_edit_page_controller.init()
  velocity_edit_page_controller.init()
  song_edit_page_controller.init()

  grid_controller.set_menu_button_state()

  register_draw_handlers()
  register_press_handlers()
  
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


  function g.remove()
    grid_controller.alert_disconnect()
  end

end

function grid_controller.set_menu_button_state()
  local selected_page = program.get_selected_page()
  channel_edit_button:set_state(selected_page == program.pages.channel_edit_page and 2 or 1)
  scale_edit_button:set_state(selected_page == program.pages.scale_edit_page and 2 or 1)
  if selected_page >= program.pages.trigger_edit_page and selected_page <= program.pages.velocity_edit_page then
    pattern_edit_button:set_state(
      selected_page == program.pages.trigger_edit_page and 2 or 
      selected_page == program.pages.note_edit_page and 3 or 
      selected_page == program.pages.velocity_edit_page and 4
    )
  else
    pattern_edit_button:set_state(1)
  end

  song_edit_button:set_state(selected_page == program.pages.song_edit_page and 2 or 1)

  if (clock_controller.is_playing()) then
    menu_buttons[1]:blink()
  else
    menu_buttons[1]:no_blink()
  end
end

function grid_controller.pre_press(x, y)
  press_handler:handle_pre(program.get_selected_page(), x, y)
  fn.dirty_grid(true)
  fn.dirty_screen(true)
end

function grid_controller.post_press(x, y)
  press_handler:handle_post(program.get_selected_page(), x, y)
  fn.dirty_grid(true)
  fn.dirty_screen(true)
end

function grid_controller.short_press(x, y)
  press_handler:handle(program.get_selected_page(), x, y)
  fn.dirty_grid(true)
  fn.dirty_screen(true)
end

function grid_controller.long_press(x, y)
  clock.sleep(1)
  grid_controller.long_press_active[x][y] = true
  press_handler:handle_long(program.get_selected_page(), x, y)
  fn.dirty_grid(true)
end

function grid_controller.dual_press(x, y, x2, y2)
  press_handler:handle_dual(program.get_selected_page(), x, y, x2, y2)
  fn.dirty_grid(true)
  fn.dirty_screen(true)
end

function grid_controller.redraw()
  g:all(0)

  draw_handler:handle_grid(program.get_selected_page())

  g:refresh()
end


function grid_controller.grid_redraw()
  if grid_connected then
    if fn.dirty_grid() == true then
      grid_controller.redraw()
      fn.dirty_grid(false)
    end
  end
end

function grid_controller.refresh()
  channel_edit_page_controller.refresh()
  song_edit_page_controller.refresh()
  trigger_edit_page_controller.refresh()
  note_edit_page_controller.refresh()
  velocity_edit_page_controller.refresh()
  grid_controller.set_menu_button_state()
end

function grid_controller.alert_disconnect() 
  print("Grid disconnected")
end

return grid_controller
