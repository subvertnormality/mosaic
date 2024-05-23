-- channel_edit_page_ui_helpers.lua
local channel_edit_page_ui_helpers = {}
local param_manager = include("mosaic/lib/param_manager")

-- Abstracting common increment/decrement logic for trig locks
function channel_edit_page_ui_helpers.handle_trig_locks_page_change(direction, trig_lock_page, param_select_vertical_scroll_selector, dials)
  if trig_lock_page:is_sub_page_enabled() then
    param_select_vertical_scroll_selector:scroll(direction)
    save_confirm.set_save(function()
      param_manager.update_param(
        dials:get_selected_index(),
        program.get_selected_channel(),
        param_select_vertical_scroll_selector:get_selected_item(),
        param_select_vertical_scroll_selector:get_meta_item()
      )
      channel_edit_page_ui_controller.refresh_trig_locks()
    end)
    save_confirm.set_cancel(function() end)
  else
    channel_edit_page_ui_controller.handle_trig_lock_param_change_by_direction(direction, program.get_selected_channel(), dials:get_selected_index())
  end
end

return channel_edit_page_ui_helpers
