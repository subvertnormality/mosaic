-- recorder: event portions, commit, per-channel isolation and the exact payloads handed to
-- memory.record_event. memory, m_grid and the "record" param are replaced per test through
-- with_recorder_globals, which restores them even when an assertion fails.

local function with_recorder_globals(pressed_keys, record_mode, body)
  local calls = {}
  local target_calls = {}
  local saved_memory, saved_grid = memory, m_grid
  local saved_record = params:get("record")
  memory = {
    record_event = function(c, event_type, data)
      calls[#calls + 1] = {c, event_type, data}
    end,
    record_event_for_target = function(song_pattern, c, event_type, data)
      target_calls[#target_calls + 1] = {song_pattern, c, event_type, data}
    end
  }
  m_grid = {get_pressed_keys = function() return pressed_keys end}
  params:set("record", record_mode)
  local ok, err = pcall(body, calls, target_calls)
  memory, m_grid = saved_memory, saved_grid
  params:set("record", saved_record)
  if not ok then error(err, 0) end
end

local function fresh(song_pattern, channel)
  program.init()
  program.get().selected_song_pattern = song_pattern
  program.get().selected_channel = channel
  return include("mosaic/lib/recorder")
end

local function root_portion(song_pattern, step, note, velocity)
  return {
    song_pattern = song_pattern,
    data = {song_pattern = song_pattern, trig = 1, note = note, velocity = velocity,
      length = 1, chord_degrees = {}, step = step}
  }
end

function test_recorder_extra_held_step_root_note_stores_full_trig_portion()
  -- README 193: holding a step and pressing a key inputs note and velocity for that step.
  local recorder = fresh(3, 2)
  with_recorder_globals({{5, 4}}, 1, function(calls)
    recorder.handle_note_midi_message(61, 90, 1, 4)
    luaunit.assert_equals(recorder.mask_events, {[2] = {[5] = root_portion(3, 5, 61, 90)}})
    luaunit.assert_equals(calls, {})
  end)
end

function test_recorder_extra_held_step_rows_four_to_seven_are_steps()
  -- characterisation: step = (row - 4) * 16 + column; rows 4 and 7 are the boundaries.
  local recorder = fresh(1, 1)
  with_recorder_globals({{16, 7}}, 1, function()
    recorder.handle_note_midi_message(40, 20, 1, nil)
    luaunit.assert_equals(recorder.mask_events, {[1] = {[64] = root_portion(1, 64, 40, 20)}})
  end)
  recorder = fresh(1, 1)
  with_recorder_globals({{1, 4}, {9, 6}}, 1, function()
    recorder.handle_note_midi_message(41, 21, 1, nil)
    luaunit.assert_equals(recorder.mask_events, {[1] = {[1] = root_portion(1, 1, 41, 21)}})
  end)
end

function test_recorder_extra_held_non_step_key_records_live_when_armed()
  -- Human decision 2026-09-11 (bugs.json record-with-non-step-key-held, was S32): with
  -- record armed, holding a grid key outside rows 4..7 (a page or menu key) records at the
  -- current step exactly as with no key held; disarmed, it records nothing.
  for _, row in ipairs({3, 8}) do
    local recorder = fresh(1, 1)
    program.set_current_step_for_channel(1, 6)
    with_recorder_globals({{2, row}}, 2, function(calls)
      recorder.handle_note_midi_message(60, 100, 1, nil)
      recorder.handle_note_midi_message(64, 100, 2, 2)
      local expected = root_portion(1, 6, 60, 100)
      expected.data.chord_degrees = {[1] = 2}
      luaunit.assert_equals(recorder.mask_events, {[1] = {[6] = expected}})
      luaunit.assert_equals(calls, {})
    end)
    recorder = fresh(1, 1)
    program.set_current_step_for_channel(1, 6)
    with_recorder_globals({{2, row}}, 1, function(calls)
      recorder.handle_note_midi_message(60, 100, 1, nil)
      luaunit.assert_equals(recorder.mask_events, {})
      luaunit.assert_equals(calls, {})
    end)
  end
end

function test_recorder_extra_held_step_chord_voice_stores_only_its_degree()
  -- characterisation: voice n stores its degree at chord_degrees[n - 1], no trig or note.
  local recorder = fresh(2, 4)
  with_recorder_globals({{3, 5}}, 1, function()
    recorder.handle_note_midi_message(67, 80, 3, -2)
    luaunit.assert_equals(recorder.mask_events, {[4] = {[19] = {
      song_pattern = 2, data = {song_pattern = 2, step = 19, chord_degrees = {[2] = -2}}
    }}})
    recorder.handle_note_midi_message(65, 80, 2, 0)
    luaunit.assert_equals(recorder.mask_events[4][19].data.chord_degrees, {[1] = 0, [2] = -2})
  end)
end

function test_recorder_extra_chord_voice_without_degree_is_dropped()
  -- characterisation: m_midi passes nil for a degree outside -14..14.
  local recorder = fresh(1, 1)
  with_recorder_globals({{3, 5}}, 1, function()
    recorder.handle_note_midi_message(67, 80, 2, nil)
    luaunit.assert_equals(recorder.mask_events, {})
  end)
  recorder = fresh(1, 1)
  program.set_current_step_for_channel(1, 2)
  with_recorder_globals({}, 2, function()
    recorder.handle_note_midi_message(67, 80, 2, nil)
    luaunit.assert_equals(recorder.mask_events, {})
  end)
end

function test_recorder_extra_live_record_uses_selected_channel_current_step()
  -- README 239: recordings are quantised to the step active for the selected channel.
  local recorder = fresh(5, 2)
  program.set_current_step_for_channel(1, 30)
  program.set_current_step_for_channel(2, 9)
  with_recorder_globals({}, 2, function(calls)
    recorder.handle_note_midi_message(72, 110, 1, 3)
    luaunit.assert_equals(recorder.mask_events, {[2] = {[9] = root_portion(5, 9, 72, 110)}})
    recorder.handle_note_midi_message(76, 110, 4, 5)
    luaunit.assert_equals(recorder.mask_events[2][9].data.chord_degrees, {[3] = 5})
    luaunit.assert_equals(recorder.mask_events[2][9].data.note, 72)
    luaunit.assert_equals(calls, {})
  end)
end

function test_recorder_extra_live_record_chord_voice_payload()
  local recorder = fresh(1, 3)
  program.set_current_step_for_channel(3, 12)
  with_recorder_globals({}, 2, function()
    recorder.handle_note_midi_message(64, 100, 2, -7)
    luaunit.assert_equals(recorder.mask_events, {[3] = {[12] = {
      song_pattern = 1, data = {song_pattern = 1, step = 12, chord_degrees = {[1] = -7}}
    }}})
  end)
end

function test_recorder_extra_disarmed_without_held_key_records_nothing()
  -- README 239: disarming recording prevents new notes from being recorded.
  for _, mode in ipairs({1, 0}) do
    local recorder = fresh(1, 1)
    with_recorder_globals({}, mode, function(calls)
      recorder.handle_note_midi_message(60, 100, 1, nil)
      recorder.handle_note_midi_message(64, 100, 2, 2)
      luaunit.assert_equals(recorder.mask_events, {})
      luaunit.assert_equals(calls, {})
    end)
  end
end

function test_recorder_extra_commit_hands_memory_the_merged_data()
  local recorder = fresh(1, 1)
  with_recorder_globals({}, 1, function(calls)
    recorder.add_note_mask_event_portion(6, 7, {song_pattern = 2, data = {song_pattern = 2, step = 7, note = 50}})
    recorder.add_note_mask_event_portion(6, 7, {data = {velocity = 33, chord_degrees = {[2] = 4}}})
    recorder.add_note_mask_event_portion(6, 8, {data = {step = 8, note = 51}})
    recorder.add_note_mask_event_portion(5, 7, {data = {step = 7, note = 52}})
    recorder.record_stored_note_mask_events(6, 7)
    luaunit.assert_equals(calls, {{6, "note_mask",
      {song_pattern = 2, step = 7, note = 50, velocity = 33, chord_degrees = {[2] = 4}}}})
    -- only that channel and step is cleared
    luaunit.assert_equals(recorder.mask_events, {
      [6] = {[8] = {data = {step = 8, note = 51}}},
      [5] = {[7] = {data = {step = 7, note = 52}}}
    })
    -- committing again finds nothing
    recorder.record_stored_note_mask_events(6, 7)
    luaunit.assert_equals(#calls, 1)
  end)
end

function test_recorder_extra_later_portion_overrides_and_is_copied()
  -- The note-off portion (m_midi) replaces the placeholder length stored at note-on.
  local recorder = fresh(2, 1)
  program.set_current_step_for_channel(1, 4)
  with_recorder_globals({}, 2, function(calls)
    recorder.handle_note_midi_message(60, 100, 1, nil)
    local late = {song_pattern = 2, data = {step = 4, length = 0.25, chord_degrees = {[1] = 2}}}
    recorder.add_note_mask_event_portion(1, 4, late)
    -- characterisation: the stored portion is a copy; later edits to the caller's table do not leak
    late.data.length = 8
    late.data.chord_degrees[1] = 9
    recorder.record_stored_note_mask_events(1, 4)
    luaunit.assert_equals(calls, {{1, "note_mask", {song_pattern = 2, trig = 1, note = 60,
      velocity = 100, length = 0.25, chord_degrees = {[1] = 2}, step = 4}}})
    local lock = {data = {parameter = 2, step = 4, value = 5}}
    recorder.add_trig_lock_event_portion(1, 4, lock)
    recorder.add_trig_lock_event_portion(1, 4, {data = {value = 6}})
    lock.data.parameter = 3
    recorder.record_stored_trig_lock_events(1, 4)
    luaunit.assert_equals(calls[2], {1, "trig_lock", {parameter = 2, step = 4, value = 6}})
  end)
end

function test_recorder_extra_commit_without_data_keeps_the_portion()
  -- characterisation: a portion with no data is neither sent nor cleared; later data
  -- merges into it.
  local recorder = fresh(1, 1)
  with_recorder_globals({}, 1, function(calls)
    recorder.add_note_mask_event_portion(1, 2, {song_pattern = 4})
    recorder.record_stored_note_mask_events(1, 2)
    luaunit.assert_equals(calls, {})
    luaunit.assert_equals(recorder.mask_events, {[1] = {[2] = {song_pattern = 4}}})
    recorder.add_note_mask_event_portion(1, 2, {data = {step = 2, length = 3}})
    recorder.record_stored_note_mask_events(1, 2)
    luaunit.assert_equals(calls, {{1, "note_mask", {step = 2, length = 3}}})
    luaunit.assert_equals(recorder.mask_events, {[1] = {}})

    recorder.add_trig_lock_event_portion(3, 4, {song_pattern = 4})
    recorder.record_stored_trig_lock_events(3, 4)
    luaunit.assert_equals(#calls, 1)
    luaunit.assert_equals(recorder.trig_lock_events, {[3] = {[4] = {song_pattern = 4}}})
  end)
end

function test_recorder_extra_commit_of_unknown_channel_or_step_is_a_no_op()
  local recorder = fresh(1, 1)
  with_recorder_globals({}, 1, function(calls)
    recorder.record_stored_note_mask_events(9, 1)
    recorder.record_stored_trig_lock_events(9, 1)
    recorder.add_note_mask_event_portion(9, 1, {data = {step = 1}})
    recorder.add_trig_lock_event_portion(9, 1, {data = {step = 1}})
    recorder.record_stored_note_mask_events(9, 2)
    recorder.record_stored_trig_lock_events(9, 2)
    luaunit.assert_equals(calls, {})
    luaunit.assert_equals(recorder.mask_events, {[9] = {[1] = {data = {step = 1}}}})
    luaunit.assert_equals(recorder.trig_lock_events, {[9] = {[1] = {data = {step = 1}}}})
  end)
end

function test_recorder_extra_trig_lock_commit_payload_and_isolation()
  local recorder = fresh(1, 1)
  with_recorder_globals({}, 1, function(calls)
    recorder.add_trig_lock_event_portion(2, 5, {data = {parameter = 3, step = 5}})
    recorder.add_trig_lock_event_portion(2, 5, {data = {value = 77}})
    recorder.add_trig_lock_event_portion(2, 6, {data = {parameter = 3, step = 6, value = 1}})
    recorder.add_trig_lock_event_portion(4, 5, {data = {parameter = 1, step = 5, value = 2}})
    -- note mask and trig lock stores are separate
    luaunit.assert_equals(recorder.mask_events, {})
    recorder.record_stored_trig_lock_events(2, 5)
    luaunit.assert_equals(calls, {{2, "trig_lock", {parameter = 3, step = 5, value = 77}}})
    luaunit.assert_equals(recorder.trig_lock_events, {
      [2] = {[6] = {data = {parameter = 3, step = 6, value = 1}}},
      [4] = {[5] = {data = {parameter = 1, step = 5, value = 2}}}
    })
    recorder.record_stored_trig_lock_events(4, 5)
    luaunit.assert_equals(calls[2], {4, "trig_lock", {parameter = 1, step = 5, value = 2}})
  end)
end

function test_recorder_extra_trig_lock_commit_keeps_the_queued_song_target()
  local recorder = fresh(1, 1)
  with_recorder_globals({}, 1, function(calls, target_calls)
    recorder.add_trig_lock_event_portion(2, 5, {
      song_pattern = 3,
      data = {parameter = 4, step = 5, value = 77}
    })
    program.set_selected_song_pattern(1)
    recorder.record_stored_trig_lock_events(2, 5)
    luaunit.assert_equals(calls, {})
    luaunit.assert_equals(target_calls, {{3, 2, "trig_lock", {parameter = 4, step = 5, value = 77}}})
    luaunit.assert_nil(recorder.trig_lock_events[2][5])
  end)
end

function test_recorder_extra_record_trig_event_sends_dirty_value()
  local recorder = fresh(1, 1)
  with_recorder_globals({}, 2, function(calls)
    -- clean parameter: nothing
    recorder.record_trig_event(3, 7, 4)
    luaunit.assert_equals(calls, {})
    -- characterisation: a dirty value of 0 is truthy and is recorded
    recorder.set_trig_lock_dirty(3, 4, 0)
    recorder.set_trig_lock_dirty(3, 5, 99)
    recorder.record_trig_event(3, 7, 4)
    luaunit.assert_equals(calls, {{3, "trig_lock", {parameter = 4, step = 7, value = 0}}})
    recorder.record_trig_event(3, 8, 5)
    luaunit.assert_equals(calls[2], {3, "trig_lock", {parameter = 5, step = 8, value = 99}})
    -- dirtiness is per channel
    recorder.record_trig_event(2, 7, 4)
    luaunit.assert_equals(#calls, 2)
    -- recording does not clear dirtiness
    luaunit.assert_equals(recorder.trig_lock_is_dirty(3, 4), 0)
    -- channels outside 1..16 have no dirty table
    recorder.record_trig_event(17, 1, 1)
    luaunit.assert_equals(#calls, 2)
  end)
end

function test_recorder_extra_trig_lock_is_dirty_returns_stored_value()
  local recorder = fresh(1, 1)
  luaunit.assert_equals(recorder.trig_lock_is_dirty(16, 10), false)
  luaunit.assert_nil(recorder.trig_lock_is_dirty(17, 1))
  luaunit.assert_nil(recorder.trig_lock_is_dirty(0, 1))
  luaunit.assert_nil(recorder.trig_lock_is_dirty(1, 11))
  recorder.set_trig_lock_dirty(16, 10, 12)
  luaunit.assert_equals(recorder.trig_lock_is_dirty(16, 10), 12)
  recorder.clear_trig_lock_dirty(16, 10)
  luaunit.assert_equals(recorder.trig_lock_is_dirty(16, 10), false)
end

function test_recorder_extra_clear_all_trig_lock_dirty_resets_every_slot()
  local recorder = fresh(1, 1)
  for c = 1, 16 do
    for p = 1, 10 do recorder.set_trig_lock_dirty(c, p, c * 100 + p) end
  end
  recorder.set_trig_lock_dirty(1, 11, 5)
  recorder.clear_all_trig_lock_dirty()
  local expected = {}
  for c = 1, 16 do
    expected[c] = {false, false, false, false, false, false, false, false, false, false}
  end
  luaunit.assert_equals(recorder.trig_lock_dirty, expected)
  luaunit.assert_nil(recorder.trig_lock_is_dirty(1, 11))
end

function test_recorder_extra_pending_portions_survive_clear_all_trig_lock_dirty()
  -- characterisation: clearing dirtiness does not touch stored portions.
  local recorder = fresh(1, 1)
  recorder.add_trig_lock_event_portion(1, 1, {data = {parameter = 1, step = 1, value = 3}})
  recorder.add_note_mask_event_portion(1, 1, {data = {step = 1, note = 3}})
  recorder.clear_all_trig_lock_dirty()
  luaunit.assert_equals(recorder.trig_lock_events, {[1] = {[1] = {data = {parameter = 1, step = 1, value = 3}}}})
  luaunit.assert_equals(recorder.mask_events, {[1] = {[1] = {data = {step = 1, note = 3}}}})
end
