-- Projection conformance against actual future lattice callbacks; no norns
-- scheduler mocks or claim of complete Mosaic slide correctness.
util={clamp=function(v,a,b)return math.max(a,math.min(b,v))end}
local Lattice=dofile('lib/clock/m_lattice.lua')
local cases,checks=0,0
local function check(division,swing,length,mode,feel,basis,amount)
  cases=cases+1
  local l=Lattice:new{auto=false,ppqn=96,pattern_length=length}
  local onsets,predictions={},{};local s
  s=l:new_sprocket{division=division,swing=swing,swing_or_shuffle=mode or 1,
    shuffle_feel=feel,shuffle_basis=basis,shuffle_amount=amount,action=function(t)
      onsets[#onsets+1]=t
      if #onsets<=8 then
        local saved={};for k,v in pairs(s) do saved[k]=v end
        local row={};for _,distance in ipairs({1,2,3,7,16,64}) do row[distance]=s:project_onset_pulses(distance) end
        for k,v in pairs(saved) do assert(s[k]==v,'Projection mutated live '..k) end
        for k in pairs(s) do assert(saved[k]~=nil,'Projection added live state') end
        predictions[#onsets]=row
      end
    end}
  l.enabled=true
  local pulses=0
  while #onsets<72 do l:pulse();pulses=pulses+1;assert(pulses<100000) end
  for start,row in ipairs(predictions) do
    for distance,wanted in pairs(row) do
      assert(onsets[start+distance]-onsets[start]==wanted,string.format('Projection mismatch case%d start%d distance%d',cases,start,distance))
      if division==1/16 and swing==0 and (mode or 1)==1 then assert(wanted==24*distance,'Independent straight-sixteenth oracle') end
      checks=checks+1
    end
  end
end
for _,division in ipairs({1/384,1/224,1/112,1/56,1/16,1/12,1/8}) do
  for _,swing in ipairs({-50,-25,0,25,50}) do
    for _,length in ipairs({3,4,64}) do check(division,swing,length) end
  end
end
for feel=1,4 do for basis=1,6 do for _,amount in ipairs({0,50,100}) do
  for _,length in ipairs({3,4,64}) do for _,division in ipairs({1/56,1/16}) do
    check(division,0,length,2,feel,basis,amount)
  end end
end end end
local l=Lattice:new{auto=false};local s=l:new_sprocket{division=1/16};s:begin_cycle()
for _,n in ipairs({0,-1,1.5,65}) do assert(not pcall(s.project_onset_pulses,s,n)) end
s.phase=3;assert(not pcall(s.project_onset_pulses,s,1));s.phase=1
s.division_for_cycle=function()error('Must never run side-effect callback')end
assert(not pcall(s.project_onset_pulses,s,1))
print(string.format('PASS %d timing configurations; %d projected-onset comparisons; unchanged live state and explicit unsupported inputs',cases,checks))
