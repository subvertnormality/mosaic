-- RD-02/04 performance characterisation outside README. PLAN.md: 45s bank,
-- instant window slicing, no classifier rerun, and p95 UI <=100ms on Norns.
-- os.clock measures Lua CPU only: this DOES NOT certify UI wall-clock latency.
package.path = './?.lua;' .. package.path
local Bank = require('lib.rhythm_doctor.bank')
local lanes = {'BD', 'SD', 'CHH', 'OHH', 'BASS'}
local candidates = {}
for _, lane in ipairs(lanes) do
  for sample = 0, 2160000 - 480, 480 do
    candidates[#candidates + 1] = {lane=lane, sample_index=sample, velocity=80, confidence=.9}
  end
end
collectgarbage('collect')
local memory_before = collectgarbage('count')
local started = os.clock()
local bank, problem = Bank.build({project_id='benchmark', generation=1, analysis_revision=1,
  sample_rate=48000, capture_start_sample=0, capture_end_sample=2160000, origin_sample=0,
  bpm=240, candidates=candidates})
assert(bank, problem and problem.code)
local build_cpu_ms = (os.clock()-started)*1000
assert(bank.timeline_cells == 720, 'PLAN: sample-derived complete timeline length')
local samples = {}
for i = 1, 100 do
  local window_start = (i * 17) % 657
  started = os.clock()
  local moved = assert(Bank.with_window_start(bank, window_start))
  for _, lane in ipairs(lanes) do
    local window = assert(Bank.window(moved, lane))
    assert(window.start == window_start and window.cell_count == 64, 'PLAN: shared64-cell window')
    assert(window.cells[1].velocity == 80 and window.cells[64].velocity == 80,
      'PLAN: browsing preserves captured velocity and complete cells')
  end
  samples[#samples + 1] = (os.clock()-started)*1000
end
table.sort(samples)
print(string.format('{"scope":"Lua bank CPU only; no UI/hardware latency claim",' ..
  '"candidates":%d,"timeline_cells":%d,"samples":%d,"build_cpu_ms":%.6f,' ..
  '"scroll_five_lanes_cpu_p95_ms":%.6f,"scroll_five_lanes_cpu_max_ms":%.6f,' ..
  '"lua_heap_growth_kib":%.6f,"semantic_assertions_passed":true}',
  #candidates, bank.timeline_cells, #samples, build_cpu_ms, samples[95], samples[100],
  collectgarbage('count')-memory_before))
