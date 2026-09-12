-- Exhaustive storage hardening for the ten trig-parameter slots.
-- README.md:749-760 and 939-971 define independent per-step locks and slides.

local function lock_channel(song_number, channel_number)
  program.set_selected_song_pattern(song_number)
  program.get().selected_channel = channel_number
  return program.get_channel(song_number, channel_number)
end

local function define_ten_params(channel)
  for slot = 1, 10 do
    channel.trig_lock_params[slot] = {
      id = "hardening_" .. slot,
      type = "midi",
      param_id = "hardening_param_" .. slot,
      off_value = -1,
      cc_min_value = slot,
      cc_max_value = slot + 20,
      cc_msb = slot
    }
  end
end

function test_hardening_all_ten_param_lock_slots_replace_clamp_and_preserve_off_at_boundaries()
  -- README.md:751: every channel has up to ten independently lockable trig params.
  for _, song_number in ipairs({1, 96}) do
    for _, channel_number in ipairs({1, 16}) do
      for _, step_number in ipairs({1, 64}) do
        program.init()
        local channel = lock_channel(song_number, channel_number)
        define_ten_params(channel)

        for slot = 1, 10 do
          program.add_step_param_trig_lock_to_channel(channel, step_number, slot, -100)
          luaunit.assert_equals(program.get_step_param_trig_lock(channel, step_number, slot), slot)

          program.add_step_param_trig_lock_to_channel(channel, step_number, slot, 1000)
          luaunit.assert_equals(program.get_step_param_trig_lock(channel, step_number, slot), slot + 20)

          program.add_step_param_trig_lock_to_channel(channel, step_number, slot, -1)
          luaunit.assert_equals(program.get_step_param_trig_lock(channel, step_number, slot), -1)

          program.add_step_param_trig_lock_to_channel(channel, step_number, slot, slot + 7)
          luaunit.assert_equals(program.get_step_param_trig_lock(channel, step_number, slot), slot + 7)
        end

        luaunit.assert_equals(#channel.step_trig_lock_banks[step_number], 10)
        luaunit.assert_equals(program.step_has_param_trig_lock(channel, step_number), true)
        luaunit.assert_nil(program.get_step_param_trig_lock(channel, step_number == 1 and 64 or 1, 1))

        local other_channel = program.get_channel(song_number, channel_number == 1 and 16 or 1)
        luaunit.assert_equals(other_channel.step_trig_lock_banks, {})
        local other_song = program.get_song_pattern(song_number == 1 and 96 or 1)
        luaunit.assert_equals(other_song.channels[channel_number].step_trig_lock_banks, {})
      end
    end
  end
end

function test_hardening_all_ten_global_and_step_slide_slots_toggle_clear_and_stay_isolated()
  program.init()
  local channel = lock_channel(1, 1)
  local other = program.get_channel(1, 16)

  for slot = 1, 10 do
    program.toggle_channel_param_slide(channel, slot)
    luaunit.assert_equals(program.get_channel_param_slide(channel, slot), true)
    program.toggle_channel_param_slide(channel, slot)
    luaunit.assert_equals(program.get_channel_param_slide(channel, slot), false)
    program.set_channel_param_slide(channel, slot, true)

    program.toggle_step_param_slide(channel, 1, slot)
    program.toggle_step_param_slide(channel, 64, slot)
    luaunit.assert_equals(program.get_step_param_slide(channel, 1, slot), true)
    luaunit.assert_equals(program.get_step_param_slide(channel, 64, slot), true)
  end

  luaunit.assert_equals(program.step_has_param_slide(channel, 1), true)
  luaunit.assert_equals(program.step_has_param_slide(channel, 64), true)
  luaunit.assert_equals(program.step_has_param_slide(other, 1), false)

  for slot = 1, 10 do
    program.clear_step_param_slide(channel, 1, slot)
    luaunit.assert_nil(program.get_step_param_slide(channel, 1, slot))
    luaunit.assert_equals(program.get_step_param_slide(channel, 64, slot), true)
    luaunit.assert_equals(program.get_channel_param_slide(channel, slot), true)
  end

  luaunit.assert_nil(channel.step_trig_lock_slides[1])
  luaunit.assert_equals(program.step_has_param_slide(channel, 1), false)
  luaunit.assert_equals(program.step_has_param_slide(channel, 64), true)
  luaunit.assert_equals(other.trig_lock_slides, {false, false, false, false, false, false, false, false, false, false})
end

function test_hardening_clear_step_removes_every_lock_and_slide_slot_without_touching_other_steps()
  program.init()
  local channel = lock_channel(1, 16)
  define_ten_params(channel)

  for _, step_number in ipairs({1, 64}) do
    for slot = 1, 10 do
      program.add_step_param_trig_lock_to_channel(channel, step_number, slot, slot + 3)
      program.toggle_step_param_slide(channel, step_number, slot)
    end
    program.add_step_octave_trig_lock(step_number, 2)
    program.add_step_scale_trig_lock(step_number, 16)
  end

  program.clear_trig_locks_for_step(1)
  luaunit.assert_nil(channel.step_trig_lock_banks[1])
  luaunit.assert_nil(channel.step_trig_lock_slides[1])
  luaunit.assert_nil(channel.step_octave_trig_lock_banks[1])
  luaunit.assert_nil(channel.step_scale_trig_lock_banks[1])
  luaunit.assert_equals(#channel.step_trig_lock_banks[64], 10)
  luaunit.assert_equals(#channel.step_trig_lock_slides[64], 10)
  luaunit.assert_equals(channel.step_octave_trig_lock_banks[64], 2)
  luaunit.assert_equals(channel.step_scale_trig_lock_banks[64], 16)

  program.clear_trig_locks_for_step(64)
  luaunit.assert_nil(channel.step_trig_lock_banks[64])
  luaunit.assert_nil(channel.step_trig_lock_slides[64])
  luaunit.assert_nil(channel.step_octave_trig_lock_banks[64])
  luaunit.assert_nil(channel.step_scale_trig_lock_banks[64])
end
