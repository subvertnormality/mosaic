local channel_edit_page_ui = {}

local quantiser = include("sinfcommand/lib/quantiser")
local Pages = include("sinfcommand/lib/ui_components/Pages")
local Page = include("sinfcommand/lib/ui_components/Page")
local VerticalScrollSelector = include("sinfcommand/lib/ui_components/VerticalScrollSelector")

local pages = Pages:new()

local quantizer_vertical_scroll_selector = VerticalScrollSelector:new(30, 20, "Quantizer", quantiser.get_scales())
local romans_vertical_scroll_selector = VerticalScrollSelector:new(105, 20, "Roman Analysis", quantiser.get_scales()[1].romans)
local notes_vertical_scroll_selector = VerticalScrollSelector:new(10, 20, "Notes", quantiser.get_notes())

local function quantizer_page_draw_func()
  quantizer_vertical_scroll_selector:draw()
  romans_vertical_scroll_selector:draw()
  notes_vertical_scroll_selector:draw()
end

function channel_edit_page_ui:change_page(subpage_name)
  pages:select_page(subpage_name)
end

function channel_edit_page_ui:register_ui_draw_handlers() 


  local quantizer_page = Page:new("quantizer_page", quantizer_page_draw_func)

  pages:add_page(quantizer_page)
  pages:select_page("quantizer_page")

  draw_handler:register_ui(
    "channel_edit_page",
    function()
      pages:draw()
    end
  )
end

function channel_edit_page_ui:select_quantizer_item(selected_item)
  quantizer_vertical_scroll_selector:set_selected_item(selected_item)
end

function channel_edit_page_ui:refresh_roman_item()
  romans_vertical_scroll_selector:set_items(quantizer_vertical_scroll_selector:get_selected_item().romans)
end

return channel_edit_page_ui