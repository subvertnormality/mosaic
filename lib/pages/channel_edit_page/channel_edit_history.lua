local channel_edit_history = {}

function channel_edit_history.new(memory_history_navigator, public_ui)
  local history = {}
  local memory_state = {
    events = {}
  }

  history.navigator = memory_history_navigator:new(
    0 + (1 - 1) % 5 * 25,
    18 + math.floor((3 - 1) / 5) * 22,
    "History"
  )

  local function refresh_selected_channel(channel)
    memory_state.events = memory.get_recent_events(channel, 25)
    history.navigator:set_max_index(memory.get_total_event_count(channel))
    history.navigator:set_current_index(memory.get_event_count(channel))
  end

  function history.draw()
    history.navigator:draw()
  end

  function history.initialize()
    history.navigator:set_event_state(memory_state)
    local selected_channel = program.get().selected_channel
    history.navigator:set_max_index(memory.get_total_event_count(selected_channel))
    history.navigator:set_current_index(memory.get_event_count(selected_channel))
    history.navigator:select()
  end

  function history.refresh()
    refresh_selected_channel(program.get_selected_channel().number)
  end

  function history.navigate(channel, direction)
    if direction > 0 then
      memory.redo(channel)
    else
      memory.undo(channel)
    end
    if program.get_selected_channel().number == channel then
      refresh_selected_channel(channel)
    end
    pattern.update_working_pattern(channel, program.get_selected_song_pattern())
  end

  function history.handle_page_change(direction)
    if history.navigator:is_selected() then
      public_ui.handle_memory_navigator(program.get_selected_channel().number, direction)
    end
  end

  return history
end

return channel_edit_history
