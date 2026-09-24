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
assert(Bank.VERSION == 5, "schema migration must publish version 5")

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
  -- Version 2: before phrase alignment and before lane sets were data.
  local legacy = fresh()
  legacy.version = 2
  legacy.phrase_start_cell, legacy.phrase_confidence, legacy.source = nil, nil, nil
  legacy.lane_names = nil
  local upgraded = Bank.upgrade(legacy)
  assert(upgraded, "a version 2 bank must upgrade")
  assert(upgraded.version == Bank.VERSION and upgraded.phrase_start_cell == 0 and upgraded.phrase_confidence == 0,
    "an upgraded bank has a phrase start at the timeline start and claims nothing")
  assert(table.concat(upgraded.lane_names, ",") == "BD,SD,CYM",
    "a bank written before lane sets were data had the three the device produces")
  assert(Bank.valid_ready(upgraded), "an upgraded bank is valid")

  -- Version 3: had phrase alignment, still had no declared lane set.
  local three = fresh()
  three.version, three.lane_names = 3, nil
  local from_three = Bank.upgrade(three)
  assert(from_three and from_three.version == Bank.VERSION, "a version 3 bank must upgrade")
  assert(table.concat(from_three.lane_names, ",") == "BD,SD,CYM", "and gains the lane set it had")
  assert(Bank.valid_ready(from_three), "an upgraded version 3 bank is valid")

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

-- Lane sets are data. The local backend produces three lanes; the remote
-- server separates a kit and produces ten. A bank has to hold whichever its
-- own analysis produced, or the extra lanes are discarded on arrival and the
-- server is pointless.
do
  local remote = { "KICK", "SNARE", "TOMS", "HIHAT", "CYMBALS",
                   "BASS", "GUITAR", "PIANO", "VOCALS", "OTHER" }
  local sensitivities = {}
  for _, lane in ipairs(remote) do sensitivities[lane] = 0 end
  local bank = assert(Bank.build{ project_id = "p", sample_rate = 48000,
    capture_start_sample = 0, capture_end_sample = 480000, origin_sample = 0, bpm = 120,
    lane_names = remote, sensitivities = sensitivities,
    candidates = { { lane = "TOMS", sample_index = 6000, velocity = 90, confidence = .9 },
                   { lane = "GUITAR", sample_index = 12000, velocity = 40, confidence = .8 } } },
    "a ten lane bank must build")
  assert(#bank.lane_names == 10, "the bank keeps every lane it was given")
  assert(bank.lanes.TOMS[2], "a tom lands in its own lane, got " .. tostring(bank.lanes.TOMS[2]))
  assert(bank.lanes.GUITAR[3], "a melodic stem lands in its own lane")
  assert(Bank.valid_ready(bank), "a ten lane bank is valid")
  local window = assert(Bank.window(bank, "GUITAR"), "a window can be taken of any declared lane")
  assert(window.cells[3], "the window shows the lane's hits")
  assert(Bank.window(bank, "BD") == nil, "a lane this bank does not have is not addressable")

  -- A candidate naming a lane the bank was not told about is a mismatched
  -- analysis, not a new lane to invent.
  local bad = Bank.build{ project_id = "p", sample_rate = 48000, capture_start_sample = 0,
    capture_end_sample = 480000, origin_sample = 0, bpm = 120, lane_names = remote,
    sensitivities = sensitivities,
    candidates = { { lane = "TROMBONE", sample_index = 6000, velocity = 90, confidence = .9 } } }
  assert(not bad, "a candidate outside the declared lane set is rejected")

  -- Saying nothing keeps the three lanes the local backend produces, so every
  -- existing caller and every saved bank behaves exactly as before.
  local default = assert(Bank.build{ project_id = "p", sample_rate = 48000,
    capture_start_sample = 0, capture_end_sample = 480000, origin_sample = 0, bpm = 120,
    candidates = {} })
  assert(table.concat(default.lane_names, ",") == "BD,SD,CYM", "the default lane set is unchanged")
end

-- A bank saved before BASS was withdrawn still has four lanes, and its owner
-- still has the project. Refusing to load it loses their whole song over a
-- lane the product removed; keeping the lane resurrects one that was withdrawn
-- because it only ever duplicated BD. The upgrade drops it, and says so by
-- leaving the bank valid rather than rejecting it.
do
  local legacy = assert(Bank.build{project_id='p', generation=5, analysis_revision=0,
    sample_rate=48000, capture_start_sample=0, capture_end_sample=480000,
    origin_sample=0, bpm=120, candidates={
      {lane='BD', sample_index=0, velocity=80, confidence=.9},
      {lane='SD', sample_index=6000, velocity=70, confidence=.8}}})
  -- Reshape it as a version 2 bank that still carries BASS.
  legacy.version = 2
  legacy.lane_names, legacy.phrase_start_cell, legacy.phrase_confidence = nil, nil, nil
  legacy.lanes.BASS = { [1] = { velocity = 80, confidence = .9, sample_index = 0, collision_count = 0 } }
  legacy.sensitivities.BASS = 0
  legacy.candidates[#legacy.candidates + 1] =
    { lane = 'BASS', sample_index = 0, velocity = 80, confidence = .9, cell = 0 }

  local upgraded = Bank.upgrade(legacy)
  assert(upgraded, "a four lane bank must upgrade rather than fail")
  assert(upgraded.lanes.BASS == nil, "the withdrawn lane is dropped")
  assert(upgraded.sensitivities.BASS == nil, "and so is its sensitivity")
  for _, candidate in ipairs(upgraded.candidates) do
    assert(candidate.lane ~= 'BASS', "and its candidates")
  end
  assert(upgraded.lanes.BD and upgraded.lanes.SD, "the lanes the product still has are kept")
  assert(#upgraded.candidates == 2, "only the withdrawn lane's candidates go, got " .. #upgraded.candidates)
  assert(Bank.valid_ready(upgraded), "an upgraded four lane bank loads")
end

-- Lane order is part of what a bank stores, and it changed: the grid used to
-- read BASS, CYMBALS, GUITAR, HIHAT, KICK... because the names were sorted
-- alphabetically. A bank written before that changed must come forward, or a
-- player who analysed yesterday keeps a grid that reads as nonsense until they
-- record again.
do
  local Bank = require('rhythm_doctor.bank')
  local alphabetical = { "BASS", "CYMBALS", "GUITAR", "HIHAT", "KICK",
                         "OTHER", "PIANO", "SNARE", "TOMS", "VOCALS" }
  local lanes, sensitivities = {}, {}
  for _, lane in ipairs(alphabetical) do lanes[lane] = {}; sensitivities[lane] = .3 end
  local stored = { version = 4, project_id = "p", lane_names = alphabetical,
    lanes = lanes, sensitivities = sensitivities, candidates = {}, source = {},
    phrase_start_cell = 0, phrase_confidence = 0 }

  local upgraded = Bank.upgrade(stored)
  assert(upgraded, "a bank one version behind must still load")
  assert(table.concat(upgraded.lane_names, " ") ==
    "KICK SNARE HIHAT CYMBALS TOMS BASS GUITAR PIANO VOCALS OTHER",
    "a stored bank is brought into kit order rather than left alphabetical")
  assert(upgraded.version == Bank.VERSION, "and lands on the current version")
  for _, lane in ipairs(alphabetical) do
    assert(upgraded.lanes[lane], lane .. " must survive the reorder")
    assert(upgraded.sensitivities[lane] == .3, lane .. " keeps its sensitivity")
  end

  -- Reordering is idempotent: a bank already at this version is returned as is.
  assert(Bank.upgrade(upgraded) == upgraded, "an up-to-date bank is not rebuilt")
  print("bank schema: stored lane order is brought into kit order")
end
