local trigger_edit_page_ui_controller = {}

local Pages = include("sinfcommand/lib/ui_components/Pages")
local Page = include("sinfcommand/lib/ui_components/Page")

local pages = Pages:new()


function trigger_edit_page_ui_controller.change_page(subpage_name)
  -- pages:select_page(subpage_name)
end



function trigger_edit_page_ui_controller.register_ui_draw_handlers() 
  draw_handler:register_ui(
    "pattern_trigger_edit_page",
    function()

    end
  )
end

function trigger_edit_page_ui_controller.init()
  trigger_edit_page_ui_controller.register_ui_draw_handlers()
end

function trigger_edit_page_ui_controller.enc(n, d)

end

return trigger_edit_page_ui_controller