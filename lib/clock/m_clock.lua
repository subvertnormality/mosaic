local midi_patch_recall = include("mosaic/lib/devices/midi_patch_recall")
local chord_timing = include("mosaic/lib/clock/chord_timing")
local lattice = include("mosaic/lib/clock/m_lattice")
local midi_output_transport = include("mosaic/lib/clock/midi_output_transport")
local step_cursor = include("mosaic/lib/clock/step_cursor")
local parameter_preview = include("mosaic/lib/clock/parameter_preview")

m_clock = {}
clock_lattice = {}

local master_clock
local midi_clock_init
local first_run = true

local ppqn = 96

-- Lock lookahead. With no scheduler installed none of this runs and playback is
-- exactly as it was. The lead is expressed in whole pulses, because a value that
-- leaves inside a pulse the sequencer was already running costs no timer and no
-- work part way through a step.
local lock_lookahead = include("mosaic/lib/clock/lock_lookahead")
local cached_tempo, cached_lead_ms, cached_lead_pulses

-- The scheduler lives on the shared m_clock table rather than in a file local.
-- include() is dofile in the test harness, so a module can be executed more than
-- once and each execution gets its own locals; state that playback and the
-- installer must agree on has to live somewhere they both see.
function m_clock.set_lock_lookahead(scheduler)
  m_clock.lookahead_scheduler = scheduler
  cached_tempo, cached_lead_ms, cached_lead_pulses = nil, nil, nil
end

-- Select which lock lead contract is in force. "legacy-delay-v1" is the existing
-- behaviour, where a lead comes from delaying notes, clock and transport behind
-- the locks. "pulse-advance" delays nothing and sends the locks early instead.
-- Switching contracts rebuilds the scheduler, so nothing is left in flight.
function m_clock.set_lock_contract(contract)
  m_midi.set_lock_contract(contract)
  if contract == "pulse-advance" then
    local scheduler = lock_lookahead.new{send = function(bundle) step.send_preview_bundle(bundle) end}
    m_clock.set_lock_lookahead(scheduler)
    step.set_lock_lookahead(scheduler)
    if clock_lattice then
      clock_lattice.advance = function(pulse) scheduler:serve(pulse) end
    end
  else
    m_clock.set_lock_lookahead(nil)
    step.set_lock_lookahead(nil)
    if clock_lattice then clock_lattice.advance = nil end
  end
end

function m_clock.get_lock_contract()
  return m_midi.get_lock_contract()
end

function m_clock.get_lock_lookahead()
  return m_clock.lookahead_scheduler
end

-- Whole pulses of lead at this tempo, rounded up so the value is never sent
-- with less lead than was asked for. Cached because the tempo rarely changes.
local function lead_in_pulses(tempo, lead_ms)
  if tempo ~= cached_tempo or lead_ms ~= cached_lead_ms then
    cached_tempo, cached_lead_ms = tempo, lead_ms
    cached_lead_pulses = math.ceil(lead_ms * tempo * ppqn / 60000)
  end
  return cached_lead_pulses
end

-- Resolve the next step's MIDI values now and hold them against an earlier
-- pulse. Called once a step's note has gone out, so previewing never delays a
-- note. The conditions the projection asserts are tested first rather than
-- caught, so an unsupported clock costs a few comparisons and simply keeps the
-- existing timing for that channel.
local function schedule_lookahead(clock, channel, channel_number, current_step)
  local lookahead_scheduler = m_clock.lookahead_scheduler
  if lookahead_scheduler == nil or channel_number == 17 or channel.mute then return end
  if not (clock.phase >= 1 and clock.phase < 2 and clock.shuffle_updated and
      not clock.division_for_cycle and clock.delay == 0 and not clock.delay_new) then
    return
  end

  -- Without a tempo there is no way to say how many pulses a lead is worth, and
  -- at lead zero there is nothing to advance. Either way the channel simply
  -- keeps the timing it already has.
  local tempo, lead_ms = params:get("clock_tempo"), m_midi.get_lead_time()
  if type(tempo) ~= "number" or type(lead_ms) ~= "number" or lead_ms <= 0 then return end

  local ahead = clock:project_onset_pulses(1)
  local transport = clock_lattice.transport
  local next_onset = transport + ahead
  local send_pulse = next_onset - lead_in_pulses(tempo, lead_ms)
  -- A value may not cross the note before it, so halfway between this onset and
  -- the next is the earliest it may leave. At fast divisions this is what
  -- shortens the lead rather than letting the ordering break.
  local midpoint = transport + math.ceil(ahead / 2)
  if send_pulse < midpoint then send_pulse = midpoint end
  if send_pulse <= transport or send_pulse >= next_onset then return end

  local start_trig = fn.calc_grid_count(channel.start_trig[1], channel.start_trig[2])
  local end_trig = fn.calc_grid_count(channel.end_trig[1], channel.end_trig[2])
  local next_step = step_cursor.next(current_step, false, start_trig, end_trig,
    program.get_selected_song_pattern().global_pattern_length)

  -- Only a step that would resolve parameters is previewed, so the lookahead
  -- never speaks for a step that playback would pass over.
  local has_trig = channel.working_pattern.trig_values[next_step] == 1
  local trigless = not has_trig and fn.param_value("trigless_locks") == 2
  if not (has_trig or (trigless and program.step_has_param_trig_lock(channel, next_step))) then
    return
  end

  local bundles = parameter_preview.midi_bundles(step.preview_view(channel), next_step)
  for index = 1, #bundles do
    local bundle = bundles[index]
    if bundle.send then lookahead_scheduler:schedule(send_pulse, bundle) end
  end
end

local delayed_ids_must_execute = {[0] = {}}
for i = 1, 16 do delayed_ids_must_execute[i] = {} end

local destroy_at_note_end_ids = {[0] = {}}
for i = 1, 16 do destroy_at_note_end_ids[i] = {} end


local execute_at_note_end_ids = {[0] = {}}
for i = 1, 16 do execute_at_note_end_ids[i] = {} end

local execute_spread_actions = {}
local spread_actions = {}
local spread_action_count = 0

local clock_divisions = include("mosaic/lib/clock/divisions").clock_divisions

-- Localizing math and table functions for performance
local insert = table.insert
local pairs, ipairs = pairs, ipairs
local program = program
local table = table
local floor = math.floor
local min = math.min
local max = math.max

-- Define quantize_value function first
function m_clock.quantize_value(value, quant)
  if not quant or quant == 0 then return value end
  
  -- For fractional quantization
  if quant < 1 then
    -- Calculate how many decimal places we need based on quant
    local decimals = -math.floor(math.log10(quant))
    local multiplier = 10^decimals
    -- Round to the nearest quant step using integer math for precision
    local scaled = math.floor(value * multiplier + 0.5)
    local quant_scaled = math.floor(quant * multiplier + 0.5)
    local steps = math.floor(scaled / quant_scaled + 0.5)
    return (steps * quant_scaled) / multiplier
  end
  
  -- For integer quantization
  return math.floor(value/quant + 0.5) * quant
end

local slides = include("mosaic/lib/clock/slide_lifetime").new(function() return m_clock end, program, function() return clock_lattice end)

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

local function execute_ids(c, ids)
  if not ids or #ids == 0 then return end  -- Early exit if empty/nil
  
  local clock = m_clock["channel_" .. c .. "_clock"]
  local delayed_actions = clock and clock.delayed_actions
  if not delayed_actions then return end  -- Early exit if no actions
  
  local len = #ids
  for i = len, 1, -1 do -- Reverse iteration for stable removal
    local id = ids[i]
    local delayed_action = delayed_actions[id]
    
    if delayed_action then
      local action = delayed_action.action
      if type(action) == "function" then action() end
      delayed_actions[id] = nil
      ids[i] = nil -- Direct removal since iterating in reverse
    end
  end
end

-- The three release lists are never reassigned (init replaces their channel entries).
local release_id_lists = {delayed_ids_must_execute, destroy_at_note_end_ids, execute_at_note_end_ids}

local function construct_remove_id_from_all_lists_for_channel(chan)
  local c = chan
  return function(id)
    for _, list in ipairs(release_id_lists) do
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
    swing = program.get_effective_swing(channel),
    swing_or_shuffle = program.get_effective_swing_shuffle_type(channel),
    shuffle_basis = program.get_effective_shuffle_basis(channel),
    shuffle_feel = program.get_effective_shuffle_feel(channel),
    shuffle_amount = program.get_effective_shuffle_amount(channel)
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

local arps = include("mosaic/lib/clock/arp_lifetime").new(function() return m_clock end, program, function() return clock_lattice end, get_shuffle_values, chord_timing)

local function count_active_actions(action)
  local count = 0
  for _, channel_actions in pairs(action) do
    for _, trig_action in pairs(channel_actions) do
      if trig_action.active then
        count = count + 1
      end
    end
  end
  return count
end

local transport = include("mosaic/lib/clock/transport_lifecycle").new {
  get_clock = function() return m_clock end,
  get_lattice = function() return clock_lattice end,
  set_lattice = function(value) clock_lattice = value end,
  reset_first_run = function() first_run = true end,
  program = program,
  prepare_start = function() m_clock.prepare_start() end,
  midi_patch_recall = midi_patch_recall,
  midi_output_transport = midi_output_transport,
  drain_releases = function()
    for c = 1, 16 do
      execute_ids(c, delayed_ids_must_execute[c])
      if execute_at_note_end_ids[c] then
        execute_ids(c, execute_at_note_end_ids[c])
        execute_at_note_end_ids[c] = {}
      end
    end
  end,
}

function m_clock.init()
  -- Stop clears the native subscription before re-entering reset/init, so the
  -- old callbacks cannot retain a replaced lattice or its held voices.
  if transport.stop_if_subscribed() then return end
  local program_data = program.get()
  clock_lattice = lattice:new({
    enabled = false,
    ppqn = ppqn,
  })
  if m_midi and m_midi.begin_output_batch then
    clock_lattice.output = {begin = m_midi.begin_output_batch, flush = m_midi.flush_output_batch,
                            serve = m_midi.serve_delayed}
  end
  if m_clock.lookahead_scheduler then
    clock_lattice.advance = function(pulse) m_clock.lookahead_scheduler:serve(pulse) end
  end

  if testing then
    clock_lattice.auto = false
  end

  spread_actions = {}

  clock_lattice.pattern_length = program.get_selected_song_pattern().global_pattern_length

  arps.destroy_all()

  for i = 1, 16 do 
    delayed_ids_must_execute[i] = {}
    destroy_at_note_end_ids[i] = {}
    execute_at_note_end_ids[i] = {}
    arps.reset_channel(i)
  end


  master_clock = clock_lattice:new_sprocket {
    action = function(t)
      local selected_song_pattern = program_data.song_patterns[program_data.selected_song_pattern]
      if params:get("elektron_program_changes") == 2 and selected_song_pattern.global_pattern_length >= 3 and
        program_data.current_step == selected_song_pattern.global_pattern_length - 1 then
        step.process_elektron_program_change(step.calculate_next_selected_song_pattern())
      end
      if not first_run then
        step.process_song_song_patterns(program_data.current_step)
        selected_song_pattern = program_data.song_patterns[program_data.selected_song_pattern]
        -- Each channel applies the global length cap relative to its own start
        -- on its own clock. Absolute-step resets here truncate offset ranges.
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

  -- Lengths 1 and 2 leave no room for the two-step lead above: announce the next slot on the
  -- slot's final step, after that step's notes (arbitrated 2026-09-11, SEM-013
  -- final-step-short-lengths). The master has already advanced, so current_step is 1 exactly
  -- when the step that began on this pulse was the last, and the next slot is computed from
  -- the state the next pulse's song switch will read.
  clock_lattice:new_sprocket {
    action = function(t)
      if params:get("elektron_program_changes") == 2 and program_data.current_step == 1 and
        program.get_selected_song_pattern().global_pattern_length < 3 then
        step.process_elektron_program_change(step.calculate_next_selected_song_pattern())
      end
    end,
    division = 1 / 16,
    swing = 0,
    swing_or_shuffle = 1,
    shuffle_basis = 0,
    shuffle_feel = 0,
    shuffle_amount = 0,
    order = 4,
    realign = false,
    enabled = true
  }

  local channel_edit_page = pages.pages.channel_edit_page
  local scale_edit_page = pages.pages.scale_edit_page
  for channel_number = 17, 1, -1 do
    local div = calculate_divisor(program.get_channel(program.get().selected_song_pattern, channel_number).clock_mods)

    -- Build the clock's key once per channel instead of on every step.
    local clock_key = "channel_" .. channel_number .. "_clock"

    -- Declared before the channel action, which runs it at the next onset.
    local end_of_clock_action
    local finish_step

    local sprocket_action = function(t)
      local song_pattern = program.get().selected_song_pattern
      local channel = program.get_channel(song_pattern, channel_number)
      local current_step = program.get_current_step_for_channel(channel_number)
      local pattern = channel.working_pattern
      local trig_values = pattern.trig_values
      local clock = m_clock[clock_key]
      
      -- Cache frequently accessed values
      local start_trig = fn.calc_grid_count(channel.start_trig[1], channel.start_trig[2])
      local end_trig = fn.calc_grid_count(channel.end_trig[1], channel.end_trig[2])
      
      local selected_step, wrapped = step_cursor.next(current_step, m_clock[clock_key].first_run,
        start_trig, end_trig, program.get_selected_song_pattern().global_pattern_length)
      if selected_step ~= current_step or not m_clock[clock_key].first_run then
        program.set_current_step_for_channel(channel_number, selected_step)
      end
      current_step = selected_step

      if wrapped then
        
        -- The global scale channel has no MIDI parameter recorder bank.
        if channel_number ~= 17 and params:get("record") == 2 and program.get_selected_channel() == channel then
          for i = 1, 10 do
            recorder.clear_trig_lock_dirty(channel_number, i)
          end
        end
      end

      -- Only a track channel on an empty step can record trigless locks.
      local trigless_locks = false
      if channel_number == 17 then
        program_data.current_scale_channel_step = current_step
        step.process_global_step_scale_trig_lock(current_step)
        step.sinfonian_sync(current_step)
      else
        program.set_channel_step_scale_number(channel_number, step.calculate_step_scale_number(channel_number, current_step))
        -- This step's trig and the trigless-lock setting decide every branch below.
        local has_trig = channel.working_pattern.trig_values[current_step] == 1
        trigless_locks = not has_trig and fn.param_value("trigless_locks") == 2
        -- Recording includes empty trigless steps as well as active trigs.
        if has_trig or trigless_locks then
          step.process_recording_params(channel)
        end
        -- Resolve parameters for the same step as the note, including startup.
        -- A single dispatch site prevents duplicate first-step lock messages.
        if has_trig or (trigless_locks and program.step_has_param_trig_lock(channel, current_step)) then
          local probe = _G.mosaic_pulse_probe
          if probe then probe:record(2, probe.pulse, channel_number, 0, 1) end
          step.process_params(channel, current_step)
          if probe then probe:record(2, probe.pulse, channel_number, 0, 2) end
        end

        -- A step's parameter locks shape its note, so they must precede it, but
        -- they need not wait behind another channel's note. The lattice sounds
        -- this note once every channel on this pulse has sent its locks, then
        -- finishes the step, before this channel's clock moves past the onset.
        if has_trig then
          clock.note_pending = current_step
          clock.pending_note = step.prepare_note(channel_number, current_step)
          clock.pending_channel = channel
          clock.pending_song_pattern = song_pattern
          return
        end
      end

      finish_step(clock, channel, current_step, false, trigless_locks, song_pattern)
    end

    finish_step = function(clock, channel, current_step, has_trig, trigless_locks, song_pattern)
      if has_trig or trigless_locks then
        if fn.param_value("record") == 2 and program.get_selected_channel() == channel then
          for i = 1, 10 do
            recorder.record_trig_event(channel_number, current_step, i, song_pattern)
          end
        end
      end

      -- The end-of-clock work used to live in a second sprocket per channel,
      -- delayed a whole cycle so that it ran at this onset, just after it.
      -- Running it here instead removes seventeen sprockets from every pulse.
      if not clock.first_run then
        end_of_clock_action()
      end

      clock.first_run = false
      clock.next_step = current_step

      -- This step is finished and its note has gone. Resolve the next step's
      -- values now so they can leave in an earlier pulse than their own.
      if m_clock.lookahead_scheduler then
        m_clock.lookahead_scheduler:clear_commit(channel_number, current_step)
        schedule_lookahead(clock, channel, channel_number, current_step)
      end

      if program_data.selected_channel == channel_number and (program_data.selected_page == channel_edit_page or program_data.selected_page == scale_edit_page)  then
        fn.dirty_grid(true)
      end
    end

    -- Only the recorder reads anything here, so test the cheapest conditions
    -- first: the global scale channel has no bank, then the record setting,
    -- then the selected channel. The end trig is only needed after a wrap.
    end_of_clock_action = function(t)
      if channel_number == 17 or fn.param_value("record") ~= 2 then return end

      local channel = program.get_channel(program.get().selected_song_pattern, channel_number)
      if program.get_selected_channel() ~= channel then return end

      local last_step = program.get_current_step_for_channel(channel_number) - 1
      if last_step < 1 then
        last_step = fn.calc_grid_count(channel.end_trig[1], channel.end_trig[2])
      end

      recorder.record_stored_note_mask_events(channel_number, last_step)
      scheduler.debounce(function()
        channel_edit_page_ui.refresh_memory()
      end)()
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

    m_clock["channel_" .. channel_number .. "_clock"].note_action = function(sprocket)
      local prepared = sprocket.pending_note
      sprocket.pending_note = nil
      step.handle(channel_number, sprocket.note_pending, prepared)
    end

    m_clock["channel_" .. channel_number .. "_clock"].after_note_action = function(sprocket)
      local current_step, channel, song_pattern = sprocket.note_pending, sprocket.pending_channel, sprocket.pending_song_pattern
      sprocket.note_pending, sprocket.pending_channel, sprocket.pending_song_pattern = nil, nil, nil
      finish_step(sprocket, channel, current_step, true, false, song_pattern)
    end

    m_clock["channel_" .. channel_number .. "_clock"].first_run = true

  end
  execute_spread_actions = clock_lattice:new_sprocket {
    action = slides.process,
    division = 1/48,
    enabled = true,
    realign = false,
    order = 5
  }

  slides.reset()
end

-- Apply the final stopped timing settings to the clean lattice prepared by
-- init/reset. Realignment resets fractional carry and phase without rebuilding
-- every sprocket on the MIDI Start callback's first-clock deadline.
function m_clock.prepare_start()
  if not clock_lattice then return m_clock.init() end
  local song_pattern = program.get().selected_song_pattern
  clock_lattice.pattern_length = program.get_selected_song_pattern().global_pattern_length
  for channel_number = 1, 17 do
    local channel = program.get_channel(song_pattern, channel_number)
    local division = 1 / (calculate_divisor(channel.clock_mods) * 4)
    local shuffle = get_shuffle_values(channel)
    local channel_clock = m_clock["channel_" .. channel_number .. "_clock"]
    for _, sprocket in ipairs({channel_clock}) do
      sprocket:set_division(division)
      sprocket:set_swing(shuffle.swing or 0)
      sprocket:set_swing_or_shuffle(shuffle.swing_or_shuffle or 1)
      sprocket:set_shuffle_basis(shuffle.shuffle_basis or 0)
      sprocket:set_shuffle_feel(shuffle.shuffle_feel or 0)
      sprocket:set_shuffle_amount(shuffle.shuffle_amount or 0)
    end
  end
  clock_lattice:prepare_for_start()
  slides.reset()
  -- A device that was left holding a value while the transport was stopped may
  -- have been changed by hand; start by sending each slot again.
  step.forget_sent_lock_values()
end



local retime_channel_slides = slides.retime

function m_clock.set_swing_shuffle_type(channel_number, swing_or_shuffle)
  local clock = m_clock["channel_" .. channel_number .. "_clock"]
  local previous = clock.swing_or_shuffle
  clock:set_swing_or_shuffle((swing_or_shuffle or 0))
  if clock.swing_or_shuffle ~= previous then retime_channel_slides(channel_number, clock) end
end

function m_clock.set_channel_swing(channel_number, swing)
  local clock = m_clock["channel_" .. channel_number .. "_clock"]
  local previous = clock.swing
  clock:set_swing(swing or 0)
  if clock.swing ~= previous then retime_channel_slides(channel_number, clock) end
end

function m_clock.set_channel_shuffle_feel(channel_number, shuffle_feel)
  local clock = m_clock["channel_" .. channel_number .. "_clock"]
  local previous = clock.shuffle_feel
  clock:set_shuffle_feel((shuffle_feel or 0))
  if clock.shuffle_feel ~= previous then retime_channel_slides(channel_number, clock) end
end

function m_clock.set_channel_shuffle_basis(channel_number, shuffle_basis)
  local clock = m_clock["channel_" .. channel_number .. "_clock"]
  local previous = clock.shuffle_basis
  clock:set_shuffle_basis((shuffle_basis or 0))
  if clock.shuffle_basis ~= previous then retime_channel_slides(channel_number, clock) end
end

function m_clock.set_channel_shuffle_amount(channel_number, shuffle_amount)
  local clock = m_clock["channel_" .. channel_number .. "_clock"]
  local previous = clock.shuffle_amount
  clock:set_shuffle_amount(shuffle_amount or 0)
  if clock.shuffle_amount ~= previous then retime_channel_slides(channel_number, clock) end
end

function m_clock.set_channel_division(channel_number, division)
  local clock = m_clock["channel_" .. channel_number .. "_clock"]
  local previous = clock.division
  local div_value = 1 / (division * 4)
  clock:set_division(div_value)
  if clock.division ~= previous then retime_channel_slides(channel_number, clock) end
end

function m_clock.get_channel_division(channel_number)
  local clock = m_clock["channel_" .. channel_number .. "_clock"]
  return clock and clock.division or 0.4
end

function m_clock.get_destroy_at_note_end_ids_length(channel)
  return #destroy_at_note_end_ids[channel]
end

-- Every note release is scheduled here; build each channel's clock key once.
local delay_clock_keys = {}

function m_clock.delay_action(c, length, type, func, before_onset, defer_zero)
  if (length == 0 or length == nil) and not defer_zero then
    func()
    return
  end

  local key = delay_clock_keys[c]
  if not key then
    key = "channel_" .. c .. "_clock"
    delay_clock_keys[c] = key
  end
  local id = m_clock[key]:set_delayed_action(length, func, before_onset)

  if type == "must_execute" then
    table.insert(delayed_ids_must_execute[c], id)
  elseif type == "destroy_at_note_end" then
    table.insert(destroy_at_note_end_ids[c], id)
  elseif type == "execute_at_note_end" then
    table.insert(execute_at_note_end_ids[c], id)
  end

  -- Return the id so it can be cancelled if needed
  return id
end

function m_clock.destroy_at_note_end_ids(c)
  local clock = m_clock["channel_" .. c .. "_clock"]
  if not (clock and clock.delayed_actions) then return end
  
  local ids = destroy_at_note_end_ids[c]
  local i = #ids
  
  while i > 0 do
    local id = ids[i]
    if clock.delayed_actions[id] then
      -- Prevent execution by making it a no-op and setting length to never trigger
      clock.delayed_actions[id].action = function() end
      clock.delayed_actions[id].length = math.huge
    end
    -- Use swap-and-pop for O(1) removal from ids list
    if i < #ids then
      ids[i] = ids[#ids]
    end
    ids[#ids] = nil
    i = i - 1
  end
end

m_clock.cancel_arp_onsets = arps.cancel_onsets
m_clock.new_arp_sprocket = arps.start

function m_clock.realign_sprockets()
  clock_lattice:realign_eligable_sprockets()
  slides.realign()
end

m_clock.cancel_all_spread_actions = slides.cancel_all

function m_clock.execute_action_across_steps_by_pulses(args)
  local distance = args.distance
  -- Equal labels alone mean no movement. A next-loop occurrence carries
  -- an explicit positive distance from the destination lookup.
  if distance == nil and args.start_step == args.end_step then return end
  if not distance then
    local channel = program.get_channel(program.get().selected_song_pattern, args.channel_number)
    local first, last = program.get_channel_step_bounds(channel)
    distance = args.end_step - args.start_step
    if args.should_wrap and distance <= 0 then distance = distance + last - first + 1 end
  end
  if distance <= 0 then return end
  local chan_clock = m_clock["channel_" .. args.channel_number .. "_clock"]
  local total_pulses = chan_clock:project_onset_pulses(distance)

  -- Cancel existing actions for this channel/trig_lock
  m_clock.cancel_spread_actions_for_channel_trig_lock(args.channel_number, args.trig_lock)
  
  -- Push new action to ring buffer
  slides.push({
    channel = args.channel_number,
    trig_lock = args.trig_lock,
    pulse_count = 0,
    total_pulses = total_pulses,
    start_pulse = clock_lattice.transport,
    end_step = args.end_step,
    end_occurrence = (chan_clock.onset_count or 0) + distance,
    start_value = args.start_value,
    last_value = args.start_value, -- Initial lock already emitted this value.
    end_value = args.end_value,
    quant = args.quant,
    func = args.func,
    active = true
  })
end

m_clock.handoff_spread_lock = slides.handoff
-- Read-only: reports what handoff would do, for the lock preview.
m_clock.spread_lock_would_handoff = slides.would_handoff
m_clock.cancel_spread_actions_for_channel_trig_lock = slides.cancel
m_clock.channel_is_sliding = slides.is_active

m_clock.start = transport.start
m_clock.stop = transport.stop
m_clock.is_playing = transport.is_playing
m_clock.set_playing = transport.set_playing
m_clock.reset = transport.reset

function m_clock.panic()
  m_midi.panic()
end

function m_clock.get_clock_divisions()
  return clock_divisions
end

function m_clock.get_clock_lattice()
  return clock_lattice
end

-- Seconds until the next master step onset, or nil when not playing or unknown.
-- Screen redraws use this to stay clear of a step's note processing.
function m_clock.seconds_to_next_step()
  if not (clock_lattice and clock_lattice.enabled and master_clock and master_clock.enabled) then return nil end
  local period = master_clock.current_ppqn
  local phase = master_clock.phase
  if type(period) ~= "number" or type(phase) ~= "number" or period < 1 then return nil end
  local tempo = clock.get_tempo()
  if type(tempo) ~= "number" or tempo <= 0 then return nil end
  local pulses = period - phase + 1
  if pulses < 0 then pulses = 0 end
  return pulses * 60 / (tempo * ppqn)
end

return m_clock



