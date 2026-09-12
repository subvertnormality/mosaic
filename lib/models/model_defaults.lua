local model_defaults = {}

function model_defaults.new(quantiser, nrpn_codec)
  local defaults = {}

  function defaults.migrate(data, get_device)
    if not data then return end
    if data.sequencer_patterns and not data.song_patterns then
      data.song_patterns = data.sequencer_patterns
      data.sequencer_patterns = nil
    end
    if not data.song_patterns then data.song_patterns = {} end
    for _, pattern in pairs(data.song_patterns) do
      if pattern.sequencer_patterns then
        pattern.song_patterns = pattern.sequencer_patterns
        pattern.sequencer_patterns = nil
      end
    end
    return nrpn_codec.migrate(data, get_device)
  end

  function defaults.table_64(value)
    local values = {}
    for i = 1, 64 do values[i] = value end
    return values
  end

  function defaults.pattern()
    return {
      trig_values = defaults.table_64(0),
      lengths = defaults.table_64(1),
      note_values = defaults.table_64(0),
      note_mask_values = defaults.table_64(-1),
      velocity_values = defaults.table_64(100)
    }
  end

  local function channels()
    local values = {}
    for i = 1, 17 do
      values[i] = {
        number = i,
        trig_lock_params = {{}, {}, {}, {}, {}, {}, {}, {}, {}, {}},
        trig_lock_calculator_ids = {},
        step_trig_lock_banks = {},
        trig_lock_slides = {false, false, false, false, false, false, false, false, false, false},
        step_trig_lock_slides = {},
        step_octave_trig_lock_banks = {},
        step_scale_trig_lock_banks = {},
        step_trig_masks = {},
        step_note_masks = {},
        step_velocity_masks = {},
        step_length_masks = {},
        step_micro_time_masks = {},
        step_chord_masks = {},
        working_pattern = {
          trig_values = defaults.table_64(0),
          lengths = defaults.table_64(1),
          note_values = defaults.table_64(0),
          velocity_values = defaults.table_64(100),
          note_mask_values = {},
        },
        start_trig = {1, 4},
        end_trig = {16, 7},
        selected_patterns = {},
        default_scale = 1,
        step_scale_number = 1,
        root_note = 0,
        chord = 1,
        trig_merge_mode = "skip",
        note_merge_mode = "average",
        velocity_merge_mode = "average",
        length_merge_mode = "average",
        octave = 0,
        clock_mods = {name = "/1", value = 1, type = "clock_division"},
        current_step = 1,
        mute = false,
        swing_shuffle_type = nil,
        swing = nil,
        shuffle_feel = nil,
        shuffle_basis = nil,
        shuffle_amount = nil
      }
    end
    return values
  end

  local function patterns()
    local values = {}
    for i = 1, 16 do values[i] = defaults.pattern() end
    return values
  end

  function defaults.song_pattern()
    local c_major = quantiser.get_scale(1)
    local value = {
      active = false,
      global_pattern_length = 64,
      scale = 0,
      repeats = 1,
      patterns = patterns(),
      channels = channels(),
      scales = {}
    }
    for i = 1, 16 do
      table.insert(value.scales, {
        number = 1,
        scale = c_major.scale,
        pentatonic_scale = c_major.pentatonic_scale,
        root_note = 0,
        chord = 1,
        chord_degree_rotation = 0,
        version = 1
      })
    end
    return value
  end

  function defaults.program(selected_page)
    local value = {
      nrpn_policy_version = 1,
      nrpn_stored_modes = {},
      selected_page = selected_page,
      selected_song_pattern = 1,
      selected_pattern = 1,
      selected_channel = 1,
      selected_scale = 1,
      root_note = 0,
      chord = 1,
      default_scale = 1,
      current_step = 1,
      current_channel_step = {1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1},
      song_patterns = {},
      global_step_accumulator = 0,
      devices = {},
      blink_state = false,
      memory = {channels = {}, current_indices = {}, original_states = {}, pattern_states = {}}
    }
    for i = 1, 16 do
      table.insert(value.devices, {midi_channel = 1, midi_device = 1, device_map = "none"})
    end
    return value
  end

  return defaults
end

return model_defaults
