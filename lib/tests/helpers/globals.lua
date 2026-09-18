globals = {}


globals.reset = function() 

  midi_note_on_events = {}
  midi_note_off_events = {}
  midi_cc_events = {}
  -- One ordered log of MIDI sends with the pulse each left on, so a test can
  -- assert that a value left before the note it belongs to.
  midi_event_log = {}
  song_edit_page_refresh_events = {}
  channel_edit_page_refresh_events = {}
  channel_edit_page_refresh_trig_locks_events = {}
  has_fired = nil
  m_grid = {
    get_pressed_keys = function() return {} end
  }

  -- Lock lead state is shared through the m_clock table and the MIDI module, so
  -- a test that turns lookahead on would otherwise leave it on for every test
  -- that ran afterwards. Reset it here, where every test's setup already is.
  if type(m_clock) == "table" and type(m_clock.set_lock_lookahead) == "function" then
    m_clock.set_lock_lookahead(nil)
  end
  if type(step) == "table" and type(step.set_lock_lookahead) == "function" then
    step.set_lock_lookahead(nil)
  end
  if type(m_midi) == "table" then
    if type(m_midi.set_lock_contract) == "function" then
      m_midi.set_lock_contract("legacy-delay-v1")
    end
    if type(m_midi.set_lead_time) == "function" then m_midi.set_lead_time(0) end
  end
end

globals.reset()