
local lattice = include("mosaic/lib/clock/m_lattice")

m_clock = {}
clock_lattice = {}

local playing = false
local master_clock
local midi_clock_init
local trigless_lock_active = {}
local first_run = true

local delayed_ids_must_execute = {[0] = {}}
for i = 1, 16 do delayed_ids_must_execute[i] = {} end

local destroy_at_note_end_ids = {[0] = {}}
for i = 1, 16 do destroy_at_note_end_ids[i] = {} end

local arp_sprockets = {[0] = {}}
for i = 1, 16 do arp_sprockets[i] = {} end

local execute_at_note_end_ids = {[0] = {}}
for i = 1, 16 do execute_at_note_end_ids[i] = {} end

local clock_divisions = include("mosaic/lib/clock/divisions").clock_divisions

-- Localizing math and table functions for performance
local remove = table.remove
local insert = table.insert
local pairs, ipairs = pairs, ipairs
local program = program
local table = table

local function calculate_divisor(clock_mod)
  if clock_mod.type == "clock_multiplication" then
    return 4 * clock_mod.value
  elseif clock_mod.type == "clock_division" then
    return 4 / clock_mod.value
  else
    return 4
  end
end

m_clock.calculate_divisor = calculate_divisor

local function destroy_sprockets(sprocket_tables)
  for _, sprocket_table in ipairs(sprocket_tables) do
    for j = #sprocket_table, 1, -1 do
      local sprocket = sprocket_table[j]
      if sprocket then 
        sprocket:destroy()
        remove(sprocket_table, j)
      end
    end
  end
end

local destroy_arp_sprockets = function() destroy_sprockets(arp_sprockets) end

local function execute_ids(c, ids)
  local clock = m_clock["channel_" .. c .. "_clock"]
  
  for i = #ids, 1, -1 do
    local id = ids[i]
    if clock and clock.delayed_actions and clock.delayed_actions[id] then
      local action = clock.delayed_actions[id].action
      if type(action) == "function" then
        action()
      end
      clock.delayed_actions[id] = nil  -- Remove the action after execution
      table.remove(ids, i)  -- Remove the ID from the list
    end
  end
end

local function construct_remove_id_from_all_lists_for_channel(chan)
  local c = chan
  return function(id)
    local lists = {
      delayed_ids_must_execute,
      destroy_at_note_end_ids,
      execute_at_note_end_ids
    }

    for _, list in ipairs(lists) do
      for i = #list[c], 1, -1 do
        if list[c][i] == id then
          table.remove(list[c], i)
          break
        end
      end
    end
  end
end

local function get_shuffle_values(channel)

  local shuffle_values = {
    swing = (channel.swing ~= -51) and channel.swing or params:get("global_swing") or 0,
    swing_or_shuffle = (channel.swing_shuffle_type and channel.swing_shuffle_type > 0) and (channel.swing_shuffle_type) or params:get("global_swing_shuffle_type"),
    shuffle_basis = (channel.shuffle_basis and channel.shuffle_basis > 0) and (channel.shuffle_basis) or params:get("global_shuffle_basis"),
    shuffle_feel = (channel.shuffle_feel and channel.shuffle_feel > 0) and (channel.shuffle_feel) or params:get("global_shuffle_feel"),
    shuffle_amount = channel.shuffle_amount or params:get("global_shuffle_amount")
  }
  
  if channel.number == 17 then
    shuffle_values.swing = 0
    shuffle_values.swing_or_shuffle = 1
    shuffle_values.shuffle_basis = 0
    shuffle_values.shuffle_feel = 0
    shuffle_values.shuffle_amount = 0
  end
  
  return shuffle_values
end

function m_clock.init()
  local program_data = program.get()
  clock_lattice = lattice:new({
    enabled = false
  })

  if testing then
    clock_lattice.auto = false
  end

  clock_lattice.pattern_length = program.get_selected_song_pattern().global_pattern_length

  destroy_arp_sprockets()

  for i = 1, 16 do 
    delayed_ids_must_execute[i] = {}
    destroy_at_note_end_ids[i] = {}
    execute_at_note_end_ids[i] = {}
    arp_sprockets[i] = {}
  end


  master_clock = clock_lattice:new_sprocket {
    action = function(t)
      local selected_song_pattern = program_data.song_patterns[program_data.selected_song_pattern]
      if params:get("elektron_program_changes") == 2 and program_data.current_step == selected_song_pattern.global_pattern_length - 1 then
        step.process_elektron_program_change(step.calculate_next_selected_song_pattern())
      end
      if not first_run then
        step.process_song_song_patterns(program_data.current_step)
        selected_song_pattern = program_data.song_patterns[program_data.selected_song_pattern]
        for i = 1, 17 do
          if ((program.get_current_step_for_channel(i) - 1) % selected_song_pattern.global_pattern_length) + 1 == selected_song_pattern.global_pattern_length then
            local channel = program.get_channel(program.get().selected_song_pattern, i)
            if (fn.calc_grid_count(channel.end_trig[1], channel.end_trig[2]) - fn.calc_grid_count(channel.start_trig[1], channel.start_trig[2]) + 1) > selected_song_pattern.global_pattern_length then
              program.set_current_step_for_channel(i, 99)
            end
          end
        end
      end

      program_data.current_step = program_data.current_step + 1
      program_data.global_step_accumulator = program_data.global_step_accumulator + 1

      if program_data.current_step > program.get_selected_song_pattern().global_pattern_length then
        program_data.current_step = 1
        first_run = false
      end
      
      fn.dirty_screen(true)
      
    end,
    division = 1 / 16,
    swing = 0,
    swing_or_shuffle = 1,
    shuffle_basis = 0,
    shuffle_feel = 0,
    shuffle_amount = 0,
    order = 1,
    realign = false,
    enabled = true
  }

  local channel_edit_page = pages.pages.channel_edit_page
  local scale_edit_page = pages.pages.scale_edit_page
  for channel_number = 17, 1, -1 do
    local div = calculate_divisor(program.get_channel(program.get().selected_song_pattern, channel_number).clock_mods)

    local sprocket_action = function(t)
      local channel = program.get_channel(program.get().selected_song_pattern, channel_number)
      local current_step = program.get_current_step_for_channel(channel_number)
      local start_trig = fn.calc_grid_count(channel.start_trig[1], channel.start_trig[2])
      local end_trig = fn.calc_grid_count(channel.end_trig[1], channel.end_trig[2])

      local channel_length = end_trig - start_trig + 1

      if channel_length > program.get_selected_song_pattern().global_pattern_length then
        end_trig = start_trig + program.get_selected_song_pattern().global_pattern_length - 1
      end

      if not m_clock["channel_" .. channel_number .. "_clock"].first_run then
        program.set_current_step_for_channel(channel_number, current_step + 1)
        current_step = current_step + 1
      end

      if current_step < start_trig then
        program.set_current_step_for_channel(channel_number, start_trig)
        current_step = start_trig
      end

      if current_step > end_trig then
        program.set_current_step_for_channel(channel_number, start_trig)
        current_step = start_trig
      end

      if channel_number == 17 then
        program_data.current_scale_channel_step = current_step
        step.process_global_step_scale_trig_lock(current_step)
        step.sinfonian_sync(current_step)
      else
        program.set_channel_step_scale_number(channel_number, step.calculate_step_scale_number(channel_number, current_step))
        
        if channel.working_pattern.trig_values[current_step] == 1 then
          step.handle(channel_number, current_step)
        end
      end

      m_clock["channel_" .. channel_number .. "_clock"].first_run = false
      m_clock["channel_" .. channel_number .. "_clock"].next_step = current_step

      if program_data.selected_channel == channel_number and (program_data.selected_page == channel_edit_page or program_data.selected_page == scale_edit_page)  then
        fn.dirty_grid(true)
      end

    end

    local end_of_clock_action = function(t)
      local channel = program.get_channel(program.get().selected_song_pattern, channel_number)
      if channel_number ~= 17 then

        local start_trig = fn.calc_grid_count(channel.start_trig[1], channel.start_trig[2])
        local end_trig = fn.calc_grid_count(channel.end_trig[1], channel.end_trig[2])

        local last_step = program.get_current_step_for_channel(channel_number) - 1
        if last_step < 1 then
          last_step = end_trig
        end

        if params:get("record") == 2 and program.get_selected_channel() == channel then
          step.record_mask_event(channel, last_step)
        end

        local next_step = program.get_current_step_for_channel(channel_number) + 1
        if next_step < 1 then return end

        if next_step > end_trig then
          next_step = start_trig
        end

        local next_trig_value = channel.working_pattern.trig_values[next_step]

        if next_trig_value == 1 then
          trigless_lock_active[channel_number] = false
          step.process_params(channel_number, next_step)
        elseif params:get("trigless_locks") == 2 and not trigless_lock_active[channel_number] and program.step_has_param_trig_lock(channel, next_step) then
          trigless_lock_active[channel_number] = true
          step.process_params(channel_number, next_step)
        end

      end
    end

    local shuffle_values = get_shuffle_values(program.get_channel(program.get().selected_song_pattern, channel_number))

    m_clock["channel_" .. channel_number .. "_clock"] = clock_lattice:new_sprocket {
      action = sprocket_action,
      division = 1 / (div * 4),
      swing = shuffle_values.swing,
      swing_or_shuffle = shuffle_values.swing_or_shuffle,
      shuffle_basis = shuffle_values.shuffle_basis,
      shuffle_feel = shuffle_values.shuffle_feel,
      shuffle_amount = shuffle_values.shuffle_amount,
      order = 2,
      realign = true,
      enabled = true,
      cleanup_delayed_action = construct_remove_id_from_all_lists_for_channel(channel_number)
    }

    m_clock["channel_" .. channel_number .. "_clock"].end_of_clock_processor = clock_lattice:new_sprocket {
      action = end_of_clock_action,
      division = 1 / (div * 4),
      swing = shuffle_values.swing,
      swing_or_shuffle = shuffle_values.swing_or_shuffle,
      shuffle_basis = shuffle_values.shuffle_basis,
      shuffle_feel = shuffle_values.shuffle_feel,
      shuffle_amount = shuffle_values.shuffle_amount,
      delay = 1,
      order = 3,
      realign = true,
      enabled = true
    }

    m_clock["channel_" .. channel_number .. "_clock"].first_run = true
  end
end

function m_clock.set_swing_shuffle_type(channel_number, swing_or_shuffle)
  local clock = m_clock["channel_" .. channel_number .. "_clock"]
  clock:set_swing_or_shuffle((swing_or_shuffle or 2) - 1)
  clock.end_of_clock_processor:set_swing_or_shuffle((swing_or_shuffle or 2) - 1)
end

function m_clock.set_channel_swing(channel_number, swing)
  local clock = m_clock["channel_" .. channel_number .. "_clock"]
  clock:set_swing(swing or 0)
  clock.end_of_clock_processor:set_swing(swing or 0)
end

function m_clock.set_channel_shuffle_feel(channel_number, shuffle_feel)
  local clock = m_clock["channel_" .. channel_number .. "_clock"]
  clock:set_shuffle_feel((shuffle_feel or 2) - 1)
  clock.end_of_clock_processor:set_shuffle_feel((shuffle_feel or 2) - 1)
end

function m_clock.set_channel_shuffle_basis(channel_number, shuffle_basis)
  local clock = m_clock["channel_" .. channel_number .. "_clock"]
  clock:set_shuffle_basis((shuffle_basis or 2) - 1)
  clock.end_of_clock_processor:set_shuffle_basis((shuffle_basis or 2) - 1)
end

function m_clock.set_channel_shuffle_amount(channel_number, shuffle_amount)
  local clock = m_clock["channel_" .. channel_number .. "_clock"]
  clock:set_shuffle_amount(shuffle_amount or 0)
  clock.end_of_clock_processor:set_shuffle_amount(shuffle_amount or 0)
end

function m_clock.set_channel_division(channel_number, division)
  local clock = m_clock["channel_" .. channel_number .. "_clock"]
  local div_value = 1 / (division * 4)
  clock:set_division(div_value)
  clock.end_of_clock_processor:set_division(div_value)
end

function m_clock.get_channel_division(channel_number)
  local clock = m_clock["channel_" .. channel_number .. "_clock"]
  return clock and clock.division or 0.4
end


function m_clock.delay_action(c, length, type, func)
  if length == 0 or length == nil then
    func()
    return
  end

  local id = m_clock["channel_" .. c .. "_clock"]:set_delayed_action(length, func)


  if type == "must_execute" then
    table.insert(delayed_ids_must_execute[c], id)
  elseif type == "destroy_at_note_end" then
    table.insert(destroy_at_note_end_ids[c], id)
  elseif type == "execute_at_note_end" then
    table.insert(execute_at_note_end_ids[c], id)
  end

end


function m_clock.new_arp_sprocket(c, division, chord_spread, chord_acceleration, length, func)
  if division == 0 or division == nil then
    return
  end

  local channel = program.get_channel(program.get().selected_song_pattern, c)

  -- Clear existing arp sprockets for the channel
  if arp_sprockets[c] then
    for i, sprocket in ipairs(arp_sprockets[c]) do
      sprocket:destroy()
    end
    arp_sprockets[c] = {}
  end

  local arp
  local runs = 1
  local acceleration_accumulator = 0

  local sprocket_action = function(div)
    func(div)

    -- Check if the arp should stop
    if length == 0 then
      if arp then
        arp:destroy()
        arp = nil
      end

      -- Execute pending note-off sprockets
      if execute_at_note_end_ids[c] then
        execute_ids(c, execute_at_note_end_ids[c])
      end

      -- Clean up the sprocket from arp_sprockets[c]
      for i = #arp_sprockets[c], 1, -1 do
        if arp_sprockets[c][i] == arp then
          table.remove(arp_sprockets[c], i)
          break
        end
      end

      -- Kill any remaining arp delay sprockets
      m_clock.destroy_at_note_end_ids(c)
    end
  end

  local shuffle_values = get_shuffle_values(channel)
  arp = clock_lattice:new_sprocket {
    action = function()
      runs = runs + 1
      local div = (division + ((chord_spread * chord_acceleration * (runs - 1))) + (acceleration_accumulator * chord_acceleration))

      sprocket_action(div)

      if div <= 0 then
        if arp then
          arp:destroy()
          arp = nil
        end
        m_clock.destroy_at_note_end_ids(c)
      else
        arp:set_division(div * m_clock["channel_" .. c .. "_clock"].division)
      end
    end,
    division = (division + (chord_spread * chord_acceleration)) * m_clock["channel_" .. c .. "_clock"].division,
    enabled = true,
    swing = shuffle_values.swing,
    swing_or_shuffle = shuffle_values.swing_or_shuffle,
    shuffle_basis = shuffle_values.shuffle_basis,
    shuffle_feel = shuffle_values.shuffle_feel,
    shuffle_amount = shuffle_values.shuffle_amount,
    delay = division + chord_spread,
    realign = false,
    order = 2,
    step = m_clock["channel_" .. c .. "_clock"]:get_step()
  }

  acceleration_accumulator = acceleration_accumulator + chord_spread

  -- Schedule the arp to stop after 'length'
  m_clock.delay_action(c, length, "must_execute", function()

    if arp then
      arp:destroy()
      arp = nil
    end

    -- Execute pending note-off sprockets
    if execute_at_note_end_ids[c] then
      execute_ids(c, execute_at_note_end_ids[c])
    end

    -- Kill any remaining arp delay sprockets
    m_clock.destroy_at_note_end_ids(c)
  end)

  table.insert(arp_sprockets[c], arp)
end


function m_clock.destroy_at_note_end_ids(c)
  local clock = m_clock["channel_" .. c .. "_clock"]
  
  for i = #destroy_at_note_end_ids[c], 1, -1 do
    local id = destroy_at_note_end_ids[c][i]
    if clock and clock.delayed_actions and clock.delayed_actions[id] then
      clock.delayed_actions[id] = nil
      table.remove(destroy_at_note_end_ids[c], i)
    end
  end
end

function m_clock.realign_sprockets()
  clock_lattice:realign_eligable_sprockets()
end

function m_clock:start()
  first_run = true
  if params:get("elektron_program_changes") == 2 then
    step.process_elektron_program_change(program.get().selected_song_pattern)
  end
  
  m_clock.set_playing()
  clock_lattice:start()
  m_midi.start()

  for i = 1, 16 do
    step.process_params(i, 1)
  end
       
end

function m_clock:stop()

  playing = false
  first_run = true

  for c = 1, 16 do
    execute_ids(c, delayed_ids_must_execute[c])
    if execute_at_note_end_ids[c] then
      execute_ids(c, execute_at_note_end_ids[c])
      execute_at_note_end_ids[c] = {}
    end
  end

  nb:stop_all()
  m_midi:stop()

  if clock_lattice and clock_lattice.stop then
    clock_lattice:stop()
  end

  m_clock.reset()

  collectgarbage("collect")
end

function m_clock.is_playing()
  return playing
end

function m_clock.set_playing()
  playing = true
end

function m_clock.reset()
  local program_data = program.get()
  for _, pattern in ipairs(program_data.song_patterns) do
    for i = 1, 17 do
      program.set_current_step_for_channel(i, 1)
    end
  end

  program_data.current_step = 1
  step.reset()

  if clock_lattice and clock_lattice.destroy then
    clock_lattice:destroy()
    clock_lattice = nil
  end

  m_clock.init()
end

function m_clock.panic()
  m_midi.panic()
end

function m_clock.get_clock_divisions()
  return clock_divisions
end

function m_clock.get_clock_lattice()
  return clock_lattice
end

return m_clock
