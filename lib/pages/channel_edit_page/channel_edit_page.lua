local channel_edit_page = {}
local pattern_buttons = {}


local quantiser = include("mosaic/lib/quantiser")

local hide_scale_fader_leds = false

local channel_edit_page_sequencer = sequencer:new(4, "channel")
local channel_select_fader = fader:new(1, 1, 16, 16)
local trig_merge_mode_button =
  button:new(
  14,
  8,
  {
    {"Skip trig merge mode on", 2},
    {"Only trig merge mode on", 5},
    {"All trig merge mode on", 8}
  }
)
local note_merge_mode_button =
  button:new(
  15,
  8,
  {
    {"Average note merge mode off", 2},
    {"Higher note merge mode on", 5},
    {"Lower note merge mode on", 8},
    {"Channel note merge mode on", 15}
  }
)
local velocity_merge_mode_button =
  button:new(
  16,
  8,
  {
    {"Average velocity merge mode off", 2},
    {"Higher velocity merge mode on", 5},
    {"Lower velocity merge mode on", 8},
    {"Channel velocity merge mode on", 15}
  }
)
local length_merge_mode_button =
  button:new(
  16,
  8,
  {
    {"Average length merge mode off", 2},
    {"Longer length merge mode on", 5},
    {"Shorter length merge mode on", 8},
    {"Channel length merge mode on", 15}
  }
)
local channel_octave_fader = fader:new(8, 8, 5, 5)
local channel_scale_fader = fader:new(1, 3, 16, 16)

function channel_edit_page.init()

  for s = 1, 16 do
    pattern_buttons["step" .. s .. "_pattern_button"] = button:new(s, 2)
  end

  channel_octave_fader:set_value(program.get_selected_channel().octave + 3)
  channel_edit_page.refresh()
  channel_edit_page_ui.refresh()

  channel_scale_fader:set_pre_func(
    function(x, y, length)
      local channel = program.get_selected_channel()
      for i = x, length + x - 1 do
        if hide_scale_fader_leds then
          break
        end
        if m_clock.is_playing() and i == channel.step_scale_number then
          grid_abstraction.led(i, y, 15)
          channel_scale_fader:set_value(0)
        end
      end
    end
  )

end

function channel_edit_page.register_draws()
  draw:register_grid(
    "channel_edit_page",
    function()
      channel_edit_page_sequencer:draw(program.get_selected_channel(), grid_abstraction.led)
    end
  )

  draw:register_grid(
    "channel_edit_page",
    function()
      channel_select_fader:draw()
    end
  )
  draw:register_grid(
    "channel_edit_page",
    function()
      channel_scale_fader:draw()
    end
  )
  for s = 1, 16 do
    draw:register_grid(
      "channel_edit_page",
      function()
        pattern_buttons["step" .. s .. "_pattern_button"]:draw()
      end
    )
  end
  draw:register_grid(
    "channel_edit_page",
    function()
      trig_merge_mode_button:draw()
    end
  )
  draw:register_grid(
    "channel_edit_page",
    function()
      note_merge_mode_button:draw()
    end
  )
  draw:register_grid(
    "channel_edit_page",
    function()
      if is_key3_down then
        length_merge_mode_button:draw()
      else
        velocity_merge_mode_button:draw()
      end
    end
  )
  draw:register_grid(
    "channel_edit_page",
    function()
      channel_octave_fader:draw()
    end
  )
end

function channel_edit_page.register_presss()
  press:register(
    "channel_edit_page",
    function(x, y)
      if channel_edit_page_sequencer:is_this(x, y) then
        if is_key3_down then
          channel_edit_page_sequencer:press(x, y)
          program.toggle_step_trig_mask(program.get().selected_channel, fn.calc_grid_count(x, y))
        end
      end
    end
  )
  press:register_long(
    "channel_edit_page",
    function(x, y)
      if channel_edit_page_sequencer:is_this(x, y) then
        if is_key3_down then
          program.clear_step_trig_mask(program.get().selected_channel, fn.calc_grid_count(x, y))
          channel_edit_page_ui.refresh_masks()
        end
      end
    end
  )
  press:register_post(
    "channel_edit_page",
    function(x, y)
      if channel_edit_page_sequencer:is_this(x, y) then
        channel_edit_page_ui.record_note_mask_event(program.get_selected_channel(), fn.calc_grid_count(x, y))
        channel_edit_page_ui.refresh_trig_locks()
        channel_edit_page_ui.refresh_masks()
        channel_edit_page.refresh_faders()
        pattern.update_working_patterns()
      end
    end
  )
  press:register(
    "channel_edit_page",
    function(x, y)
      if channel_select_fader:is_this(x, y) then
        local channel = program.get_channel(program.get().selected_sequencer_pattern, x)

        if is_key3_down == true then
          if (channel.mute == true) then
            channel.mute = false
            tooltip:show("Channel " .. x .. " unmuted")
            channel_select_fader:light(x)
          else
            channel.mute = true
            tooltip:show("Channel " .. x .. " muted")
            channel_select_fader:dim(x)
          end
          channel_edit_page.refresh_muted_channels()
          fn.dirty_screen(true)
        else
          channel_select_fader:press(x, y)
          program.get().selected_channel = x
          tooltip:show("Channel " .. x .. " selected")
          channel_edit_page_ui.set_note_dashboard_values({
            note = -1,
            velocity = -1,
            length = -1,
            chords = {-1, -1, -1, -1}
          })
          channel_edit_page.refresh()
          channel_edit_page_ui.refresh()
        end
      end
    end
  )
  press:register_long(
    "channel_edit_page",
    function(x, y)
      if channel_select_fader:is_this(x, y) then
        local channel = program.get_channel(program.get().selected_sequencer_pattern, x)

        if (channel.mute == true) then
          channel.mute = false
          tooltip:show("Channel " .. x .. " unmuted")
          channel_select_fader:light(x)
        else
          channel.mute = true
          tooltip:show("Channel " .. x .. " muted")
          channel_select_fader:dim(x)
        end
        channel_edit_page.refresh_muted_channels()
        fn.dirty_screen(true)
      end
    end
  )
  press:register_dual(
    "channel_edit_page",
    function(x, y, x2, y2)
      local channel = program.get_selected_channel()
      local selected_sequencer_pattern = program.get().selected_sequencer_pattern
      channel_edit_page_sequencer:dual_press(x, y, x2, y2)
      if channel_edit_page_sequencer:is_this(x2, y2) then
        program.get_selected_sequencer_pattern().active = true
        tooltip:show("Channel " .. program.get().selected_channel .. " length changed")
      end
      if channel_octave_fader:is_this(x2, y2) then
        channel_octave_fader:press(x2, y2)
        local s = fn.calc_grid_count(x, y)
        local channel = program.get_selected_channel()
        local octave_value = channel_octave_fader:get_value()
        if
          program.get_step_octave_trig_lock(channel, s) and
            octave_value == program.get_step_octave_trig_lock(channel, s) + 3
         then
          program.add_step_octave_trig_lock(s, nil)
        else
          program.add_step_octave_trig_lock(s, octave_value - 3)
        end
        channel_edit_page.refresh_faders()
      end
      if channel_scale_fader:is_this(x2, y2) then
        channel_scale_fader:press(x2, y2)
        local s = fn.calc_grid_count(x, y)
        local channel = program.get_selected_channel()
        local scale_value = channel_scale_fader:get_value()
        if scale_value == program.get_step_scale_trig_lock(channel, s) then
          program.add_step_scale_trig_lock(s, nil)
        else
          program.add_step_scale_trig_lock(s, scale_value)
        end
        channel_edit_page.refresh_faders()
      end
      if channel_select_fader:is_this(x, y) and channel_select_fader:is_this(x2, y2) then
        
        local channel1 = program.get_channel(program.get().selected_sequencer_pattern, x)
        local channel2 = program.get_channel(program.get().selected_sequencer_pattern, x2)

        if is_key3_down == true then

          if channel1.mute == true then
            channel1.mute = false
            channel_select_fader:light(x)
          else
            channel1.mute = true
            channel_select_fader:dim(x)
          end
          if channel2.mute == true then
            channel2.mute = false
            channel_select_fader:light(x2)
          else
            channel2.mute = true
            channel_select_fader:dim(x2)
          end
          tooltip:show("Channel mutes toggled")
          channel_edit_page.refresh_muted_channels()
          fn.dirty_screen(true)
        end
      end
    end
  )
  for s = 1, 16 do
    press:register(
      "channel_edit_page",
      function(x, y)
        if pattern_buttons["step" .. s .. "_pattern_button"]:is_this(x, y) then
          local selected_sequencer_pattern = program.get().selected_sequencer_pattern
          pattern_buttons["step" .. s .. "_pattern_button"]:press(x, y)
          if pattern_buttons["step" .. s .. "_pattern_button"]:get_state() == 2 then
            fn.add_to_set(program.get_selected_channel().selected_patterns, x)
            program.get_selected_sequencer_pattern().active = true
            tooltip:show("Pattern " .. x .. " added to ch. " .. program.get().selected_channel)
          else
            fn.remove_from_set(program.get_selected_channel().selected_patterns, x)
            program.get_selected_sequencer_pattern().active = true
            tooltip:show("Pattern " .. x .. " removed from ch. " .. program.get().selected_channel)
          end
          pattern.update_working_patterns()
          program.get_selected_sequencer_pattern().active = true
        end
      end
    )
  end
  press:register(
    "channel_edit_page",
    function(x, y)
      if trig_merge_mode_button:is_this(x, y) then
        trig_merge_mode_button:press(x, y)

        if trig_merge_mode_button:get_state() == 1 then

          program.get_selected_channel().trig_merge_mode = "skip"

          tooltip:show(
            "Skip trig merge mode"
          )
        elseif trig_merge_mode_button:get_state() == 2 then

          program.get_selected_channel().trig_merge_mode = "only"
          tooltip:show(
            "Only trig merge mode"
          )
        elseif trig_merge_mode_button:get_state() == 3 then

          program.get_selected_channel().trig_merge_mode = "all"
          tooltip:show(
            "All trig merge mode"
          )
        end

        program.get_selected_sequencer_pattern().active = true
        pattern.update_working_patterns()

      end
    end
  )
  press:register(
    "channel_edit_page",
    function(x, y)
      if note_merge_mode_button:is_this(x, y) then

        note_merge_mode_button:press(x, y)

        if note_merge_mode_button:get_state() == 1 then
          program.get_selected_channel().note_merge_mode = "average"
          tooltip:show(
            "Average note merge mode"
          )
        elseif note_merge_mode_button:get_state() == 2 then
          program.get_selected_channel().note_merge_mode = "up"
          tooltip:show(
            "Higher note merge mode"
          )
        elseif note_merge_mode_button:get_state() == 3 then
          program.get_selected_channel().note_merge_mode = "down"
          tooltip:show(
            "Lower note merge mode"
          )
        elseif note_merge_mode_button:get_state() == 4 then

          note_merge_mode_button:set_state(1)
          tooltip:show(
            "Average note merge mode"
          )
        end

        program.get_selected_sequencer_pattern().active = true
        pattern.update_working_patterns()

      end
    end
  )
  press:register(
    "channel_edit_page",
    function(x, y)
      if velocity_merge_mode_button:is_this(x, y) and not is_key3_down then

        velocity_merge_mode_button:press(x, y)

        if velocity_merge_mode_button:get_state() == 1 then
          program.get_selected_channel().velocity_merge_mode = "average"
          tooltip:show(
            "Average velocity merge mode"
          )
        elseif velocity_merge_mode_button:get_state() == 2 then
          program.get_selected_channel().velocity_merge_mode = "up"
          tooltip:show(
            "Higher velocity merge mode"
          )
        elseif velocity_merge_mode_button:get_state() == 3 then
          program.get_selected_channel().velocity_merge_mode = "down"
          tooltip:show(
            "Lower velocity merge mode"
          )
        elseif velocity_merge_mode_button:get_state() == 4 then
          velocity_merge_mode_button:set_state(1)
          tooltip:show(
            "Average velocity merge mode"
          )
        end

        program.get_selected_sequencer_pattern().active = true
        pattern.update_working_patterns()

      end
    end

  )
  press:register(
    "channel_edit_page",
    function(x, y)
      if length_merge_mode_button:is_this(x, y) and is_key3_down then

        length_merge_mode_button:press(x, y)

        if length_merge_mode_button:get_state() == 1 then
          program.get_selected_channel().length_merge_mode = "average"
          tooltip:show(
            "Average length merge mode"
          )
        elseif length_merge_mode_button:get_state() == 2 then
          program.get_selected_channel().length_merge_mode = "up"
          tooltip:show(
            "Longer length merge mode"
          )
        elseif length_merge_mode_button:get_state() == 3 then
          program.get_selected_channel().length_merge_mode = "down"
          tooltip:show(
            "Shorter length merge mode"
          )
        elseif length_merge_mode_button:get_state() == 4 then
          length_merge_mode_button:set_state(1)
          tooltip:show(
            "Average length merge mode"
          )
        end

        program.get_selected_sequencer_pattern().active = true
        pattern.update_working_patterns()
      end
    end
  )
  press:register(
    "channel_edit_page",
    function(x, y)
      if channel_octave_fader:is_this(x, y) then
        channel_octave_fader:press(x, y)
        program.get_selected_channel().octave = channel_octave_fader:get_value() - 3
        program.get_selected_sequencer_pattern().active = true
        tooltip:show("Ch. " .. program.get().selected_channel .. " octave: " .. channel_octave_fader:get_value() - 3)
      end
    end
  )
  press:register_dual(
    "channel_edit_page",
    function(x, y, x2, y2)
      if pattern_buttons["step" .. x2 .. "_pattern_button"]:is_this(x2, y2) then
        if note_merge_mode_button:is_this(x, y) then
          program.get_selected_channel().note_merge_mode = "pattern_number_" .. x2
          note_merge_mode_button:set_state(4)
          program.get_selected_sequencer_pattern().active = true
          pattern.update_working_patterns()
          tooltip:show(
            "Note merge mode pattern " ..x2
          )
        end
        if velocity_merge_mode_button:is_this(x, y) then
          program.get_selected_channel().velocity_merge_mode = "pattern_number_" .. x2
          velocity_merge_mode_button:set_state(4)
          program.get_selected_sequencer_pattern().active = true
          pattern.update_working_patterns()
          tooltip:show(
            "Velocity merge mode pattern " ..x2
          )
        end
        if length_merge_mode_button:is_this(x, y) then
          program.get_selected_channel().length_merge_mode = "pattern_number_" .. x2
          length_merge_mode_button:set_state(4)
          program.get_selected_sequencer_pattern().active = true
          pattern.update_working_patterns()
          tooltip:show(
            "Length merge mode pattern " ..x2
          )
        end
      end
    end
  )
  press:register_pre(
    "channel_edit_page",
    function(x, y)
      if channel_edit_page_sequencer:is_this(x, y) then
        channel_edit_page_ui.refresh_masks()
        channel_edit_page_ui.refresh_trig_locks()
        channel_edit_page.refresh_faders()
      end
    end
  )
end

function channel_edit_page.handle_note_midi_message(note, velocity, chord_number, chord_degree)
  local pressed_keys = m_grid.get_pressed_keys()
  local channel = program.get_selected_channel()
  if #pressed_keys > 0 then
    if (pressed_keys[1][2] > 3 and pressed_keys[1][2] < 8) then

      local s = fn.calc_grid_count(pressed_keys[1][1], pressed_keys[1][2])
      if chord_number == 1 then
        channel_edit_page_ui.add_note_mask_event_portion(
          channel, 
          s, 
          {
            sequencer_pattern = program.get().selected_sequencer_pattern,
            data = {
              trig = 1,
              note = note,
              velocity = velocity,
              length = 1,
              chord_degrees = {nil, nil, nil, nil},
              step = s
            }
          }
        )
      elseif (chord_degree) then
        local chord = {}
        chord[chord_number - 1] = chord_degree 
        channel_edit_page_ui.add_note_mask_event_portion(
          channel, 
          s, 
          {
            sequencer_pattern = program.get().selected_sequencer_pattern,
            data = {
              step = s,
              chord_degrees = chord
            }
          }
        )
      end

    end
  elseif params:get("record") == 2 then
    local s = program.get_current_step_for_channel(channel.number)
    if chord_number == 1 then
      channel_edit_page_ui.add_note_mask_event_portion(
          channel, 
          s, 
          {
            sequencer_pattern = program.get().selected_sequencer_pattern,
            data = {
              trig = 1,
              note = note,
              velocity = velocity,
              length = 1,
              chord_degrees = {nil, nil, nil, nil},
              step = s
            }
          }
        )
    elseif (chord_degree) then
      local chord = {}
      chord[chord_number - 1] = chord_degree 
      channel_edit_page_ui.add_note_mask_event_portion(
          channel, 
          s, 
          {
            sequencer_pattern = program.get().selected_sequencer_pattern,
            data = {
              step = s,
              chord_degrees = chord
            }
          }
        )
    end
  end
end


function channel_edit_page.refresh_merge_buttons()
  local trig_merge_mode = program.get_selected_channel().trig_merge_mode
  local note_merge_mode = program.get_selected_channel().note_merge_mode
  local velocity_merge_mode = program.get_selected_channel().velocity_merge_mode
  local length_merge_mode = program.get_selected_channel().length_merge_mode

  if trig_merge_mode == "skip" then
    trig_merge_mode_button:set_state(1)
  elseif trig_merge_mode == "only" then
    trig_merge_mode_button:set_state(2)
  elseif trig_merge_mode == "all" then
    trig_merge_mode_button:set_state(3)
  end

  if note_merge_mode == "average" then
    note_merge_mode_button:set_state(1)
  elseif note_merge_mode == "up" then
    note_merge_mode_button:set_state(2)
  elseif note_merge_mode == "down" then
    note_merge_mode_button:set_state(3)
  elseif string.match(note_merge_mode, "pattern_number_") then
    note_merge_mode_button:set_state(4)
  end

  if velocity_merge_mode == "average" then
    velocity_merge_mode_button:set_state(1)
  elseif velocity_merge_mode == "up" then
    velocity_merge_mode_button:set_state(2)
  elseif velocity_merge_mode == "down" then
    velocity_merge_mode_button:set_state(3)
  elseif string.match(velocity_merge_mode, "pattern_number_") then
    velocity_merge_mode_button:set_state(4)
  end

  if length_merge_mode == "average" then
    length_merge_mode_button:set_state(1)
  elseif length_merge_mode == "up" then
    length_merge_mode_button:set_state(2)
  elseif length_merge_mode == "down" then
    length_merge_mode_button:set_state(3)
  elseif string.match(length_merge_mode, "pattern_number_") then
    length_merge_mode_button:set_state(4)
  end

  channel_select_fader:set_value(program.get().selected_channel)
end

function channel_edit_page.refresh_muted_channels()
  for i = 1, 16 do
    if program.get_channel(program.get().selected_sequencer_pattern, i).mute == true then
      channel_select_fader:dim(i)
    else
      channel_select_fader:light(i)
    end
  end
end

function channel_edit_page.refresh_faders()
  local channel = program.get_selected_channel()
  channel_select_fader:set_value(program.get().selected_channel)
  local pressed_keys = m_grid.get_pressed_keys()
  if #pressed_keys > 0 then
    local s = fn.calc_grid_count(pressed_keys[1][1], pressed_keys[1][2])
    local step_scale_trig_lock = program.get_step_scale_trig_lock(channel, s)
    local step_octave_trig_lock = program.get_step_octave_trig_lock(channel, s)
    if step_scale_trig_lock then
      channel_scale_fader:set_value(step_scale_trig_lock)
      hide_scale_fader_leds = true
    else
      if program.get().default_scale > 0 then
        channel_scale_fader:set_value(program.get().default_scale)
      else
        channel_scale_fader:set_value(0)
      end
    end
    if step_octave_trig_lock then
      channel_octave_fader:set_value(step_octave_trig_lock + 3)
    else
      channel_octave_fader:set_value(channel.octave + 3)
    end
  else
    channel_scale_fader:set_value(program.get().default_scale)
    channel_octave_fader:set_value(channel.octave + 3)
    hide_scale_fader_leds = false
  end
end

function channel_edit_page.refresh_step_buttons()
  local channel = program.get_selected_channel()

  local selected_sequencer_pattern = program.get().selected_sequencer_pattern
  for s = 1, 16 do
    if pattern_buttons["step" .. s .. "_pattern_button"] then
      if channel.selected_patterns[s] ~= nil then
        pattern_buttons["step" .. s .. "_pattern_button"]:set_state(2)
      else
        pattern_buttons["step" .. s .. "_pattern_button"]:set_state(1)
      end
    end
  end
end

function channel_edit_page.refresh()
  channel_edit_page.refresh_faders()
  channel_edit_page.refresh_step_buttons()
  channel_edit_page.refresh_merge_buttons()
  channel_edit_page.refresh_muted_channels()
end

return channel_edit_page
