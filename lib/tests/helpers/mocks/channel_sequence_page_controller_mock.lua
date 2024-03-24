channel_sequencer_page_controller = {}

channel_sequencer_page_controller.refresh = function()
  table.insert(channel_sequencer_page_controller_refresh_events, true)
end