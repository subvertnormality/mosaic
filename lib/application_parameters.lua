-- Mosaic parameter declarations and actions, in their native registration order.
local application_parameters = {}

function application_parameters.register(project_actions)
  params:add_group("mosaic", "MOSAIC", 34)
  params:add_separator("Pattern project management")
  params:add_trigger("save_p", "< Save project")
  params:set_action(
    "save_p",
    function(x)
      project_actions.save()
    end
  )
  params:add_trigger("load_p", "> Load project")
  params:set_action(
    "load_p",
    function(x)
      project_actions.load()
    end
  )
  params:add_trigger("new", "+ New")
  params:set_action(
    "new",
    function(x)
      project_actions.new()
    end
  )
  params:add_option("global_swing_shuffle_type", "Global swing type", {"Swing", "Shuffle"}, 1)
  params:set_action(
    "global_swing_shuffle_type",
    function(x)
      song_edit_page_ui.refresh_swing_shuffle_type()
      channel_edit_page_ui.refresh_swing_shuffle_type()
    end
  )
  params:hide("global_swing_shuffle_type")

  params:add_number("global_swing", "Global swing", -50, 50, 0, nil, false)
  params:set_action(
    "global_swing",
    function(x)
      song_edit_page_ui.refresh_swing()
    end
  )
  params:hide("global_swing")

  params:add_option("global_shuffle_feel", "Global shuffle feel", {"Drunk", "Smooth", "Heavy", "Clave"}, 1)
  params:set_action(
    "global_shuffle_feel",
    function(x)
      song_edit_page_ui.refresh_shuffle_feel()
    end
  )
  params:hide("global_shuffle_feel")

  params:add_option("global_shuffle_basis", "Global shuffle basis", {"9", "7", "5", "6", "8??", "9??"}, 1)
  params:set_action(
    "global_shuffle_basis",
    function(x)
      song_edit_page_ui.refresh_shuffle_basis()
    end
  )
  params:hide("global_shuffle_basis")

  params:add_number("global_shuffle_amount", "Global shuffle amount", 0, 100, 0, nil, false)
  params:set_action(
    "global_shuffle_amount",
    function(x)
      song_edit_page_ui.refresh_shuffle_amount()
    end
  )
  params:hide("global_shuffle_amount")

  params:add_separator("Sequencer")
  params:add_option("record", "Record", {"Off", "On"}, 1)
  params:add_option("stop_safety", "Shift press to stop", {"Off", "On"}, 1)
  params:add_option("song_mode", "Song mode", {"Off", "On"}, 2)
  params:add_option("wrap_param_slides", "Wrap param slides", {"Off", "On"}, 1)
  params:set_action(
    "song_mode",
    function(x)
      song_edit_page_ui:refresh()
    end
  )
  params:add_option("reset_on_end_of_pattern_repeat", "Reset on pattern repeat", {"Off", "On"}, 1)
  params:add_option("reset_on_song_pattern_transition", "Reset on song seq change", {"Off", "On"}, 2)
  params:add_option("elektron_program_changes", "Elektron program changes", {"Off", "On"}, 1)
  params:add_number("elektron_program_change_channel", "Elektron p.change channel", 1, 16, 10, nil, false)
  params:add_separator("Parameter locks")
  params:add_option("trigless_locks", "Trigless locks", {"Off", "On"}, 2)
  params:add_separator("Quantiser")
  params:add_option("quantiser_act_on_note_masks", "Snap note masks to scale", {"Off", "On"}, 2)
  params:add_option("quantiser_fully_act_on_note_masks", "Quantise note masks", {"Off", "On"}, 1)
  params:add_option("quantiser_trig_lock_hold", "Scales lock until ptn end", {"Off", "On"}, 2)
  params:add_option("all_scales_lock_to_pentatonic", "Lock all to pentatonic", {"Off", "On"}, 1)
  params:add_option("random_lock_to_pentatonic", "Lock random to pent.", {"Off", "On"}, 2)
  params:add_option("merged_lock_to_pentatonic", "Lock merged to pent.", {"Off", "On"}, 2)
  params:add_separator("Trig Editor")
  params:add_option("tresillo_amount", "Tresillo amount", {8, 16, 24, 32, 40, 48, 56, 64}, 3)
  params:set_action(
    "tresillo_amount",
    function(x)
      trigger_edit_page_ui:refresh()
    end
  )
  params:add_separator("Midi control")
  params:add_option("midi_scale_mapped_to_white_keys", "Map scale to white keys", {"Off", "On"}, 1)
  params:add_option("midi_honour_rotation", "Honour scale rotations", {"Off", "On"}, 1)
  params:add_option("midi_honour_degree", "Honour scale degree", {"Off", "On"}, 1)
  params:add_option("midi_honour_transpose", "Honour scale transpose", {"Off", "On"}, 1)

end

return application_parameters
