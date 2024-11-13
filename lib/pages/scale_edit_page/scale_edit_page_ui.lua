local scale_edit_page_ui = {}

local quantiser = include("mosaic/lib/quantiser")
local pages = include("mosaic/lib/ui_components/pages")
local page = include("mosaic/lib/ui_components/page")
local vertical_scroll_selector = include("mosaic/lib/ui_components/vertical_scroll_selector")
local list_selector = include("mosaic/lib/ui_components/list_selector")

local gv = include("mosaic/lib/ui_components/grid_viewer")

local grid_viewer = gv:new(0, 3)
local scales_pages = pages:new()
local quantizer_vertical_scroll_selector = vertical_scroll_selector:new(13, 25, "Quantizer", quantiser.get_scales())
local romans_vertical_scroll_selector = vertical_scroll_selector:new(80, 25, "Roman Analysis", quantiser.get_scales()[1].romans)
local notes_vertical_scroll_selector = vertical_scroll_selector:new(0, 25, "Notes", quantiser.get_notes())
local transpose_vertical_scroll_selector = vertical_scroll_selector:new(103, 25, "Transpose", {"-12", "-11", "-10", "-9", "-8", "-7", "-6", "-5", "-4", "-3", "-2", "-1", "0", "+1", "+2", "+3", "+4", "+5", "+6", "+7", "+8", "+9", "+10", "+11", "+12"})
local rotation_vertical_scroll_selector = vertical_scroll_selector:new(115, 25, "Rotation", {"r0", "r1", "r2", "r3", "r4", "r5", "r6"})

local scales_page_to_index = {["Quantizer"] = 1, ["Clock Mods"] = 2, ["Grid Viewer"] = 3}
local index_to_scales_page = {"Quantizer", "Clock Mods"}

local clock_mod_list_selector = list_selector:new(0, 18, "Clock Mod", {})

local throttle_time = 0.01

local scales_channel = 17

local quantizer_page = page:new("", function()
  quantizer_vertical_scroll_selector:draw()
  romans_vertical_scroll_selector:draw()
  notes_vertical_scroll_selector:draw()
  transpose_vertical_scroll_selector:draw()
  rotation_vertical_scroll_selector:draw()
end)

local clock_mods_page = page:new("Clocks", function()
  clock_mod_list_selector:draw()
end)

local grid_viewer_page = page:new("", function()
  grid_viewer:draw()
end)

function scale_edit_page_ui.register_ui_draws()
  draw:register_ui(
    "scale_edit_page",
    function()
      scales_pages:draw()
    end
  )

end

function scale_edit_page_ui.init()

  quantizer_vertical_scroll_selector:select()
  clock_mod_list_selector:set_list(m_clock.get_clock_divisions())

  quantizer_page:set_sub_name_func(function()
    return "Scale slot " .. program.get().selected_scale .. " "
  end)

  scales_pages:add_page(quantizer_page)
  scales_pages:add_page(clock_mods_page)
  scales_pages:add_page(grid_viewer_page)

  scales_pages:select_page(scales_page_to_index["Quantizer"])

  scale_edit_page_ui.refresh_clock_mods()

end

-- Update functions
function scale_edit_page_ui.update_scale()
  local scale = quantizer_vertical_scroll_selector:get_selected_item()
  local chord = romans_vertical_scroll_selector:get_selected_index()
  local root_note = notes_vertical_scroll_selector:get_selected_index() - 1
  local transpose = transpose_vertical_scroll_selector:get_selected_index() - 13
  local rotation = rotation_vertical_scroll_selector:get_selected_index() - 1

  save_confirm.set_cancel_message("Scale not saved.")
  save_confirm.set_cancel(scale_edit_page_ui.refresh_quantiser)

  if is_key3_down then
    save_confirm.set_confirm_message("K2 to save across song.")
    save_confirm.set_ok_message("Scale saved to all.")
    save_confirm.set_save(function()
      program.set_all_sequencer_pattern_scales(
        program.get().selected_scale,
        {number = scale.number, scale = scale.scale, pentatonic_scale = scale.pentatonic_scale, chord = chord, root_note = root_note, chord_degree_rotation = rotation, transpose = transpose}
      )
    end)
  else
    save_confirm.set_save(function()
      program.set_scale(
        program.get().selected_scale,
        {number = scale.number, scale = scale.scale, pentatonic_scale = scale.pentatonic_scale, chord = chord, root_note = root_note, chord_degree_rotation = rotation, transpose = transpose}
      )
    end)
  end
end

function scale_edit_page_ui.update_clock_mods()
  local channel = program.get_selected_channel()
  local clock_mods = clock_mod_list_selector:get_selected()
  channel.clock_mods = clock_mods

  if m_clock.is_playing() then
    step.queue_for_pattern_change(function() 
      local c = channel.number 
      local div = m_clock.calculate_divisor(clock_mods)
      m_clock.set_channel_division(c, div) 
    end)
  else
    m_clock.set_channel_division(channel.number, m_clock.calculate_divisor(clock_mods))
  end
  
end

function scale_edit_page_ui.enc(n, d)
  local channel = program.get_channel(program.get().selected_sequencer_pattern, scales_channel)
  if n == 3 then
    for _ = 1, math.abs(d) do
      if d > 0 then
        if scales_pages:get_selected_page() == scales_page_to_index["Quantizer"] then
          scale_edit_page_ui.handle_quantizer_page_increment()
        elseif scales_pages:get_selected_page() == scales_page_to_index["Clock Mods"] then
          scale_edit_page_ui.handle_scales_clock_mods_page_increment()
        end
      else
        if scales_pages:get_selected_page() == scales_page_to_index["Quantizer"] then
          scale_edit_page_ui.handle_quantizer_page_decrement()
        elseif scales_pages:get_selected_page() == scales_page_to_index["Clock Mods"] then
          scale_edit_page_ui.handle_scales_clock_mods_page_decrement()
        end
      end
    end
  elseif n == 2 then
    for i = 1, math.abs(d) do
      if d > 0 then
        scale_edit_page_ui.handle_encoder_two_positive()
      else
        scale_edit_page_ui.handle_encoder_two_negative()
      end
    end
  elseif n == 1 then
    for _ = 1, math.abs(d) do
      if d > 0 then
        scale_edit_page_ui.handle_encoder_one_positive()
      else
        scale_edit_page_ui.handle_encoder_one_negative()
      end
    end
  end
end


function scale_edit_page_ui.key(n, z)
  if n == 2 and z == 1 then
    scale_edit_page_ui.handle_key_two_pressed()
  elseif n == 3 and z == 1 then
    scale_edit_page_ui.handle_key_three_pressed()
  end
end

scale_edit_page_ui.refresh_clock_mods = scheduler.debounce(function()
  local channel = program.get_channel(program.get().selected_sequencer_pattern, scales_channel)
  local clock_mods = channel.clock_mods
  local divisions = fn.filter_by_type(m_clock.get_clock_divisions(), clock_mods.type)
  local i = fn.find_index_in_table_by_value(divisions, clock_mods.value)
  if clock_mods.type == "clock_division" then
    i = i + 12
  end
  clock_mod_list_selector:set_selected_value(i)
  clock_mod_list_selector:select()
end, throttle_time)


scale_edit_page_ui.refresh_romans = scheduler.debounce(function()
  local scale = quantizer_vertical_scroll_selector:get_selected_item()
  if scale then
    local number = scale.number
    program.get_selected_sequencer_pattern().active = true
    romans_vertical_scroll_selector:set_items(quantiser.get_scales()[number].romans)
    fn.dirty_screen(true)
  end
end, throttle_time)

scale_edit_page_ui.refresh_quantiser = scheduler.debounce(function()
  local channel = program.get_channel(program.get().selected_sequencer_pattern, scales_channel)
  local scale = program.get_scale(program.get().selected_scale)
  program.get_selected_sequencer_pattern().active = true
  quantizer_vertical_scroll_selector:set_selected_item(scale.number)
  notes_vertical_scroll_selector:set_selected_item(scale.root_note + 1)
  romans_vertical_scroll_selector:set_selected_item(scale.chord)
  transpose_vertical_scroll_selector:set_selected_item((scale.transpose or 0) + 13)
  rotation_vertical_scroll_selector:set_selected_item((scale.chord_degree_rotation or 0) + 1)
  scale_edit_page_ui.refresh_romans(quantizer_vertical_scroll_selector, romans_vertical_scroll_selector, quantiser)
end, throttle_time)


function scale_edit_page_ui.refresh()
  scale_edit_page_ui.select_scale_page_by_index(scales_pages:get_selected_page() or 1)
end

function scale_edit_page_ui.handle_quantizer_page_increment()
  if quantizer_vertical_scroll_selector:is_selected() then
    quantizer_vertical_scroll_selector:scroll_down()
    scale_edit_page_ui.refresh_romans()
  elseif romans_vertical_scroll_selector:is_selected() then
    romans_vertical_scroll_selector:scroll_down()
  elseif notes_vertical_scroll_selector:is_selected() then
    notes_vertical_scroll_selector:scroll_down()
  elseif transpose_vertical_scroll_selector:is_selected() then
    transpose_vertical_scroll_selector:scroll_down()
  elseif rotation_vertical_scroll_selector:is_selected() then
    rotation_vertical_scroll_selector:scroll_down()
  end
  scale_edit_page_ui.update_scale()
end

function scale_edit_page_ui.handle_quantizer_page_decrement()
  if quantizer_vertical_scroll_selector:is_selected() then
    quantizer_vertical_scroll_selector:scroll_up()
    scale_edit_page_ui.refresh_romans()
  elseif romans_vertical_scroll_selector:is_selected() then
    romans_vertical_scroll_selector:scroll_up()
  elseif notes_vertical_scroll_selector:is_selected() then
    notes_vertical_scroll_selector:scroll_up()
  elseif transpose_vertical_scroll_selector:is_selected() then
    transpose_vertical_scroll_selector:scroll_up()
  elseif rotation_vertical_scroll_selector:is_selected() then
    rotation_vertical_scroll_selector:scroll_up()
  end
  scale_edit_page_ui.update_scale()
end


function scale_edit_page_ui.handle_scales_clock_mods_page_increment()
  if clock_mod_list_selector:is_selected() then
    clock_mod_list_selector:decrement()
    save_confirm.set_save(scale_edit_page_ui.update_clock_mods)
    save_confirm.set_cancel(scale_edit_page_ui.refresh_clock_mods)
  end
end

function scale_edit_page_ui.handle_scales_clock_mods_page_decrement()
  if clock_mod_list_selector:is_selected() then
    clock_mod_list_selector:increment()
    save_confirm.set_save(function()
      scale_edit_page_ui.update_clock_mods()
    end)
    save_confirm.set_cancel(function()
      scale_edit_page_ui.refresh_clock_mods()
    end)
  end
end


function scale_edit_page_ui.handle_encoder_one_positive()
  scale_edit_page_ui.select_scale_page_by_index((scales_pages:get_selected_page() or 1) + 1)
  fn.dirty_screen(true)
  save_confirm.cancel()
end

function scale_edit_page_ui.handle_encoder_one_negative()
  scale_edit_page_ui.select_scale_page_by_index((scales_pages:get_selected_page() or 1) - 1)
  fn.dirty_screen(true)
  save_confirm.cancel()
end

function scale_edit_page_ui.handle_encoder_two_positive()

  if scales_pages:get_selected_page() == scales_page_to_index["Quantizer"] then
    if quantizer_vertical_scroll_selector:is_selected() then
      quantizer_vertical_scroll_selector:deselect()
      romans_vertical_scroll_selector:select()
    elseif romans_vertical_scroll_selector:is_selected() then
      romans_vertical_scroll_selector:deselect()
      transpose_vertical_scroll_selector:select()
    elseif transpose_vertical_scroll_selector:is_selected() then
      transpose_vertical_scroll_selector:deselect()
      rotation_vertical_scroll_selector:select()
    elseif notes_vertical_scroll_selector:is_selected() then
      notes_vertical_scroll_selector:deselect()
      quantizer_vertical_scroll_selector:select()
    end
  elseif scales_pages:get_selected_page() == scales_page_to_index["Clock Mods"] then
    clock_mod_list_selector:select()
  elseif scales_pages:get_selected_page() == scales_page_to_index["Grid Viewer"] then
    grid_viewer:next_channel()
  end
end

function scale_edit_page_ui.handle_encoder_two_negative(pages, selectors, dials, trig_lock_page)

  if scales_pages:get_selected_page() == scales_page_to_index["Quantizer"] then
    if quantizer_vertical_scroll_selector:is_selected() then
      quantizer_vertical_scroll_selector:deselect()
      notes_vertical_scroll_selector:select()
    elseif romans_vertical_scroll_selector:is_selected() then
      romans_vertical_scroll_selector:deselect()
      quantizer_vertical_scroll_selector:select()
    elseif transpose_vertical_scroll_selector:is_selected() then
      transpose_vertical_scroll_selector:deselect()
      romans_vertical_scroll_selector:select()
    elseif rotation_vertical_scroll_selector:is_selected() then
      rotation_vertical_scroll_selector:deselect()
      transpose_vertical_scroll_selector:select()
    end
  elseif scales_pages:get_selected_page() == scales_page_to_index["Clock Mods"] then
    clock_mod_list_selector:select()
  elseif scales_pages:get_selected_page() == scales_page_to_index["Grid Viewer"] then
    grid_viewer:prev_channel()
  end
end

function scale_edit_page_ui.handle_key_two_pressed()
  local pressed_keys = m_grid.get_pressed_keys()
  if #pressed_keys < 1 then
    save_confirm.cancel()
  elseif #pressed_keys > 0 then
    for _, keys in ipairs(pressed_keys) do
      local s = fn.calc_grid_count(keys[1], keys[2])
      program.clear_trig_locks_for_step(s)
      tooltip:show("Scale locks for step " .. s .. " cleared")
    end
  end
end


function scale_edit_page_ui.handle_key_three_pressed()
  local pressed_keys = m_grid.get_pressed_keys()
  if #pressed_keys < 1 then
    save_confirm.confirm()
  end
end

function scale_edit_page_ui.select_scales_quantizer_page()
  scale_edit_page_ui.refresh_quantiser()
  scale_edit_page_ui.refresh_romans()
  scales_pages:select_page(scales_page_to_index["Quantizer"])
end

function scale_edit_page_ui.select_scales_clock_mods_page()
  scale_edit_page_ui.refresh_clock_mods()
  scales_pages:select_page(scales_page_to_index["Clock Mods"])
end

function scale_edit_page_ui.select_grid_viewer_page()
  scales_pages:select_page(scales_page_to_index["Grid Viewer"])
end

function scale_edit_page_ui.select_scale_page_by_index(index)
  if index == 1 then
    scale_edit_page_ui.select_scales_quantizer_page()
  elseif index == 2 then
    scale_edit_page_ui.select_scales_clock_mods_page()
  elseif index == 3 then
    scale_edit_page_ui.select_grid_viewer_page()
  end
end

return scale_edit_page_ui
