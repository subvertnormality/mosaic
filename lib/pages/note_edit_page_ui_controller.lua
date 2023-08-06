local note_edit_page_ui = {}

local Pages = include("patterning/lib/ui_components/Pages")
local Page = include("patterning/lib/ui_components/Page")

local GridViewer = include("patterning/lib/ui_components/GridViewer")

local grid_viewer = GridViewer:new(0, 0)


local grid_viewer_page = Page:new("", function ()
  grid_viewer:draw()

end)

function note_edit_page_ui.register_ui_draw_handlers() 
  draw_handler:register_ui(
    "pattern_note_edit_page",
    function()
      grid_viewer_page:draw()
    end
  )
end

function note_edit_page_ui.init()
  note_edit_page_ui.register_ui_draw_handlers()
end

function note_edit_page_ui.enc(n, d)
  if n == 2 then
    for i=1, math.abs(d) do
      if d > 0 then
        grid_viewer:next_channel()
      else
        grid_viewer:prev_channel()
      end
    end
  end
end

return note_edit_page_ui