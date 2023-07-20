local channel_edit_page_ui = {}


local function quantizer_page_draw_func()
  screen.move(0,30)
  screen.text("quantizer_page")

end

function channel_edit_page_ui:register_ui_draw_handlers() 

  local pages = Pages:new()
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


return channel_edit_page_ui