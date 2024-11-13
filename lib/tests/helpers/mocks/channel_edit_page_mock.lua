channel_edit_page = {}

channel_edit_page.refresh = function()
  table.insert(channel_edit_page_refresh_events, true)
end