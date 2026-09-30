-- Reference-host CPU measurement for the pure Harmony solver. This deliberately
-- excludes clocks, MIDI and emulator work; it is evidence, not a norns claim.
local root=arg[1]or"."
local voicing=dofile(root.."/lib/harmony/voicing.lua")
local roles={
  {id="v1",min=24,max=60,centre=48,preferred_leap=12},
  {id="v2",min=36,max=72,centre=55,preferred_leap=7},
  {id="v3",min=43,max=79,centre=62,preferred_leap=7},
  {id="v4",min=48,max=84,centre=67,preferred_leap=7},
  {id="v5",min=55,max=96,centre=72,preferred_leap=7},
}
local material={}
for index,pc in ipairs({0,2,4,7,11})do material[index]={id="s"..index,pc=pc,required=true}end
local repeats=100
local rows={}
for _,preset in ipairs({"smooth","compact","independent"})do
  local frame={mode="revoice",material=material,roles=roles,previous={},crossing=false,
    exact_unison=false,preset=preset,policy_version=1,node_budget=200000,
    bass={mode="smooth",direction="nearest"}}
  local started=os.clock();local nodes=0
  for _=1,repeats do
    local result=voicing.solve(frame);assert(result.status=="ok",result.status)
    nodes=math.max(nodes,result.nodes or 0)
  end
  local elapsed=os.clock()-started
  rows[#rows+1]=string.format('{"preset":"%s","runs":%d,"nodes":%d,"cpu_seconds":%.6f,"cpu_ms_per_solve":%.6f}',
    preset,repeats,nodes,elapsed,elapsed*1000/repeats)
end
io.write('{"schema_version":1,"scope":"reference-host-pure-solver","rows":['..table.concat(rows,",")..']}\n')
