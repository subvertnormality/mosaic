local velocity_edit_page_ui = {}

local grid_viewer = include("mosaic/lib/ui_components/grid_viewer")

local grid_viewer = grid_viewer:new(0, 3)

function velocity_edit_page_ui.change_page(subpage_name)
end

function velocity_edit_page_ui.register_ui_draws()
  draw:register_ui(
    "velocity_edit_page",
    function()
      grid_viewer:draw()
    end
  )
end

function velocity_edit_page_ui.init()
end

function velocity_edit_page_ui.enc(n, d)
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

return velocity_edit_page_ui
