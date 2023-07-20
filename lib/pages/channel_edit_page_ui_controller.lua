local channel_edit_page_ui = {}

local Pages = include("sinfcommand/lib/ui_components/Pages")
local Page = include("sinfcommand/lib/ui_components/Page")

local pages = Pages:new()

local function quantizer_page_draw_func()
  screen.move(0,30)
  screen.text("quantizer_page")

end

function channel_edit_page_ui:change_page(subpage_name)
  pages:select_page(subpage_name)
end

function channel_edit_page_ui:register_ui_draw_handlers() 


  local quantizer_page = Page:new("quantizer_page", quantizer_page_draw_func)
  local test_page = Page:new("test_page", test_page_draw_func)

  pages:add_page(quantizer_page)
  pages:select_page("quantizer_page")

  draw_handler:register_ui(
    "channel_edit_page",
    function()
      pages:draw()
    end
  )
end


return channel_edit_page_ui