song_edit_page = {}

song_edit_page.refresh = function()
  table.insert(song_edit_page_refresh_events, true)
end