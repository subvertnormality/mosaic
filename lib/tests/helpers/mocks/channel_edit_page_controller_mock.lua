channel_edit_page_controller = {}

channel_edit_page_controller.refresh = function()
  table.insert(channel_edit_page_controller_refresh_events, true)
end