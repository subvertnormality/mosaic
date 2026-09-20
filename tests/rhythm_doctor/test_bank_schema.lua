-- PLAN.md Bank lifecycle: only complete sample-authoritative banks may be READY.
-- Characterisation outside README; malformed worker/load results are not acceptance.
package.path = './lib/?.lua;' .. package.path
local Bank = require('rhythm_doctor.bank')
local function fresh()
  return assert(Bank.build{project_id='p', generation=1, analysis_revision=2,
    sample_rate=48000, capture_start_sample=0, capture_end_sample=480000,
    origin_sample=0, bpm=120, candidates={
      {lane='BD', sample_index=0, velocity=80, confidence=.9}}})
end
local failures, total = {}, 0
local cases = {
  function(b) b.sample_rate=nil end,
  function(b) b.bpm=0/0 end,
  function(b) b.timeline_cells=100000000 end,
  function(b) b.window_start=b.timeline_cells-63 end,
  function(b) b.capture_end_sample=48000*46 end,
  function(b) b.timeline_end_sample=1 end,
  function(b) b.sensitivities.BD=-1 end,
  function(b) b.lanes.BD[1].velocity=128 end,
  function(b) b.lanes.BD[1].velocity=3.5 end,
  function(b) b.lanes.BD[1].sample_index=480000 end,
  function(b) b.lanes.BD[1000]=b.lanes.BD[1] end,
  function(b) b.lanes.BD[1].confidence=0/0 end,
  function(b) b.lanes.HH={} end,
  function(b) b.candidates=nil end,
  function(b) b.generation='1' end,
  function(b) b.phrase_start_cell=b.timeline_cells end,
  function(b) b.phrase_start_cell=-1 end,
  function(b) b.phrase_start_cell=1.5 end,
  function(b) b.phrase_confidence=1.5 end,
  function(b) b.phrase_confidence='high' end,
}
assert(Bank.valid_ready(fresh()))
assert(Bank.VERSION == 3, "schema migration must publish version 3")

-- Phrase alignment. The bank addresses the phrase start as a cell so the
-- centre button can jump the window there; the beat grid is what the alignment
-- editor steps through when the player disagrees with the detector.
do
  local args = { project_id = "p", sample_rate = 48000, capture_start_sample = 0,
    capture_end_sample = 480000, origin_sample = 0, bpm = 120,
    phrase_start_sample = 48000, phrase_confidence = .75,
    beat_positions = { 0, 24000, 48000, 72000 }, candidates = {} }
  local bank = assert(Bank.build(args), "a bank carrying phrase data must build")
  assert(bank.phrase_start_cell == 8, "a cell is 6000 samples at 120bpm/48k, so 48000 is cell 8, got " .. tostring(bank.phrase_start_cell))
  assert(bank.phrase_confidence == .75, "confidence is carried verbatim")
  assert(#bank.source.beat_positions == 4, "the beat grid reaches the alignment editor")
  assert(Bank.valid_ready(bank), "a phrase-carrying bank is valid")
  assert(Bank.phrase_window_start(bank) == 8, "the centre button lands on the phrase start")

  -- A phrase start with no room for a whole window behind it must clamp, not
  -- hand the UI a window start it will refuse.
  local late = Bank.build{ project_id = "p", sample_rate = 48000, capture_start_sample = 0,
    capture_end_sample = 480000, origin_sample = 0, bpm = 120,
    phrase_start_sample = 470000, candidates = {} }
  local low, high = Bank.window_bounds(late)
  assert(Bank.phrase_window_start(late) == high,
    "a phrase start near the end clamps to the last whole window")
  assert(low == 0)

  -- No phrase detected is not the same as a phrase at cell zero, but cell zero
  -- is the only honest place to put the jump when nothing was found.
  local none = assert(Bank.build{ project_id = "p", sample_rate = 48000, capture_start_sample = 0,
    capture_end_sample = 480000, origin_sample = 0, bpm = 120, candidates = {} })
  assert(none.phrase_start_cell == 0, "an absent phrase start defaults to the timeline start")
  assert(none.phrase_confidence == 0, "an absent phrase start claims no confidence")
end

-- A bank saved before phrase alignment existed must still load. The player has
-- real captures on the device; rejecting them to publish a schema number would
-- destroy work to gain nothing.
do
  local legacy = fresh()
  legacy.version = 2
  legacy.phrase_start_cell, legacy.phrase_confidence, legacy.source = nil, nil, nil
  local upgraded = Bank.upgrade(legacy)
  assert(upgraded, "a version 2 bank must upgrade")
  assert(upgraded.version == 3 and upgraded.phrase_start_cell == 0 and upgraded.phrase_confidence == 0,
    "an upgraded bank has a phrase start at the timeline start and claims nothing")
  assert(Bank.valid_ready(upgraded), "an upgraded bank is valid")
  assert(Bank.upgrade({ version = 99 }) == nil, "an unknown schema is not silently accepted")
end
assert(table.concat(Bank.LANES, ",") == "BD,SD,CYM", "schema lane order is the three shipped lanes")
do
  local args = { project_id = "p", sample_rate = 48000, capture_start_sample = 0, capture_end_sample = 480000,
    origin_sample = 0, bpm = 120, candidates = {{lane = "CYM", sample_index = 0, velocity = 80, confidence = .9},
      {lane = "CYM", sample_index = 1, velocity = 80, confidence = .9}} }
  assert(Bank.build(args), "closed and open hat candidates must be accepted")
  args.candidates[1].lane = "HH"
  assert(not Bank.build(args), "combined legacy hat candidates must be rejected")
end
for index, mutate in ipairs(cases) do
  total=total+1
  local bank=fresh(); mutate(bank)
  local ok, valid=pcall(Bank.valid_ready,bank)
  if not ok or valid then failures[#failures+1]='malformed case '..index..' not rejected cleanly' end
end
local ok, low = pcall(Bank.window_bounds,{})
if not ok or low~=nil then failures[#failures+1]='missing timeline did not reject cleanly' end
if #failures>0 then io.stderr:write(table.concat(failures,'\n')..'\n'); os.exit(1) end
print('rhythm_doctor schema: '..total..' malformed banks rejected')
