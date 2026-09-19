util={clamp=function(n,a,b) return math.max(a,math.min(b,n)) end}
local id=0;fn={generate_id=function() id=id+1;return id end}
local Lattice=dofile(arg[1] or 'lib/clock/m_lattice.lua');local checked=0
for _,period in ipairs({2,3,24,216,408}) do
 for _,length in ipairs({.1,.25,.5,.9,1,1.5,2,3.2,65}) do
  local deadline=math.ceil(period*length-1e-9)
  for _,reset_tick in ipairs({1,math.max(1,deadline-1),deadline,deadline+1}) do
   for _,repeated in ipairs({false,true}) do
    local lattice=Lattice:new{auto=false,ppqn=96};local now=0;local fired={};local first=true;local sprocket
    lattice:new_sprocket{division=1/384,order=1,action=function()
      if now==reset_tick or (repeated and now>reset_tick and (now-reset_tick)%7==0) then lattice:realign_eligable_sprockets() end
    end}
    sprocket=lattice:new_sprocket{division=period/384,realign=true,order=2,action=function()
      if first then first=false;sprocket:set_delayed_action(length,function() fired[#fired+1]=now end,true) end
    end}
    lattice:start()
    for tick=0,deadline+period*2 do now=tick;lattice:pulse() end
    assert(#fired==1 and fired[1]==deadline,string.format('T=%s length=%s reset=%s repeat=%s expected=%s actual=%s',period,length,reset_tick,tostring(repeated),deadline,tostring(fired[1])))
    checked=checked+1
   end
  end
 end
end
print(checked..' pending-progress independent pulse-deadline cases passed')
