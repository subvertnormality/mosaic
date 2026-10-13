-- Add a persisted Rhythm Doctor bank to a saved project, so a reload reaches
-- READY without any analysis backend. Used to build a behaviour fixture.
package.path = './lib/?.lua;' .. arg[2] .. '/?.lua;' .. package.path
local tab = dofile(arg[2] .. '/tabutil.lua')
local Bank = require('rhythm_doctor.bank')
local Persistence = require('rhythm_doctor.bank_persistence')

local path = arg[1]
local saved = assert(tab.load(path), 'could not load project')
local bank = assert(Bank.build{ project_id = 'fixture', generation = 1, analysis_revision = 1,
  sample_rate = 48000, capture_start_sample = 0, capture_end_sample = 48000 * 20,
  origin_sample = 0, bpm = 120, tempo_mode = 'auto',
  sensitivities = { BD = 0.2, SD = 0.2, CYM = 0.2 },
  candidates = {
    { lane = 'BD',   sample_index = 0,      velocity = 100, confidence = 0.9 },
    { lane = 'SD',   sample_index = 12000,  velocity = 90,  confidence = 0.8 },
    { lane = 'CYM',  sample_index = 6000,   velocity = 70,  confidence = 0.7 },
  } })
local envelope = assert(Persistence.encode(bank), 'bank did not encode')
-- The bank is serialised inside the program table, because project_lifecycle
-- hands the guard program.get() on load, not the outer saved table.
assert(type(saved[2]) == 'table', 'project has no program table to extend')
saved[2].rhythm_doctor = envelope
tab.save(saved, path)

-- Prove the round trip: the file must decode back to a ready bank.
local reread = assert(tab.load(path))
local decoded = assert(Persistence.decode(reread[2].rhythm_doctor), 'did not decode')
assert(Bank.valid_ready(decoded), 'decoded bank is not ready')
print('INJECTED ok cells=' .. tostring(decoded.timeline_cells) .. ' bpm=' .. tostring(decoded.bpm))
