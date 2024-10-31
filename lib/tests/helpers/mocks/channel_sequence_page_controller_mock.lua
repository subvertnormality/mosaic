song_edit_page_controller = {}

song_edit_page_controller.refresh = function()
  table.insert(song_edit_page_controller_refresh_events, true)
end