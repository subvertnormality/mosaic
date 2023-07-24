local channel_edit_page_ui = {}

local midi_device_map = include("sinfcommand/lib/midi_device_map")

local quantiser = include("sinfcommand/lib/quantiser")
local Pages = include("sinfcommand/lib/ui_components/Pages")
local Page = include("sinfcommand/lib/ui_components/Page")
local VerticalScrollSelector = include("sinfcommand/lib/ui_components/VerticalScrollSelector")
local Dial = include("sinfcommand/lib/ui_components/Dial")
local ControlScrollSelector = include("sinfcommand/lib/ui_components/ControlScrollSelector")

local midi_controller = include("sinfcommand/lib/midi_controller")

local pages = Pages:new()

local quantizer_vertical_scroll_selector = VerticalScrollSelector:new(30, 25, "Quantizer", quantiser.get_scales())
local romans_vertical_scroll_selector = VerticalScrollSelector:new(105, 25, "Roman Analysis", quantiser.get_scales()[1].romans)
local notes_vertical_scroll_selector = VerticalScrollSelector:new(10, 25, "Notes", quantiser.get_notes())

local midi_device_vertical_scroll_selector = VerticalScrollSelector:new(10, 25, "Midi Device", {})
local midi_channel_vertical_scroll_selector = VerticalScrollSelector:new(45, 25, "Midi Channel", {{name = "CC1", value = 1}, {name = "CC2", value = 2}, {name = "CC3", value = 3}, {name = "CC4", value = 4}, {name = "CC5", value = 5}, {name = "CC6", value = 6}, {name = "CC7", value = 7}, {name = "CC8", value = 8}, {name = "CC9", value = 9}, {name = "CC10", value = 10}, {name = "CC11", value = 11}, {name = "CC12", value = 12}, {name = "CC13", value = 13}, {name = "CC14", value = 14}, {name = "CC15", value = 15}, {name = "CC16", value = 16}})
local midi_device_map_vertical_scroll_selector = VerticalScrollSelector:new(70, 25, "Midi Map", midi_device_map:get_midi_device_map())

local param_1 = Dial:new(5, 20, "Param 1", "XXXX", "XXXX")
local param_2 = Dial:new(25, 20, "Param 2", "XXXX", "XXXX")
local param_3 = Dial:new(45, 20, "Param 3", "XXXX", "XXXX")
local param_4 = Dial:new(65, 20, "Param 4", "XXXX", "XXXX")
local param_5 = Dial:new(5, 40, "Param 5", "XXXX", "XXXX")
local param_6 = Dial:new(25, 40, "Param 6", "XXXX", "XXXX")
local param_7 = Dial:new(45, 40, "Param 7", "XXXX", "XXXX")
local param_8 = Dial:new(65, 40, "Param 8", "XXXX", "XXXX")

local dials = ControlScrollSelector:new(0, 0, {})

local quantizer_page = Page:new("", function ()
  quantizer_vertical_scroll_selector:draw()
  romans_vertical_scroll_selector:draw()
  notes_vertical_scroll_selector:draw()
end)

local channel_edit_page = Page:new("Config", function ()
  midi_device_vertical_scroll_selector:draw()
  midi_channel_vertical_scroll_selector:draw()
  midi_device_map_vertical_scroll_selector:draw()
end)

local trig_lock_page = Page:new("Trig Locks", function ()
  dials:draw()
end)

function channel_edit_page_ui:change_page(page)
  pages:select_page(page)

end

function channel_edit_page_ui:register_ui_draw_handlers() 
  
  draw_handler:register_ui(
    "channel_edit_page",
    function()
      pages:draw()
    end
  )

end

function channel_edit_page_ui:init()
  quantizer_vertical_scroll_selector:select()
  midi_channel_vertical_scroll_selector:select()
  midi_device_vertical_scroll_selector:set_items(midi_controller:get_midi_outs())
  dials:set_items({param_1, param_2, param_3, param_4, param_5, param_6, param_7, param_8})

  quantizer_page:set_sub_name_func(function ()
    return "Quantizer " .. program.sequencer_patterns[program.selected_sequencer_pattern].channels[program.selected_channel].default_scale .. " "
  end)

  channel_edit_page:set_sub_name_func(function ()
    return "Ch. " .. program.selected_channel .. " "
  end)

  trig_lock_page:set_sub_name_func(function ()
    return "Ch. " .. program.selected_channel .. " "
  end)

  pages:add_page(quantizer_page)
  pages:add_page(channel_edit_page)
  pages:add_page(trig_lock_page)
  dials:select(1)
  pages:select_page(1)

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

function channel_edit_page_ui:select_midi_device_item(selected_item)
  midi_device_vertical_scroll_selector:set_selected_item(selected_item)
end

function channel_edit_page_ui:select_midi_channel_item(selected_item)
  midi_channel_vertical_scroll_selector:set_selected_item(selected_item)
end

function channel_edit_page_ui:select_midi_device_map_item(selected_item)
  midi_device_map_vertical_scroll_selector:set_selected_item(selected_item)
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

function channel_edit_page_ui:update_channel_config()
  local channel = program.sequencer_patterns[program.selected_sequencer_pattern].channels[program.selected_channel]
  local midi_device = midi_device_vertical_scroll_selector:get_selected_item()
  local midi_channel = midi_channel_vertical_scroll_selector:get_selected_item()
  local midi_device_map = midi_device_map_vertical_scroll_selector:get_selected_item()

  channel.midi_device = midi_device.value
  channel.midi_channel = midi_channel.value
  channel.midi_device_map = midi_device_map.value
end

function channel_edit_page_ui:enc(n, d)
  if n == 3 then
    for i=1, math.abs(d) do
      if d > 0 then
        if pages:get_selected_page() == 1 then
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
        elseif pages:get_selected_page() == 2 then
          if midi_device_vertical_scroll_selector:is_selected() then
            midi_device_vertical_scroll_selector:scroll_down()
          end
          if midi_channel_vertical_scroll_selector:is_selected() then
            midi_channel_vertical_scroll_selector:scroll_down()
          end
          if midi_device_map_vertical_scroll_selector:is_selected() then
            midi_device_map_vertical_scroll_selector:scroll_down()
          end
          channel_edit_page_ui:update_channel_config()
        elseif pages:get_selected_page() == 3 then
          dials:scroll_next()
        end
      else
        if pages:get_selected_page() == 1 then
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
        elseif pages:get_selected_page() == 2 then
          if midi_device_vertical_scroll_selector:is_selected() then
            midi_device_vertical_scroll_selector:scroll_up()
          end
          if midi_channel_vertical_scroll_selector:is_selected() then
            midi_channel_vertical_scroll_selector:scroll_up()
          end
          if midi_device_map_vertical_scroll_selector:is_selected() then
            midi_device_map_vertical_scroll_selector:scroll_up()
          end
          channel_edit_page_ui:update_channel_config()
        elseif pages:get_selected_page() == 3 then
          dials:scroll_previous()
        end
      end
    end
  end

  if n == 2 then
    for i=1, math.abs(d) do
      if d > 0 then

        if pages:get_selected_page() == 1 then
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
        elseif pages:get_selected_page() == 2 then
          if midi_device_vertical_scroll_selector:is_selected() then
            midi_device_vertical_scroll_selector:deselect()
            midi_channel_vertical_scroll_selector:select()
          elseif midi_channel_vertical_scroll_selector:is_selected() then
            midi_channel_vertical_scroll_selector:deselect()
            midi_device_map_vertical_scroll_selector:select()
          elseif midi_device_map_vertical_scroll_selector:is_selected() then
            midi_device_map_vertical_scroll_selector:deselect()
            midi_device_vertical_scroll_selector:select()
          end
        end
      else
        if pages:get_selected_page() == 1 then
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
        elseif pages:get_selected_page() == 2 then
          if midi_device_vertical_scroll_selector:is_selected() then
            midi_device_vertical_scroll_selector:deselect()
            midi_device_map_vertical_scroll_selector:select()
          elseif midi_channel_vertical_scroll_selector:is_selected() then
            midi_channel_vertical_scroll_selector:deselect()
            midi_device_vertical_scroll_selector:select()
          elseif midi_device_map_vertical_scroll_selector:is_selected() then
            midi_device_map_vertical_scroll_selector:deselect()
            midi_channel_vertical_scroll_selector:select()
          end
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