local channel_sequencer_page_ui_controller = {}


local pages = include("mosaic/lib/ui_components/pages")
local page = include("mosaic/lib/ui_components/page")
local gv = include("mosaic/lib/ui_components/grid_viewer")
local value_selector = include("mosaic/lib/ui_components/value_selector")
local list_selector = include("mosaic/lib/ui_components/list_selector")
local pages = pages:new()
local grid_viewer = gv:new(0, 3)

local tempo_selector = value_selector:new(0, 18, "Tempo", 30, 300)
local pattern_repeat_selector = value_selector:new(0, 29, "Repeats", 1, 16)
local song_mode_selector = list_selector:new(70, 29, "Song mode", {{name = "Off", value = 1}, {name = "On", value = 2}})

local swing_shuffle_type = list_selector:new(70, 18, "Swing type", {{name = "Swing", value = 1}, {name = "Shuffle", value = 2}})
local swing_selector = value_selector:new(0, 40, "Swing", -50, 50)
local shuffle_feel_selector = list_selector:new(0, 40, "Feel", {{name = "Drunk", value = 1}, {name = "Smooth", value = 2}, {name = "Heavy", value = 3}, {name = "Clave", value = 4}})
local shuffle_basis_selector = list_selector:new(40, 40, "Basis", {{name = "9", value = 1}, {name = "7", value = 2}, {name = "5", value = 3}, {name = "6", value = 4}, {name = "8??", value = 5}, {name = "9??", value = 6}})
local shuffle_amount_selector = value_selector:new(70, 40, "Amount", 0, 100)



local global_settings_page =
  page:new(
  "Global settings",
  function()
    tempo_selector:draw()
    swing_shuffle_type:draw()
    if swing_shuffle_type:get_selected().value == 1 then
      swing_selector:draw()
    else
      shuffle_feel_selector:draw()
      shuffle_basis_selector:draw()
      shuffle_amount_selector:draw()
    end
  end
)

local song_progression_page =
  page:new(
  "Song progression",
  function()
    pattern_repeat_selector:draw()
    song_mode_selector:draw()
  end
)

local page_to_index = {
  ["Song progression"] = 1,
  ["Global settings"] = 2,
  ["Grid viewer"] = 3
}

local grid_viewer_page =
  page:new(
  "",
  function()
    grid_viewer:draw()
  end
)

function channel_sequencer_page_ui_controller.init()
  pages:add_page(song_progression_page)
  pages:add_page(global_settings_page)
  pages:add_page(grid_viewer_page)
  pages:select_page(1)
  pattern_repeat_selector:select()
  tempo_selector:select()
  channel_sequencer_page_ui_controller.register_ui_draw_handlers()
  channel_sequencer_page_ui_controller.refresh()
end

function channel_sequencer_page_ui_controller.register_ui_draw_handlers()
  draw_handler:register_ui(
    "channel_sequencer_page",
    function()
      pages:draw()
    end
  )
end

function channel_sequencer_page_ui_controller.change_page(subpage_name)
  pages:select_page(subpage_name)
end

-- Function to get currently visible selectors based on swing type
local function get_visible_selectors()
  local selectors = {tempo_selector, swing_shuffle_type}
  if swing_shuffle_type:get_selected().value == 1 then
    table.insert(selectors, swing_selector)
  else
    table.insert(selectors, shuffle_feel_selector)
    table.insert(selectors, shuffle_basis_selector)
    table.insert(selectors, shuffle_amount_selector)
  end
  return selectors
end

function channel_sequencer_page_ui_controller.enc(n, d)
  if n == 1 then
    for i = 1, math.abs(d) do
      if d > 0 then
        pages:next_page()
        fn.dirty_screen(true)
      else
        pages:previous_page()
        fn.dirty_screen(true)
      end
    end
  end

  if n == 2 then
    for i = 1, math.abs(d) do
      if pages:get_selected_page() == 1 then
        -- Handle navigation on 'Song progression' page
        if d > 0 then
          if pattern_repeat_selector:is_selected() then
            pattern_repeat_selector:deselect()
            song_mode_selector:select()
          end
        else
          if song_mode_selector:is_selected() then
            song_mode_selector:deselect()
            pattern_repeat_selector:select()
          end
        end
      elseif pages:get_selected_page() == 2 then
        -- Handle navigation on 'Global settings' page
        local selectors = get_visible_selectors()
        local current_index = nil
        for idx, selector in ipairs(selectors) do
          if selector:is_selected() then
            current_index = idx
            break
          end
        end

        if current_index then
          if d > 0 then
            if current_index < #selectors then
              selectors[current_index]:deselect()
              selectors[current_index + 1]:select()
            end
          else
            if current_index > 1 then
              selectors[current_index]:deselect()
              selectors[current_index - 1]:select()
            end
          end
        else
          -- No selector is currently selected, select the first one
          selectors[1]:select()
        end
      elseif pages:get_selected_page() == 3 then
        -- Handle navigation on 'Grid viewer' page
        if d > 0 then
          grid_viewer:next_channel()
        else
          grid_viewer:prev_channel()
        end
      end
    end
  end

  if n == 3 then
    for i = 1, math.abs(d) do
      if pages:get_selected_page() == 1 then
        if d > 0 then
          if song_mode_selector:is_selected() then
            song_mode_selector:increment()
            save_confirm.set_save(
              function()
                channel_sequencer_page_ui_controller.update_song_mode()
              end
            )
            save_confirm.set_cancel(
              function()
                channel_sequencer_page_ui_controller.refresh_song_mode()
              end
            )
          elseif pattern_repeat_selector:is_selected() then
            pattern_repeat_selector:increment()
            save_confirm.set_save(
              function()
                channel_sequencer_page_ui_controller.update_pattern_repeat()
              end
            )
            save_confirm.set_cancel(
              function()
                channel_sequencer_page_ui_controller.refresh_pattern_repeat()
              end
            )
          end
        else
          if song_mode_selector:is_selected() then
            song_mode_selector:decrement()
            save_confirm.set_save(
              function()
                channel_sequencer_page_ui_controller.update_song_mode()
              end
            )
            save_confirm.set_cancel(
              function()
                channel_sequencer_page_ui_controller.refresh_song_mode()
              end
            )
          elseif pattern_repeat_selector:is_selected() then
            pattern_repeat_selector:decrement()
            save_confirm.set_save(
              function()
                channel_sequencer_page_ui_controller.update_pattern_repeat()
              end
            )
            save_confirm.set_cancel(
              function()
                channel_sequencer_page_ui_controller.refresh_pattern_repeat()
              end
            )
          end
        end
      elseif pages:get_selected_page() == 2 then
        local selectors = get_visible_selectors()
        for _, selector in ipairs(selectors) do
          if selector:is_selected() then
            if d > 0 then
              selector:increment()
            else
              selector:decrement()
            end

            -- Handle save and cancel actions
            if selector == tempo_selector then
              save_confirm.set_save(
                function()
                  channel_sequencer_page_ui_controller.update_tempo()
                end
              )
              save_confirm.set_cancel(
                function()
                  channel_sequencer_page_ui_controller.refresh_tempo()
                end
              )
            elseif selector == swing_shuffle_type then
              save_confirm.set_save(
                function()
                  channel_sequencer_page_ui_controller.update_swing_shuffle_type()
                end
              )
              save_confirm.set_cancel(
                function()
                  channel_sequencer_page_ui_controller.refresh_swing_shuffle_type()
                end
              )
              -- After changing swing type, refresh the screen but keep selection
              fn.dirty_screen(true)
            elseif selector == swing_selector then
              save_confirm.set_save(
                function()
                  channel_sequencer_page_ui_controller.update_swing()
                end
              )
              save_confirm.set_cancel(
                function()
                  channel_sequencer_page_ui_controller.refresh_swing()
                end
              )
            elseif selector == shuffle_feel_selector then
              save_confirm.set_save(
                function()
                  channel_sequencer_page_ui_controller.update_shuffle_feel()
                end
              )
              save_confirm.set_cancel(
                function()
                  channel_sequencer_page_ui_controller.refresh_shuffle_feel()
                end
              )
            elseif selector == shuffle_basis_selector then
              save_confirm.set_save(
                function()
                  channel_sequencer_page_ui_controller.update_shuffle_basis()
                end
              )
              save_confirm.set_cancel(
                function()
                  channel_sequencer_page_ui_controller.refresh_shuffle_basis()
                end
              )
            elseif selector == shuffle_amount_selector then
              save_confirm.set_save(
                function()
                  channel_sequencer_page_ui_controller.update_shuffle_amount()
                end
              )
              save_confirm.set_cancel(
                function()
                  channel_sequencer_page_ui_controller.refresh_shuffle_amount()
                end
              )
            end
            break -- Exit after handling the selected parameter
          end
        end
      end
    end
  end
end

function channel_sequencer_page_ui_controller.update_tempo()
  params:set("clock_tempo", tempo_selector:get_value())
end

function channel_sequencer_page_ui_controller.update_pattern_repeat()
  program.get_selected_sequencer_pattern().repeats = pattern_repeat_selector:get_value()
  program.get_selected_sequencer_pattern().active = true
end

function channel_sequencer_page_ui_controller.update_song_mode()
  params:set("song_mode", song_mode_selector:get_selected().value)
end

function channel_sequencer_page_ui_controller.refresh_song_mode()
  song_mode_selector:set_selected_value(params:get("song_mode"))
end

function channel_sequencer_page_ui_controller.refresh_tempo()
  tempo_selector:set_value(params:get("clock_tempo"))
end

function channel_sequencer_page_ui_controller.refresh_pattern_repeat()
  pattern_repeat_selector:set_value(program.get_selected_sequencer_pattern().repeats)
end

function channel_sequencer_page_ui_controller.update_swing_shuffle_type()
  params:set("global_swing_shuffle_type", swing_shuffle_type:get_selected().value)
  fn.dirty_screen(true)
end

function channel_sequencer_page_ui_controller.refresh_swing_shuffle_type()
  swing_shuffle_type:set_selected_value(params:get("global_swing_shuffle_type"))
  fn.dirty_screen(true)
end

function channel_sequencer_page_ui_controller.update_swing()
  params:set("global_swing", swing_selector:get_value())
end

function channel_sequencer_page_ui_controller.refresh_swing()
  swing_selector:set_value(params:get("global_swing"))
end

function channel_sequencer_page_ui_controller.update_shuffle_feel()
  params:set("global_shuffle_feel", shuffle_feel_selector:get_selected().value)
end

function channel_sequencer_page_ui_controller.refresh_shuffle_feel()
  shuffle_feel_selector:set_selected_value(params:get("global_shuffle_feel"))
end

function channel_sequencer_page_ui_controller.update_shuffle_basis()
  params:set("global_shuffle_basis", shuffle_basis_selector:get_selected().value)
end

function channel_sequencer_page_ui_controller.refresh_shuffle_basis()
  shuffle_basis_selector:set_selected_value(params:get("global_shuffle_basis"))
end

function channel_sequencer_page_ui_controller.update_shuffle_amount()
  params:set("global_shuffle_amount", shuffle_amount_selector:get_value())
end

function channel_sequencer_page_ui_controller.refresh_shuffle_amount()
  shuffle_amount_selector:set_value(params:get("global_shuffle_amount"))
end

function channel_sequencer_page_ui_controller.refresh()
  channel_sequencer_page_ui_controller.refresh_pattern_repeat()
  channel_sequencer_page_ui_controller.refresh_tempo()
  channel_sequencer_page_ui_controller.refresh_song_mode()
  channel_sequencer_page_ui_controller.refresh_swing_shuffle_type()
  channel_sequencer_page_ui_controller.refresh_swing()
  channel_sequencer_page_ui_controller.refresh_shuffle_feel()
  channel_sequencer_page_ui_controller.refresh_shuffle_basis()
end

return channel_sequencer_page_ui_controller
