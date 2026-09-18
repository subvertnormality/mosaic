m_midi = {}
m_midi.start = function() end

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

function m_midi:note_on(note, velocity, channel, device)
  table.insert(midi_note_on_events, {note, velocity, channel, device})
  log("note_on", note, velocity, channel)
end

function m_midi:note_off(note, velocity, channel, device)
  table.insert(midi_note_off_events, {note, velocity, channel, device})
end

function m_midi.cc(cc_msb, cc_lsb, value, channel, device)
  table.insert(midi_cc_events, {cc_msb, value, channel})
  log("cc", cc_msb, value, channel)
end