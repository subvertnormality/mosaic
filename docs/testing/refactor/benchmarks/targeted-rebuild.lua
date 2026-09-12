-- Run from repository root: lua5.3 docs/testing/refactor/benchmarks/targeted-rebuild.lua
-- Actual merge and cooperative scheduler; host CPU time, not physical-norns timing.
local baseline = arg[1] or "c7a9bde"
assert(baseline:match("^%x+$") and #baseline >= 7 and #baseline <= 40)
local f = assert(io.popen("git show " .. baseline .. ":lib/pattern.lua"))
local old_source = f:read("*a"); assert(f:close())
include = function() return {} end
program = {
  initialise_64_table = function(t) for i=1,64 do t[i]=0 end; return t end,
  get_step_trig_masks = function() return nil end
}
fn = dofile("lib/helpers/functions.lua")
local function same(a,b)
  for k,v in pairs(a) do
    if type(v)=="table" then assert(type(b[k])=="table"); same(v,b[k])
    else assert(v==b[k], tostring(k)) end
  end
  for k in pairs(b) do assert(a[k]~=nil,tostring(k)) end
end
local function make_song(consumers)
  local song={patterns={},channels={}}
  for p=1,2 do
    local source={lengths={},trig_values={},note_values={},note_mask_values={},velocity_values={}}
    for s=1,64 do
      source.lengths[s]=16; source.trig_values[s]=s%4==1 and 1 or 0
      source.note_values[s]=s%12+p; source.note_mask_values[s]=-1; source.velocity_values[s]=80+p
    end
    song.patterns[p]=source
  end
  for c=1,16 do
    song.channels[c]={number=c, selected_patterns={[c<=consumers and 1 or 2]=true},
      trig_merge_mode="all", note_merge_mode="average", velocity_merge_mode="average", length_merge_mode="average"}
  end
  return song
end
local function run(candidate,consumers)
  scheduler=dofile("lib/scheduler.lua")
  local impl=candidate and dofile("lib/pattern.lua") or assert(load(old_source))()
  local song=make_song(consumers)
  impl.update_working_patterns(song)
  while scheduler.active_count>0 do scheduler.update() end
  collectgarbage("collect")
  local started=os.clock()
  for edit=1,100 do
    song.patterns[1].note_values[1]=edit%128
    if candidate then impl.update_source_working_patterns(song,1)
    else impl.update_working_patterns(song) end
    while scheduler.active_count>0 do scheduler.update() end
  end
  return os.clock()-started,song
end
for _,consumers in ipairs({1,4,16}) do
  for sample=1,5 do
    local old,new,old_song,new_song
    if sample%2==1 then old,old_song=run(false,consumers); new,new_song=run(true,consumers)
    else new,new_song=run(true,consumers); old,old_song=run(false,consumers) end
    same(old_song,new_song)
    print(string.format("consumers=%d sample=%d baseline=%.6f targeted=%.6f speedup=%.3f",consumers,sample,old,new,old/new))
  end
end
