util={clamp=function(n,a,b) return math.max(a,math.min(b,n)) end}
local id=0;fn={generate_id=function() id=id+1;return id end}
local Lattice=dofile(arg[1] or 'lib/clock/m_lattice.lua');local checked=0
do
 local lattice=Lattice:new{auto=false,ppqn=96};local now=0;local s;local onsets=0;local events={};local releases={}
 lattice:new_sprocket{division=1/384,order=1,action=function()
  if now==5 or now==10 or now==15 or now==20 or now==48 then lattice:realign_eligable_sprockets() end
 end}
 s=lattice:new_sprocket{division=24/384,realign=true,order=2,action=function()
  onsets=onsets+1;events[#events+1]={kind='on',tick=now}
  if onsets<=5 then
   local origin=now
   s:set_delayed_action(2,function() releases[#releases+1]={origin,now};events[#events+1]={kind='off',tick=now} end,true)
  end
 end}
 lattice:start();for tick=0,140 do now=tick;lattice:pulse() end
 assert(#releases==5)
 for i,pair in ipairs(releases) do assert(pair[1]==(i-1)*5 and pair[2]==pair[1]+48,'Populated generations moved deadlines') end
 local at48={};for _,event in ipairs(events) do if event.tick==48 then at48[#at48+1]=event.kind end end
 assert(#at48==2 and at48[1]=='off' and at48[2]=='on','Due release did not precede coincident reset onset')
 assert(not s._pending_clocks,'Populated timing generations leaked');checked=checked+1
end
for _,delay in ipairs({.5,1}) do
 local lattice=Lattice:new{auto=false,ppqn=96};local now=0;local s;local seen={}
 lattice:new_sprocket{division=1/384,order=1,action=function() if now==5 or now==17 then lattice:realign_eligable_sprockets() end end}
 s=lattice:new_sprocket{division=24/384,delay=delay,realign=true,order=2,action=function() end}
 s:set_delayed_action(1,function() seen[#seen+1]=now end)
 lattice:start();for tick=0,100 do now=tick;lattice:pulse() end
 assert(#seen==1 and seen[1]==24*(1+delay),'Negative delayed phase changed pending deadline');checked=checked+1
end
do
 local lattice=Lattice:new{auto=false,ppqn=96};local now=0;local s;local first=true;local seen={}
 lattice:new_sprocket{division=1/384,order=1,action=function()
  if now==5 then lattice:realign_eligable_sprockets() end
  if now==10 then s:stop() end
  if now==21 then s:start() end
 end}
 s=lattice:new_sprocket{division=24/384,realign=true,order=2,action=function()
  if first then first=false;s:set_delayed_action(2,function() seen[#seen+1]=now end) end
 end}
 lattice:start();for tick=0,120 do now=tick;lattice:pulse() end
 assert(#seen==1 and seen[1]==59,'Disabled parent did not pause pending progress')
 assert(not s._pending_clocks,'Resumed group leaked');checked=checked+1
end
do
 local lattice=Lattice:new{auto=false,ppqn=96};local now=0;local s;local first=true;local seen={}
 s=lattice:new_sprocket{division=24/384,realign=true,action=function()
  if first then first=false;s:set_delayed_action(1,function()
   lattice:realign_eligable_sprockets()
   s:set_delayed_action(.5,function() seen[#seen+1]=now end,true)
  end) end
 end}
 lattice:start();for tick=0,100 do now=tick;lattice:pulse() end
 assert(#seen==1 and seen[1]==36,'Callback realignment lost child timing context');checked=checked+1
end
do
 local lattice=Lattice:new{auto=false,ppqn=96};local s=lattice:new_sprocket{division=24/384,realign=true,action=function() end}
 local ok,err=pcall(function() s:run_pending_action{action=function() error('intentional-pending-error') end} end)
 assert(not ok and tostring(err):find('intentional%-pending%-error'),'Callback error swallowed')
 assert(not s._executing_pending_action,'Callback error leaked scheduling context');checked=checked+1
end
print(checked..' populated-generation, delayed-phase, pause, reentrant-reset and error cases passed')
