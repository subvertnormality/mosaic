local trigger_edit_page_ui_controller = {}


local pages = include("mosaic/lib/ui_components/pages")
local page = include("mosaic/lib/ui_components/page")
local grid_viewer = include("mosaic/lib/ui_components/grid_viewer")
local list_selector = include("mosaic/lib/ui_components/list_selector")

local pages = pages:new()
local grid_viewer = grid_viewer:new(0, 3)
local tresillo_mult =
  list_selector:new(
  0,
  29,
  "Tresillo mult",
  {
    {id = 1, value = 8, name = "x8"},
    {id = 2, value = 16, name = "x16"},
    {id = 3, value = 24, name = "x24"},
    {id = 4, value = 32, name = "x32"},
    {id = 5, value = 40, name = "x40"},
    {id = 6, value = 48, name = "x48"},
    {id = 7, value = 56, name = "x56"},
    {id = 8, value = 64, name = "x64"}
  }
)

function trigger_edit_page_ui_controller.change_page(subpage_name)
  -- pages:select_page(subpage_name)
end

local grid_viewer_page =
  page:new(
  "",
  function()
    grid_viewer:draw()
  end
)

local trig_edit_options_page =
  page:new(
  "Trig editor options",
  function()
    tresillo_mult:draw()
  end
)

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
  tresillo_mult:select()
  trigger_edit_page_ui_controller.refresh_tresillo()
  trigger_edit_page_ui_controller.register_ui_draw_handlers()
end

function trigger_edit_page_ui_controller.enc(n, d)
  if n == 2 then
    for i = 1, math.abs(d) do
      if d > 0 then
        grid_viewer:next_channel()
      else
        grid_viewer:prev_channel()
      end
    end
  end

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

  if n == 3 then
    for i = 1, math.abs(d) do
      if d > 0 then
        if pages:get_selected_page() == 2 then
          tresillo_mult:increment()
          trigger_edit_page_ui_controller.update_tresillo()
        end
      else
        if pages:get_selected_page() == 2 then
          tresillo_mult:decrement()
          trigger_edit_page_ui_controller.update_tresillo()
        end
      end
    end
  end
end

function trigger_edit_page_ui_controller.update_tresillo()
  params:set("tresillo_amount", tresillo_mult:get_selected().id)
end

function trigger_edit_page_ui_controller.refresh_tresillo()
  tresillo_mult:set_selected_value(params:get("tresillo_amount"))
end

function trigger_edit_page_ui_controller:refresh()
  trigger_edit_page_ui_controller.refresh_tresillo()
end

return trigger_edit_page_ui_controller
