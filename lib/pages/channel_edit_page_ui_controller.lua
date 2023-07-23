local channel_edit_page_ui = {}

local quantiser = include("sinfcommand/lib/quantiser")
local Pages = include("sinfcommand/lib/ui_components/Pages")
local Page = include("sinfcommand/lib/ui_components/Page")
local VerticalScrollSelector = include("sinfcommand/lib/ui_components/VerticalScrollSelector")

local pages = Pages:new()

local quantizer_vertical_scroll_selector = VerticalScrollSelector:new(30, 20, "Quantizer", quantiser.get_scales())
local romans_vertical_scroll_selector = VerticalScrollSelector:new(105, 20, "Roman Analysis", quantiser.get_scales()[1].romans)
local notes_vertical_scroll_selector = VerticalScrollSelector:new(10, 20, "Notes", quantiser.get_notes())

local quantizer_page = Page:new("quantizer_page", function ()
  quantizer_vertical_scroll_selector:draw()
  romans_vertical_scroll_selector:draw()
  notes_vertical_scroll_selector:draw()
end)

local channel_edit_page = Page:new("channel_edit_page", function ()
  print("drawing channel edit page")
end)


function channel_edit_page_ui:change_page(subpage_name)
  pages:select_page(subpage_name)
end

function channel_edit_page_ui:register_ui_draw_handlers() 
  

  pages:add_page(quantizer_page)
  pages:add_page(channel_edit_page)
  pages:select_page(1)

  draw_handler:register_ui(
    "channel_edit_page",
    function()
      pages:draw()
    end
  )

end

function channel_edit_page_ui:init()
  quantizer_vertical_scroll_selector:select()
end

function channel_edit_page_ui:select_quantizer_item(selected_item)
  quantizer_vertical_scroll_selector:set_selected_item(selected_item)
end

function channel_edit_page_ui:select_roman_item(selected_item)
  romans_vertical_scroll_selector:set_selected_item(selected_item)
end

function channel_edit_page_ui:select_note_item(selected_item)
  notes_vertical_scroll_selector:set_selected_item(selected_item)
end

function channel_edit_page_ui:update_scale()
  local channel = program.sequencer_patterns[program.selected_sequencer_pattern].channels[program.selected_channel]
  local scale = quantizer_vertical_scroll_selector:get_selected_item()
  local chord = romans_vertical_scroll_selector:get_selected_index()
  local root_note = notes_vertical_scroll_selector:get_selected_index() - 1

  program.scales[channel.default_scale] = {
    number = scale.number,
    scale = scale.scale,
    chord = chord,
    root_note = root_note
  }
end


function channel_edit_page_ui:enc(n, d)
  if n == 3 then
    for i=1, math.abs(d) do
      if d > 0 then
        if quantizer_vertical_scroll_selector:is_selected() then
          quantizer_vertical_scroll_selector:scroll_down()
        end
        if romans_vertical_scroll_selector:is_selected() then
          romans_vertical_scroll_selector:scroll_down()
        end
        if notes_vertical_scroll_selector:is_selected() then
          notes_vertical_scroll_selector:scroll_down()
        end
        channel_edit_page_ui:update_scale()
      else
        if quantizer_vertical_scroll_selector:is_selected() then
          quantizer_vertical_scroll_selector:scroll_up()
        end
        if romans_vertical_scroll_selector:is_selected() then
          romans_vertical_scroll_selector:scroll_up()
        end
        if notes_vertical_scroll_selector:is_selected() then
          notes_vertical_scroll_selector:scroll_up()
        end
        channel_edit_page_ui:update_scale()
      end
    end
  end

  if n == 2 then
    for i=1, math.abs(d) do
      if d > 0 then
        if quantizer_vertical_scroll_selector:is_selected() then
          quantizer_vertical_scroll_selector:deselect()
          romans_vertical_scroll_selector:select()
        elseif romans_vertical_scroll_selector:is_selected() then
          romans_vertical_scroll_selector:deselect()
          notes_vertical_scroll_selector:select()
        elseif notes_vertical_scroll_selector:is_selected() then
          notes_vertical_scroll_selector:deselect()
          quantizer_vertical_scroll_selector:select()
        end
      else
        if quantizer_vertical_scroll_selector:is_selected() then
          quantizer_vertical_scroll_selector:deselect()
          notes_vertical_scroll_selector:select()
        elseif romans_vertical_scroll_selector:is_selected() then
          romans_vertical_scroll_selector:deselect()
          quantizer_vertical_scroll_selector:select()
        elseif notes_vertical_scroll_selector:is_selected() then
          notes_vertical_scroll_selector:deselect()
          romans_vertical_scroll_selector:select()
        end
      end
    end
  end

  if n == 1 then 
    for i=1, math.abs(d) do
      if d > 0 then
        pages:next_page()
        fn.dirty_screen(true)

      else
        pages:previous_page()
        fn.dirty_screen(true)
      end
    end
  end

end

return channel_edit_page_ui