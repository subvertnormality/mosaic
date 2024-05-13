local channel_sequencer_page_ui_controller = {}

local fn = include("mosaic/lib/functions")
local pages = include("mosaic/lib/ui_components/pages")
local page = include("mosaic/lib/ui_components/page")
local grid_viewer = include("mosaic/lib/ui_components/grid_viewer")
local value_selector = include("mosaic/lib/ui_components/value_selector")
local list_selector = include("mosaic/lib/ui_components/list_selector")
local pages = pages:new()
local grid_viewer = grid_viewer:new(0, 0)

local tempo_selector = value_selector:new(10, 25, "Tempo", 30, 300)
local pattern_repeat_selector = value_selector:new(10, 25, "Repeats", 1, 16)
local song_mode_selector = list_selector:new(70, 25, "Song mode", {{name = "On", value = 1}, {name = "Off", value = 2}})

local global_settings_page =
  page:new(
  "Global settings",
  function()
    tempo_selector:draw()
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
  tempo_selector:select()
  pattern_repeat_selector:select()
  channel_sequencer_page_ui_controller.register_ui_draw_handlers()
  channel_sequencer_page_ui_controller.refresh_tempo()
  channel_sequencer_page_ui_controller.refresh_pattern_repeat()
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
      if d > 0 then
        if pages:get_selected_page() == 1 then
          if pattern_repeat_selector:is_selected() then
            pattern_repeat_selector:deselect()
            song_mode_selector:select()
          end
        elseif pages:get_selected_page() == 3 then
          grid_viewer:next_channel()
        end
      else
        if pages:get_selected_page() == 1 then
          if song_mode_selector:is_selected() then
            song_mode_selector:deselect()
            pattern_repeat_selector:select()
          end
        elseif pages:get_selected_page() == 3 then
          grid_viewer:prev_channel()
        end
      end
    end
  end

  if n == 3 then
    for i = 1, math.abs(d) do
      if d > 0 then
        if pages:get_selected_page() == 1 then
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
        elseif pages:get_selected_page() == 2 then
          tempo_selector:increment()
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
        end
      else
        if pages:get_selected_page() == 1 then
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
        elseif pages:get_selected_page() == 2 then
          tempo_selector:decrement()
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

function channel_sequencer_page_ui_controller.refresh()
  channel_sequencer_page_ui_controller.refresh_pattern_repeat()
  channel_sequencer_page_ui_controller.refresh_tempo()
  channel_sequencer_page_ui_controller.refresh_song_mode()
end

return channel_sequencer_page_ui_controller
