-- Measures the actual production merge body under dependency-only stubs.
local baseline=arg[1] or 'e5a16bb'
assert(baseline:match('^%x+$') and #baseline>=7 and #baseline<=40, 'Expected commit hash')
local file=assert(io.popen('git show '..baseline..':lib/pattern.lua'));local source=file:read('*a');assert(file:close())
include=function() return {} end
program={initialise_64_table=function(t) for i=1,64 do t[i]=0 end;return t end,
 get_step_trig_masks=function() return nil end}
fn=dofile('lib/helpers/functions.lua')
local original=assert(load(source,'baseline-'..baseline))()
local candidate=dofile('lib/pattern.lua')
local function same(a,b)
 for k,v in pairs(a) do if type(v)=='table' then assert(type(b[k])=='table');same(v,b[k]) else assert(v==b[k],tostring(k)) end end
 for k in pairs(b) do assert(a[k]~=nil,tostring(k)) end
end
for _,count in ipairs({1,4,16}) do
 for _,kind in ipairs({'dense-short','dense-long','sparse-long'}) do
  for _,mode in ipairs({'average','pattern_number_1'}) do
   local song={patterns={},channels={{selected_patterns={}}}}
   for p=1,count do
    local s={lengths={},trig_values={},note_values={},note_mask_values={},velocity_values={}}
    for i=1,64 do
     s.lengths[i]=kind=='dense-short' and 1 or 64
     s.trig_values[i]=(kind~='sparse-long' or (i+p)%16==0) and 1 or 0
     s.note_values[i]=i%12+p;s.note_mask_values[i]=-1;s.velocity_values[i]=80+p
    end
    song.patterns[p]=s;song.channels[1].selected_patterns[p]=true
   end
   same(original.get_and_merge_patterns(1,'all',mode,mode,mode,song),candidate.get_and_merge_patterns(1,'all',mode,mode,mode,song))
   local times={}
   for _,impl in ipairs({original,candidate}) do
    collectgarbage('collect');local t=os.clock()
    for n=1,400 do impl.get_and_merge_patterns(1,'all',mode,mode,mode,song) end
    times[#times+1]=os.clock()-t
   end
   print(string.format('%d %s %s original=%.6f candidate=%.6f speedup=%.3f',count,kind,mode,times[1],times[2],times[1]/times[2]))
  end
 end
end
