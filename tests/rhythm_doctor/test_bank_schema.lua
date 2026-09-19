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
  function(b) b.candidates=nil end,
  function(b) b.generation='1' end,
}
assert(Bank.valid_ready(fresh()))
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
