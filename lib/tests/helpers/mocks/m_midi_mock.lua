m_midi = {}
m_midi.start = function() end
m_midi.has_device = function() return true end

-- The lock lead contract and lead time, so tests can exercise lookahead. The
-- production module owns these; the mock only has to answer the same questions.
local lead_time_ms = 0
local lock_contract = "legacy-delay-v1"
function m_midi.get_lead_time() return lead_time_ms end
function m_midi.set_lead_time(value) lead_time_ms = value end
function m_midi.get_lock_contract() return lock_contract end
function m_midi.set_lock_contract(value) lock_contract = value end

local function log(kind, a, b, c)
  if midi_event_log == nil then midi_event_log = {} end
  local transport = 0
  if type(clock_lattice) == "table" and type(clock_lattice.transport) == "number" then
    transport = clock_lattice.transport
  end
  table.insert(midi_event_log, {kind = kind, a = a, b = b, c = c, pulse = transport})
end

function m_midi:note_on(note, velocity, channel, device, _, on_emitted)
  table.insert(midi_note_on_events, {note, velocity, channel, device})
  log("note_on", note, velocity, channel)
  if on_emitted then on_emitted(note)end
  return true
end

function m_midi:note_off(note, velocity, channel, device)
  table.insert(midi_note_off_events, {note, velocity, channel, device})
end

-- The production write path reports every parameter write to this listener;
-- the mock answers the same way so lookahead sees a control turned in a test.
m_midi.parameter_write_listener = nil
function m_midi.set_parameter_write_listener(listener)
  m_midi.parameter_write_listener = listener
end

function m_midi.cc(cc_msb, cc_lsb, value, channel, device)
  table.insert(midi_cc_events, {cc_msb, value, channel})
  log("cc", cc_msb, value, channel)
  local listener = m_midi.parameter_write_listener
  if listener then listener("cc", device, channel or 1, cc_msb) end
end
