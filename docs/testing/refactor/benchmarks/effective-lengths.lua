local unpack=table.unpack
local function effective_lengths(source)
  local result = {unpack(source.lengths)}
  for s = 1, 64 do
    if source.trig_values[s] == 1 and result[s] > 1 then
      for distance = 1, math.min(63, math.ceil(result[s]) - 1) do
        if source.trig_values[(s + distance - 1) % 64 + 1] == 1 then
          result[s] = distance
          break
        end
      end
    end
  end
  return result
end

local original=effective_lengths
local function candidate(source)
  local result={unpack(source.lengths)}
  local next_trig
  for s=1,64 do
    if source.trig_values[s]==1 then next_trig=s+64;break end
  end
  if not next_trig then return result end
  for s=64,1,-1 do
    if source.trig_values[s]==1 then
      local length=result[s]
      if length>1 then
        local distance=next_trig-s
        if distance<=63 and distance<length then result[s]=distance end
      end
      next_trig=s
    end
  end
  return result
end
local scenarios={}
for _,kind in ipairs({'dense-short','dense-long','sparse-long','single-long','fractional'}) do
 local s={lengths={},trig_values={}}
 for i=1,64 do
  s.lengths[i]=kind=='dense-short' and 1 or (kind=='fractional' and (i%9)/3 or 64)
  s.trig_values[i]=(kind=='single-long' and i==32 or kind=='sparse-long' and i%16==0 or kind=='fractional' and i%5==0 or kind:match('dense')) and 1 or 0
 end
 scenarios[kind]=s
end
math.randomseed(42)
local cases=0
for n=1,10000 do
 local s={lengths={},trig_values={}}
 for i=1,64 do s.lengths[i]=({-1,0,0.25,1,1.1,2,2.333,63,64,65,128})[math.random(11)];s.trig_values[i]=math.random(4)==1 and 1 or 0 end
 local a,b=original(s),candidate(s)
 for i=1,64 do assert(a[i]==b[i],n..':'..i) end
 cases=cases+1
end
print('equivalence_cases='..cases)
for name,s in pairs(scenarios) do
 local times={}
 for _,fn in ipairs({original,candidate}) do
  collectgarbage('collect');local t=os.clock()
  for n=1,30000 do fn(s) end
  times[#times+1]=os.clock()-t
 end
 print(name..' original='..times[1]..' candidate='..times[2]..' speedup='..times[1]/times[2])
end
