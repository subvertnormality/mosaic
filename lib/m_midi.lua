
local step = include("mosaic/lib/step")
local quantiser = include("mosaic/lib/quantiser")
local divisions = include("mosaic/lib/clock/divisions")

local m_midi = {}

-- norns builds two tables for every message it sends: the message, then its
-- bytes. A step sends a hundred messages, so write the bytes into one reused
-- table and hand them to the port's device, which sends them as one write
-- exactly as it would have. The table is read before send returns. A port
-- without a norns MIDI device behind it (a test double, a disconnected port)
-- keeps its own methods.
local wire_bytes = {0, 0, 0}

local function device_for_bytes(port)
  local device = port.device
  if device ~= nil and getmetatable(device) ~= nil and type(device.send) == "function" then
    return device
  end
end

-- While the clock runs a pulse, messages for one device are gathered and sent
-- as one write at the points the pulse marks (after its releases, after its
-- parameter locks, and at its end), in the order they were produced. Every
-- write is a system call on the CM3+, and a busy step made a hundred of them
-- before its notes could leave. Any other send to a port first sends what is
-- gathered, so the order of messages on a port never changes.
local delay_queue
local batching = false
local batches = {}
local batch_devices = {}

function m_midi.begin_output_batch()
  m_midi.flush_output_batch()
  batching = true
  -- begin() also sends anything already overdue, ahead of what this pulse
  -- produces: the rescue for a deadline that passed unserved.
  if delay_queue then delay_queue:begin() end
end

-- Serve deadlines that fall inside a pulse's work, at the seams between its
-- channels. What is sent only leaves on a write, so write it: holding it for
-- the batch at the end of the pulse is the wait this exists to avoid. A seam
-- with nothing due costs one comparison and no write.
function m_midi.serve_delayed()
  if delay_queue and delay_queue:serve() then m_midi.flush_output_batch() end
end

function m_midi.flush_output_batch(stop)
  for i = 1, #batch_devices do
    local device = batch_devices[i]
    local bytes = batches[device]
    batches[device] = nil
    batch_devices[i] = nil
    local probe = _G.mosaic_pulse_probe
    if probe then probe:record(4, probe.pulse, i, 0, 1, #bytes, 1) end
    device:send(bytes)
    if probe then probe:record(4, probe.pulse, i, 0, 2, #bytes, 1) end
  end
  if stop then
    batching = false
    if delay_queue then delay_queue:finish() end
  end
end

function m_midi.send_three(port, status, data1, data2)
  local device = device_for_bytes(port)
  if not device then return false end
  if batching then
    local bytes = batches[device]
    if not bytes then
      bytes = {}
      batches[device] = bytes
      batch_devices[#batch_devices + 1] = device
    end
    local n = #bytes
    bytes[n + 1], bytes[n + 2], bytes[n + 3] = status, data1, data2
    return true
  end
  wire_bytes[1], wire_bytes[2], wire_bytes[3] = status, data1, data2
  local probe = _G.mosaic_pulse_probe
  if probe then probe:record(4, probe.pulse, 0, 0, 1, 3, 1) end
  device:send(wire_bytes)
  if probe then probe:record(4, probe.pulse, 0, 0, 2, 3, 1) end
  return true
end

-- Delayed messages capture the physical connection: reconnecting a vport must
-- not send an old queued onset to a newly attached receiver.
local delay_line = include("mosaic/lib/clock/midi_delay_line")
local lead_time_ms=0
-- Lock lead is achieved by sending the locks early, never by delaying anything.
-- The delaying path remains only so a measurement can run the old behaviour as a
-- control; it is not a product setting and nothing in the app selects it.
local lock_contract="pulse-advance"
function m_midi.get_lock_contract() return lock_contract end
function m_midi.set_lock_contract(value)
  if value~="legacy-delay-v1" and value~="pulse-advance" then
    error("Unsupported lock lead contract: "..tostring(value))
  end
  if delay_queue then delay_queue:drain() end
  lock_contract=value
end
local function emit(message)
  local port=message.port
  if port.device ~= message.device then return end
  if message.method then
    m_midi.flush_output_batch()
    message.method(port,table.unpack(message.args))
  elseif not m_midi.send_three(port,message.status,message.note,message.velocity) then
    m_midi.flush_output_batch()
    port[message.kind](port,message.note,message.velocity,message.channel)
  end
end
local function queue(ms,message)
  if not delay_queue then
    -- Subtract the epoch before adding milliseconds: adding 0.005 to Unix
    -- wall time loses fractions of a microsecond through float cancellation.
    local origin=util.time()
    delay_queue=delay_line.new({now=function() return util.time()-origin end,
      probe_deadline=function(due) return origin + due end,
      resolution=0.000001,
      begin=function() m_midi.begin_output_batch() end,
      flush=function() m_midi.flush_output_batch(true) end,send=emit})
    if batching then delay_queue:begin() end
  end
  return delay_queue:push(ms,message)
end

-- README Lock lead time: a parameter value normally leaves at its step time,
-- lead ms ahead of its note. When notes on one MIDI channel are closer together
-- than twice the lead, a value sent at step time would change the receiver
-- during the previous note's attack, or before that note even sounds. The value
-- then waits until halfway between the previous note-on and its own note-on, so
-- each note keeps its own value for half the gap and the next value settles in
-- the other half. Only times already known are used: the previous note's
-- deadline and this value's own note deadline (now plus the lead).
local last_note_due = {}
local last_held_due = {}
local function forget_note_deadlines()
  last_note_due = {}
  last_held_due = {}
end
local function remember(by_port, port, channel, due)
  local channels = by_port[port]
  if not channels then channels = {}; by_port[port] = channels end
  channels[channel] = due
end
function m_midi.parameter_deadline(port, channel)
  -- Under pulse-advance a value's lead comes from leaving in an earlier pulse,
  -- so nothing is held back here. This spacing rule belongs to the old contract
  -- and applies only when that is being measured as a control.
  if lock_contract == "pulse-advance" then return nil end
  if lead_time_ms == 0 or not delay_queue then return nil end
  channel = channel or 1
  local now = delay_queue:now()
  -- Measure from the step's pulse, as its note is: a stall inside the pulse
  -- must not move the value later than the note it belongs to.
  local heard = delay_queue:time() + lead_time_ms / 1000
  local due = now
  local notes = last_note_due[port]
  local previous = notes and notes[channel]
  if previous then
    local midpoint = (previous + heard) / 2
    if midpoint > due then due = midpoint end
  end
  -- A held value is never overtaken by a later one on the same channel.
  local held = last_held_due[port]
  held = held and held[channel]
  if held and held > due then due = held end
  if due <= now + 0.000001 then return nil end
  remember(last_held_due, port, channel, due)
  return due
end
function m_midi.hold_parameter(due, port, status, data1, data2, channel)
  delay_queue:push_at(due, {port=port, device=port.device, kind="cc", note=data1,
    velocity=data2, channel=channel, status=status})
end

local function delayed_note(ms,port,kind,note,velocity,channel)
  -- Under pulse-advance a note is never delayed: its lead comes from the locks
  -- having left earlier, so the note keeps the timing it has at lead 0.
  if not ms or ms==0 or lock_contract=="pulse-advance" then return false end
  local due=queue(ms,{port=port,device=port.device,kind=kind,note=note,velocity=velocity or 100,
    channel=channel,status=(kind=="note_on" and 0x90 or 0x80)+(channel or 1)-1})
  if kind=="note_on" then remember(last_note_due, port, channel or 1, due) end
  return true
end
function m_midi.drain_pending_output()
  if delay_queue then delay_queue:drain() end
  forget_note_deadlines()
end

-- Told of every parameter write as it reaches the wire: kind ("cc" or "nrpn"),
-- port, MIDI channel and the CC number or NRPN address. Lock lookahead installs
-- it so a write from anywhere else can retire a value it sent early; with none
-- installed a write costs one nil test.
m_midi.parameter_write_listener = nil
function m_midi.set_parameter_write_listener(listener)
  m_midi.parameter_write_listener = listener
end

-- Cache the global setting through its params action; zero keeps the original
-- send path and allocates no timer. Captured note containers retain gate timing.
function m_midi.get_lead_time() return lead_time_ms end
function m_midi.set_lead_time(value)
  if delay_queue then delay_queue:close();delay_queue=nil end
  forget_note_deadlines()
  lead_time_ms=value
end
local clock_hooks={}
function m_midi.install_clock_hooks()
  for id,port in ipairs(midi.vports) do
    for _,name in ipairs({"clock","start","continue","stop","song_position"}) do
      local original=port[name]
      if type(original)=="function" then
        local wrapper
        wrapper=function(self,...)
          local ms=lead_time_ms
          if name=="stop" then m_midi.drain_pending_output() end
          -- Pulse-advance adds no latency to clock or transport either.
          if ms==0 or lock_contract=="pulse-advance" then return original(self,...) end
          queue(ms,{port=self,device=self.device,method=original,args={...}})
        end
        clock_hooks[#clock_hooks+1]={port=port,name=name,original=original,wrapper=wrapper}
        port[name]=wrapper
      end
    end
  end
end
function m_midi.cleanup()
  -- With zero lead the old script emitted nothing during unload. Only an
  -- allocated delay line needs transport/release cleanup before core frees
  -- script clocks and metros; restoring hooks itself must not send MIDI.
  if delay_queue then
    m_midi.stop()
    delay_queue:close();delay_queue=nil
    forget_note_deadlines()
  end
  for _,hook in ipairs(clock_hooks) do
    if hook.port[hook.name]==hook.wrapper then hook.port[hook.name]=hook.original end
  end
  clock_hooks={}
end

midi_devices = {}
m_midi.note_counts = {}  -- Initialize note counts table

local chord_number = 0
local midi_input = include("mosaic/lib/devices/midi_input")
local midi_ingress = midi_input.new(m_midi, step, quantiser, divisions)

handle_midi_event_data = function(data, midi_device)
  return midi_ingress.handle(data, midi_device)
end


function m_midi.init()
  m_midi.install_clock_hooks()
  for i = 1, #midi.vports do
    midi_devices[i] = midi.connect(i)
    midi_devices[i].event = function(data) 
      handle_midi_event_data(data, midi_devices[i])
    end
  end

end

function m_midi.get_midi_outs()
  local midi_outs = {}
  for i = 1, #midi.vports do
    if midi_devices[i] and midi_devices[i].name ~= "none" and midi_devices[i].name ~= "Norns2sinfonion" then
      table.insert(
        midi_outs,
        {name = "OUT " .. i, value = i, long_name = util.trim_string_to_width(midi_devices[i].name, 80)}
      )
    end
  end

  return midi_outs
end


function m_midi.send_to_sinfonion(command, value)
  for id = 1, #midi_devices do

    if midi_devices[id] and midi_devices[id].name == "Norns2sinfonion" then
      m_midi.flush_output_batch()
      midi_devices[id]:program_change(value, command)
    end
  end
end

function m_midi:reset_note_counts()
  for device = 1, #midi_devices do
    self.note_counts[device] = nil
  end
end


function m_midi:note_on(note, velocity, channel, device, lead_time_ms)
  if lead_time_ms == nil then lead_time_ms=m_midi.get_lead_time() end
  if midi_devices[device] ~= nil then
    -- Composed scale/chord/merge/octave operations may exceed MIDI's
    -- seven-bit note domain. Normalize at the final MIDI-only boundary.
    note = fn.constrain(0, 127, note)
    -- Initialize tables if necessary
    if not self.note_counts[device] then
      self.note_counts[device] = {}
    end
    if not self.note_counts[device][channel] then
      self.note_counts[device][channel] = {}
    end
    if not self.note_counts[device][channel][note] then
      self.note_counts[device][channel][note] = 0
    end

    -- Increment the note count
    self.note_counts[device][channel][note] = self.note_counts[device][channel][note] + 1

    -- Send the Note On message
    local port = midi_devices[device]
    if not delayed_note(lead_time_ms, port, "note_on", note, velocity, channel) and not m_midi.send_three(port, 0x90 + (channel or 1) - 1, note, velocity or 100) then
      m_midi.flush_output_batch()
      port:note_on(note, velocity, channel)
    end
  end
end

function m_midi:note_off(note, velocity, channel, device, lead_time_ms)
  if lead_time_ms == nil then lead_time_ms=m_midi.get_lead_time() end
  if midi_devices[device] ~= nil then
    -- Use the same normalized key as note_on so ownership cannot strand.
    note = fn.constrain(0, 127, note)
    -- Check if the note is currently on
    if self.note_counts[device] and self.note_counts[device][channel] and self.note_counts[device][channel][note] then
      -- Decrement the note count
      self.note_counts[device][channel][note] = self.note_counts[device][channel][note] - 1
      -- Every emitted Note On owns a Note Off, including overlapping pitches.
      -- Retain counts for bookkeeping without collapsing receiver releases.
      local port = midi_devices[device]
      if not delayed_note(lead_time_ms, port, "note_off", note, velocity, channel) and not m_midi.send_three(port, 0x80 + (channel or 1) - 1, note, velocity or 100) then
        m_midi.flush_output_batch()
        port:note_off(note, velocity, channel)
      end
      if self.note_counts[device][channel][note] <= 0 then
        -- Remove the note from the table
        self.note_counts[device][channel][note] = nil
      end
    else
      -- Note is not currently on, but we received a Note Off.
      -- For safety, send Note Off anyway
      local port = midi_devices[device]
      if not delayed_note(lead_time_ms, port, "note_off", note, velocity, channel) and not m_midi.send_three(port, 0x80 + (channel or 1) - 1, note, velocity or 100) then
        m_midi.flush_output_batch()
        port:note_off(note, velocity, channel)
      end
    end
  end
end

m_midi.cc, m_midi.nrpn = include("mosaic/lib/devices/midi_wire_output").new(m_midi)

function m_midi:program_change(program_id, channel, device)
  if midi_devices[device] ~= nil then
    m_midi.flush_output_batch()
    midi_devices[device]:program_change(program_id, channel)
  end
end

function m_midi.start()

  for id = 1, #midi.vports do
    if midi_devices[id].device ~= nil then
      m_midi.flush_output_batch()
      midi_devices[id]:start()
    end
  end

end

function m_midi:all_notes_off()
  m_midi.drain_pending_output()
  for device, channels in pairs(self.note_counts) do
    if midi_devices[device] ~= nil then
      for channel, notes in pairs(channels) do
        for note, count in pairs(notes) do
          if count > 0 then
            -- Preserve one release for every owned onset, including distinct
            -- internal notes that clamp to the same MIDI endpoint.
            for _ = 1, count do
              m_midi.flush_output_batch()
              midi_devices[device]:note_off(note, 0, channel)
            end
            self.note_counts[device][channel][note] = nil
          end
        end
        -- Clean up empty channel tables
        if next(self.note_counts[device][channel]) == nil then
          self.note_counts[device][channel] = nil
        end
      end
      -- Clean up empty device tables
      if next(self.note_counts[device]) == nil then
        self.note_counts[device] = nil
      end
    end
  end
end

-- Modify the stop function
function m_midi.stop(send_transport)
  -- Turn off all active notes
  m_midi:all_notes_off()

  -- Restart cleanup releases voices without sending Stop back to the clock
  -- source. Ordinary Stop retains its transport output on every device.
  if send_transport ~= false then
    for id = 1, #midi.vports do
      if midi_devices[id] and midi_devices[id].device ~= nil then
        m_midi.flush_output_batch()
        midi_devices[id]:stop()
      end
    end
  end

  -- Reset note counts
  m_midi.note_counts = {}
  -- Transport Stop also resets keyboard chord state, so a key whose Note Off
  -- never arrived cannot keep a step's chord open.
  midi_ingress.reset_chords()
end


local all_off_by_device = {}
function m_midi.all_off(id)
  m_midi.drain_pending_output()
  if not all_off_by_device[id] then
    all_off_by_device[id] = scheduler.debounce(function()
      for note = 0, 127 do
        m_midi.drain_pending_output()
        for channel = 1, 16 do
          m_midi.flush_output_batch()
          midi_devices[id]:note_off(note, 0, channel)
          -- Forget only notes actually cleared by this sweep position.
          -- Notes played behind it still need ownership for transport Stop.
          local channels = m_midi.note_counts[id]
          if channels and channels[channel] then
            channels[channel][note] = nil
          end
        end
        coroutine.yield()
      end
      chord_number = 0
    end)
  end
  all_off_by_device[id]()
end

function m_midi.panic()
  m_midi.drain_pending_output()
  for id = 1, #midi.vports do
    if midi_devices[id].device ~= nil then
      m_midi.all_off(id)
    end
  end
  -- Clear all note counts
  m_midi.note_counts = {}
  chord_number = 0
end

function m_midi.midi_devices_connected() 
  for id = 1, #midi.vports do
    if midi_devices[id].device ~= nil then
      return true
    end
  end
  return false
end


function m_midi.set_up_midi_mapping_params()
  return include("mosaic/lib/devices/midi_mapping_params").setup()
end

return m_midi
