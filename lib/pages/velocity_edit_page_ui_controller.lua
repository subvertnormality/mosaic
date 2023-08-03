local velocity_edit_page_ui_controller = {}

local Pages = include("sinfcommand/lib/ui_components/Pages")
local Page = include("sinfcommand/lib/ui_components/Page")

local pages = Pages:new()

local GridViewer = include("sinfcommand/lib/ui_components/GridViewer")

local grid_viewer = GridViewer:new(0, 0)

function velocity_edit_page_ui_controller.change_page(subpage_name)
  -- pages:select_page(subpage_name)
end


local grid_viewer_page = Page:new("", function ()
  grid_viewer:draw()

end)

function velocity_edit_page_ui_controller.register_ui_draw_handlers() 
  draw_handler:register_ui(
    "pattern_velocity_edit_page",
    function()
      pages:draw()
    end
  )
end

function velocity_edit_page_ui_controller.init()
  pages:add_page(grid_viewer_page)
  pages:select_page(1)
  velocity_edit_page_ui_controller.register_ui_draw_handlers()
end

function velocity_edit_page_ui_controller.enc(n, d)

end

return velocity_edit_page_ui_controller