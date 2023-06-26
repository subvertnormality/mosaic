velocity_edit_page_controller = {}

local VerticalFader = include("sinfcommand/lib/controls/VerticalFader")

function velocity_edit_page_controller:init()

  velocity_edit_page_step1_fader = VerticalFader:new(1, 1, 7)
  velocity_edit_page_step2_fader = VerticalFader:new(2, 1, 7)
  velocity_edit_page_step3_fader = VerticalFader:new(3, 1, 7)
  velocity_edit_page_step4_fader = VerticalFader:new(4, 1, 7)
  velocity_edit_page_step5_fader = VerticalFader:new(5, 1, 7)
  velocity_edit_page_step6_fader = VerticalFader:new(6, 1, 7)
  velocity_edit_page_step7_fader = VerticalFader:new(7, 1, 7)
  velocity_edit_page_step8_fader = VerticalFader:new(8, 1, 7)

end

function velocity_edit_page_controller:register_draw_handlers()
  draw_handler:register(
  "pattern_velocity_edit_page",
  function()
    return velocity_edit_page_step1_fader:draw()
  end
  )
  draw_handler:register(
  "pattern_velocity_edit_page",
  function()
    return velocity_edit_page_step2_fader:draw()
  end
  ) 
  draw_handler:register(
  "pattern_velocity_edit_page",
  function()
    return velocity_edit_page_step3_fader:draw()
  end
  )
  draw_handler:register(
  "pattern_velocity_edit_page",
  function()
    return velocity_edit_page_step4_fader:draw()
  end
  )
  draw_handler:register(
  "pattern_velocity_edit_page",
  function()
    return velocity_edit_page_step5_fader:draw()
  end
  )
  draw_handler:register(
  "pattern_velocity_edit_page",
  function()
    return velocity_edit_page_step6_fader:draw()
  end
  )
  draw_handler:register(
  "pattern_velocity_edit_page",
  function()
    return velocity_edit_page_step7_fader:draw()
  end
  )
  draw_handler:register(
  "pattern_velocity_edit_page",
  function()
    return velocity_edit_page_step8_fader:draw()
  end
  )
end

function velocity_edit_page_controller:register_press_handlers()
  -- press_handler:register(
  -- pattern_velocity_edit_page,
  -- function(x, y)
  --   local result = pattern_trigger_edit_page_pattern_select_fader:press(x, y)
  --   program.selected_pattern = pattern_trigger_edit_page_pattern_select_fader:get_value()
  --   return result
  -- end
  -- )
end

return velocity_edit_page_controller
