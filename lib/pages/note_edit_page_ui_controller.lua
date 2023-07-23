local note_edit_page_ui = {}

local Pages = include("sinfcommand/lib/ui_components/Pages")
local Page = include("sinfcommand/lib/ui_components/Page")

local pages = Pages:new()

function note_edit_page_ui:change_page(subpage_name)
  pages:select_page(subpage_name)
end


function note_edit_page_ui:register_ui_draw_handlers() 
  draw_handler:register_ui(
    "pattern_note_edit_page",
    function()

    end
  )
end


function note_edit_page_ui:enc(n, d)

end

return note_edit_page_ui