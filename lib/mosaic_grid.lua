local mosaic_grid = {}

local fader = include("mosaic/lib/controls/fader")
local sequencer = include("mosaic/lib/controls/sequencer")
local button = include("mosaic/lib/controls/button")

press = include("mosaic/lib/press")
draw = include("mosaic/lib/draw")
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
  pages.pages_to_grid_menu_button_mappings.trigger_edit_page, 
  8, 
  {{"off", 2}, {"trig", 5}, {"note", 10}, {"velocity", 15}}
)
local channel_edit_button = button:new(pages.pages_to_grid_menu_button_mappings.channel_edit_page, 8)
local scale_edit_button = button:new(pages.pages_to_grid_menu_button_mappings.scale_edit_page, 8)
local song_edit_button = button:new(pages.pages_to_grid_menu_button_mappings.song_edit_page, 8)

local throttle_time = 0.1

local menu_buttons = {}


local pressed_keys = {}
local dual_in_progress = false

local function sync_current_channel_state()
  if program.get().previous_channel == 17 then
    program.get().previous_channel = 1
  end
  if (program.get_selected_page() == pages.pages.scale_edit_page) then
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

function mosaic_grid.get_pressed_keys()
  return pressed_keys
end

local function register_draws()
  trigger_edit_page_controller.register_draws()
  note_edit_page_controller.register_draws()
  velocity_edit_page_controller.register_draws()
  channel_edit_page_controller.register_draws()
  scale_edit_page_controller.register_draws()
  song_edit_page_controller.register_draws()


  draw:register_grid(
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


local function register_presss()
  channel_edit_page_controller.register_presss()
  scale_edit_page_controller.register_presss()
  trigger_edit_page_controller.register_presss()
  note_edit_page_controller.register_presss()
  velocity_edit_page_controller.register_presss()
  song_edit_page_controller.register_presss()

  press:register(
    "menu",
    function(x, y)
      if (y == 8) then
        if 
          x >= pages.pages_to_grid_menu_button_mappings.channel_edit_page and 
          x <= pages.pages_to_grid_menu_button_mappings.song_edit_page 
        then
          if (x ~= pages.pages_to_grid_menu_button_mappings.trigger_edit_page) then
            if program.get_selected_page() ~= pages.grid_menu_to_page_mappings[x] then
              program.set_selected_page(pages.grid_menu_to_page_mappings[x])
            end
          elseif (x == pages.pages_to_grid_menu_button_mappings.trigger_edit_page) then
            if program.get_selected_page() == pages.pages.trigger_edit_page then
              program.set_selected_page(pages.pages.note_edit_page)
            elseif program.get_selected_page() == pages.pages.note_edit_page then
              program.set_selected_page(pages.pages.velocity_edit_page)
            elseif program.get_selected_page() == pages.pages.velocity_edit_page then
              program.set_selected_page(pages.pages.trigger_edit_page)
            else
              program.set_selected_page(pages.pages.trigger_edit_page)
            end
          end

          sync_current_channel_state()

          pages.page_to_controller_mappings[program.get_selected_page()].refresh()
          mosaic_grid.set_menu_button_state()
          tooltip:show(pages.page_names[program.get_selected_page()])
          fn.dirty_screen(true)
          fn.dirty_grid(true)
        end
      end
    end
  )
  press:register(
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
          mosaic_grid.set_menu_button_state()
          channel_edit_page_controller.refresh_faders()
        end
      end
    end
  )
  press:register_long(
    "menu",
    function(x, y)
      if (y == 8) then
        if (x == 1) then
          if params:get("stop_safety") == 2 then
            clock.transport:stop()
            tooltip:show("Stopping playback")
            mosaic_grid.set_menu_button_state()
          end
        end
      end
    end
  )
  press:register_long(
    "menu",
    function(x, y)
      if (y == 8) then
        if 
          x >= pages.pages_to_grid_menu_button_mappings.trigger_edit_page and 
          x <= pages.pages_to_grid_menu_button_mappings.song_edit_page 
        then
          if pages.pages_to_grid_menu_button_mappings[pages.page_numbers_to_ids[program.get_selected_page()]] ~= x then
            tooltip:show("Midi Panic")
            clock_controller.panic()
          end
        end
      end
    end
  )
end

function mosaic_grid.init()
  pages.initialise_page_controller_mappings()
  mosaic_grid.counter = {}
  mosaic_grid.toggled = {}
  mosaic_grid.long_press_active = {}
  mosaic_grid.disconnect_dismissed = true
  for x = 1, 16 do
    mosaic_grid.counter[x] = {}
    mosaic_grid.long_press_active[x] = {}
    for y = 1, 8 do
      mosaic_grid.counter[x][y] = nil
      mosaic_grid.long_press_active[x][y] = {}
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

  mosaic_grid.set_menu_button_state()

  register_draws()
  register_presss()
  
  function g.key(x, y, z)

    if z == 1 then
      table.insert(pressed_keys, {x, y})
      mosaic_grid.pre_press(x, y)
      mosaic_grid.counter[x][y] = clock.run(mosaic_grid.long_press, x, y)
    elseif z == 0 then -- otherwise, if a grid key is released...
      fn.remove_table_from_table(pressed_keys, {x, y})
  
      local held_button = pressed_keys[1]
  

      if mosaic_grid.counter[x][y] then -- and the long press is still waiting...
        clock.cancel(mosaic_grid.counter[x][y]) -- then cancel the long press clock,
  
        if mosaic_grid.long_press_active[x][y] == true then
          mosaic_grid.long_press_active[x][y] = false
        elseif held_button ~= nil then
          if mosaic_grid.counter[held_button[1]][held_button[2]] then
            clock.cancel(mosaic_grid.counter[held_button[1]][held_button[2]])
          end
          mosaic_grid.dual_press(held_button[1], held_button[2], x, y)
          dual_in_progress = true
        else
          if dual_in_progress ~= true then
            mosaic_grid.short_press(x, y) -- and execute a short press instead.
          end
          dual_in_progress = false
        end
      end
      mosaic_grid.post_press(x, y)
    end
  end


  function g.remove()
    mosaic_grid.alert_disconnect()
  end

end

function mosaic_grid.set_menu_button_state()
  local selected_page = program.get_selected_page()
  channel_edit_button:set_state(selected_page == pages.pages.channel_edit_page and 2 or 1)
  scale_edit_button:set_state(selected_page == pages.pages.scale_edit_page and 2 or 1)
  if selected_page >= pages.pages.trigger_edit_page and selected_page <= pages.pages.velocity_edit_page then
    pattern_edit_button:set_state(
      selected_page == pages.pages.trigger_edit_page and 2 or 
      selected_page == pages.pages.note_edit_page and 3 or 
      selected_page == pages.pages.velocity_edit_page and 4
    )
  else
    pattern_edit_button:set_state(1)
  end

  song_edit_button:set_state(selected_page == pages.pages.song_edit_page and 2 or 1)

  if (clock_controller.is_playing()) then
    menu_buttons[1]:blink()
  else
    menu_buttons[1]:no_blink()
  end
end

function mosaic_grid.pre_press(x, y)
  press:handle_pre(program.get_selected_page(), x, y)
  fn.dirty_grid(true)
  fn.dirty_screen(true)
end

function mosaic_grid.post_press(x, y)
  press:handle_post(program.get_selected_page(), x, y)
  fn.dirty_grid(true)
  fn.dirty_screen(true)
end

function mosaic_grid.short_press(x, y)
  press:handle(program.get_selected_page(), x, y)
  fn.dirty_grid(true)
  fn.dirty_screen(true)
end

function mosaic_grid.long_press(x, y)
  clock.sleep(1)
  mosaic_grid.long_press_active[x][y] = true
  press:handle_long(program.get_selected_page(), x, y)
  fn.dirty_grid(true)
end

function mosaic_grid.dual_press(x, y, x2, y2)
  press:handle_dual(program.get_selected_page(), x, y, x2, y2)
  fn.dirty_grid(true)
  fn.dirty_screen(true)
end

function mosaic_grid.redraw()
  g:all(0)

  draw:handle_grid(program.get_selected_page())

  g:refresh()
end


function mosaic_grid.grid_redraw()
  if grid_connected then
    if fn.dirty_grid() == true then
      mosaic_grid.redraw()
      fn.dirty_grid(false)
    end
  end
end

function mosaic_grid.refresh()
  channel_edit_page_controller.refresh()
  song_edit_page_controller.refresh()
  trigger_edit_page_controller.refresh()
  note_edit_page_controller.refresh()
  velocity_edit_page_controller.refresh()
  mosaic_grid.set_menu_button_state()
end

function mosaic_grid.alert_disconnect() 
  print("Grid disconnected")
end

return mosaic_grid
