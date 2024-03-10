globals = {}


globals.reset = function() 

  midi_note_on_events = {}
  midi_note_off_events = {}
  midi_cc_events = {}
  channel_sequencer_page_controller_refresh_events = {}
  channel_edit_page_controller_refresh_events = {}
  channel_edit_page_controller_refresh_trig_locks_events = {}
  has_fired = nil
end

globals.reset()