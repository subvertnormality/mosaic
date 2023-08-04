local trigger_edit_page_ui_controller = {}

local Pages = include("sinfcommand/lib/ui_components/Pages")
local Page = include("sinfcommand/lib/ui_components/Page")
local GridViewer = include("sinfcommand/lib/ui_components/GridViewer")

local pages = Pages:new()
local grid_viewer = GridViewer:new(0, 0)

function trigger_edit_page_ui_controller.change_page(subpage_name)
  -- pages:select_page(subpage_name)
end


local grid_viewer_page = Page:new("", function ()
  grid_viewer:draw()

end)

local trig_edit_options_page = Page:new("Trig editor options", function ()

end)


function trigger_edit_page_ui_controller.register_ui_draw_handlers() 
  draw_handler:register_ui(
    "pattern_trigger_edit_page",
    function()
      pages:draw()
    end
  )
end

function trigger_edit_page_ui_controller.init()
  pages:add_page(grid_viewer_page)
  pages:add_page(trig_edit_options_page)
  pages:select_page(1)
  trigger_edit_page_ui_controller.register_ui_draw_handlers()
end

function trigger_edit_page_ui_controller.enc(n, d)
  if n == 2 then
    for i=1, math.abs(d) do
      if d > 0 then
        grid_viewer:next_channel()
      else
        grid_viewer:prev_channel()
      end
    end
  end

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
end

return trigger_edit_page_ui_controller