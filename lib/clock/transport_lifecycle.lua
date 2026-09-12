-- Application transport state and start/stop/reset ordering.
-- Native F8 scheduling remains owned by midi_output_transport.
local transport_lifecycle = {}

function transport_lifecycle.new(deps)
  local lifecycle = {}
  local playing = false
  local cancel_midi_output_transport
  local warned_midi_boundary = false
  function lifecycle.start(self, from_external_transport)
    if playing and not from_external_transport and
        (deps.get_lattice().enabled or cancel_midi_output_transport) then return end
    -- MIDI Start resets position even when playback is already active.
    -- Reuse cleanup so held voices and pending releases cannot cross epochs.
    if playing and from_external_transport then self:stop(false) end
    if not playing then
      -- Stopped edits can consume fractional preview carry in different orders.
      -- Build both processors from the final settings before the first onset.
      -- Preserve step state and leave already-playing clocks untouched.
      if deps.get_lattice() then deps.get_lattice():destroy() end
      self.init()
    end
    deps.reset_first_run()
    if params:get("elektron_program_changes") == 2 then
      step.process_elektron_program_change(deps.program.get().selected_song_pattern)
    end

    deps.midi_patch_recall.send()
    deps.get_clock().set_playing()
    -- Only incoming transport Start defines external beat zero. Local Play
    -- against an already-running MIDI clock retains its own starting phase.
    deps.get_lattice().sync_to_external = from_external_transport == true
    deps.get_lattice().external_clock_active = function() return params:get("clock_source") == 2 end
    local sends_clock = false
    for port = 1,16 do
      if params:get("clock_midi_out_" .. port) == 1 then sends_clock = true end
    end
    if sends_clock and deps.midi_output_transport.available() then
      -- Incoming Start establishes source beat zero. Supplying it prevents a late
      -- first output callback from silently rebasing the forwarded phrase.
      local source_origin = from_external_transport and 0 or nil
      cancel_midi_output_transport = deps.midi_output_transport.start(deps.get_lattice(), m_midi.start, function() deps.get_clock():stop() end, source_origin)
    else
      if sends_clock and not warned_midi_boundary then
        print("Mosaic: native MIDI output boundary unavailable; master phase alignment is not guaranteed")
        warned_midi_boundary = true
      end
      m_midi.start()
      deps.get_lattice():start()
    end

  end

  function lifecycle.stop(self, send_transport)
    if cancel_midi_output_transport then
      cancel_midi_output_transport()
      cancel_midi_output_transport = nil
    end

    playing = false
    deps.reset_first_run()

    deps.drain_releases()

    nb:stop_all()
    m_midi.stop(send_transport)

    if deps.get_lattice() and deps.get_lattice().stop then
      deps.get_lattice():stop()
    end

    deps.get_clock().reset()

    collectgarbage("collect")
  end

  function lifecycle.is_playing()
    return playing
  end

  function lifecycle.set_playing()
    playing = true
  end

  function lifecycle.reset()
    -- Stop clears the native subscription before re-entering reset/init, so the
    -- old callbacks cannot retain a replaced lattice or its held voices.
    if cancel_midi_output_transport then deps.get_clock():stop(); return end
    local program_data = deps.program.get()
    for _, pattern in ipairs(program_data.song_patterns) do
      for i = 1, 17 do
        deps.program.set_current_step_for_channel(i, 1)
      end
    end

    program_data.current_step = 1
    step.reset()

    if deps.get_lattice() and deps.get_lattice().destroy then
      deps.get_lattice():destroy()
      deps.set_lattice(nil)
    end

    deps.get_clock().init()
  end


  function lifecycle.stop_if_subscribed()
    if not cancel_midi_output_transport then return false end
    deps.get_clock():stop()
    return true
  end
  return lifecycle
end

return transport_lifecycle
