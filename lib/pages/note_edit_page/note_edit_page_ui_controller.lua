local note_edit_page_ui = {}

local pages = include("mosaic/lib/ui_components/pages")
local page = include("mosaic/lib/ui_components/page")

local grid_viewer = include("mosaic/lib/ui_components/grid_viewer")

local grid_viewer = grid_viewer:new(0, 3)

local grid_viewer_page =
  page:new(
  "",
  function()
    grid_viewer:draw()
  end
)

function note_edit_page_ui.register_ui_draw_handlers()
  draw_handler:register_ui(
    "note_edit_page",
    function()
      grid_viewer_page:draw()
    end
  )
end

function note_edit_page_ui.init()
end

function note_edit_page_ui.enc(n, d)
  if n == 2 then
    for i = 1, math.abs(d) do
      if d > 0 then
        grid_viewer:next_channel()
      else
        grid_viewer:prev_channel()
      end
    end
  end
end

return note_edit_page_ui
