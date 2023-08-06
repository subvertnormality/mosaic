local channel_sequencer_page_ui_controller = {}

local Pages = include("sinfcommand/lib/ui_components/Pages")
local Page = include("sinfcommand/lib/ui_components/Page")
local GridViewer = include("sinfcommand/lib/ui_components/GridViewer")
local ValueSelector = include("sinfcommand/lib/ui_components/ValueSelector")
local pages = Pages:new()
local grid_viewer = GridViewer:new(0, 0)

local tempo_selector = ValueSelector:new(10, 30, "Tempo", 30, 300)
local pattern_repeat_selector = ValueSelector:new(10, 30, "Repeat sequence", 1, 16)

local global_settings_page = Page:new("Global settings", function ()
  tempo_selector:draw()
end)

local song_progression_page = Page:new("Song progression", function ()
  pattern_repeat_selector:draw()
end)

local page_to_index = {
  ["Song progression"] = 1,
  ["Global settings"] = 2,
  ["Grid viewer"] = 3
}

local grid_viewer_page = Page:new("", function ()
  grid_viewer:draw()
end)

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
    for i=1, math.abs(d) do
      if d > 0 then
        pages:next_page()
        fn.dirty_screen(true)

      else
        pages:previous_page()
        fn.dirty_screen(true)
      end
    end
  end

  if n == 3 then
    for i=1, math.abs(d) do
      if d > 0 then
        if pages:get_selected_page() == 1 then
          pattern_repeat_selector:increment()
          channel_sequencer_page_ui_controller.update_pattern_repeat()

        elseif pages:get_selected_page() == 2 then

          tempo_selector:increment()
          channel_sequencer_page_ui_controller.update_tempo() 

        end

      else
        if pages:get_selected_page() == 1 then

          pattern_repeat_selector:decrement()
          channel_sequencer_page_ui_controller.update_pattern_repeat()

        elseif pages:get_selected_page() == 2 then

          tempo_selector:decrement()
          channel_sequencer_page_ui_controller.update_tempo() 
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

function channel_sequencer_page_ui_controller.refresh_tempo() 
  tempo_selector:set_value(params:get("clock_tempo"))
end

function channel_sequencer_page_ui_controller.refresh_pattern_repeat() 
  pattern_repeat_selector:set_value(program.get_selected_sequencer_pattern().repeats)
end

function channel_sequencer_page_ui_controller.refresh() 
  channel_sequencer_page_ui_controller.refresh_pattern_repeat() 
  channel_sequencer_page_ui_controller.refresh_tempo() 
end

return channel_sequencer_page_ui_controller