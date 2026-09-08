util={clamp=function(n,a,b) return math.max(a,math.min(b,n)) end}
local id=0;fn={generate_id=function() id=id+1;return id end}
local Lattice=dofile(arg[1] or 'lib/clock/m_lattice.lua');local checked=0
local cases={
 {name='faster',length=3,expected=41,change=function(s) s:set_division(12/384) end},
 {name='slower',length=3,expected=134,change=function(s) s:set_division(48/384) end},
 -- Existing positive swing lengthens odd cycles: after the unchanged first
 -- 24-pulse cycle, cycles2..4 are12,36,12. Negative swing reverses them.
 {name='positive swing',length=4,expected=84,change=function(s) s:set_swing(50) end},
 {name='negative swing',length=4,expected=108,change=function(s) s:set_swing(-50) end},
}
for _,case in ipairs(cases) do
 for _,reset in ipairs({false,true}) do
  local lattice=Lattice:new{auto=false,ppqn=96};local now=0;local first=true;local fired={};local s
  lattice:new_sprocket{division=1/384,order=1,action=function()
    if reset and (now==5 or now==17 or now==31) then lattice:realign_eligable_sprockets() end
    if now==10 then case.change(s) end
  end}
  s=lattice:new_sprocket{division=24/384,realign=true,order=2,action=function()
   if first then first=false;s:set_delayed_action(case.length,function() fired[#fired+1]=now end,true) end
  end}
  lattice:start()
  for tick=0,180 do now=tick;lattice:pulse() end
  assert(#fired==1 and fired[1]==case.expected,case.name..' reset='..tostring(reset)..' expected='..case.expected..' actual='..tostring(fired[1]))
  assert(not s._pending_clocks or #s._pending_clocks==0,'Completed timing group leaked')
  checked=checked+1
 end
end
-- Deferred callbacks retain insertion order, live values and parent cancellation.
local lattice=Lattice:new{auto=false,ppqn=96};local now=0;local first=true;local s;local seen={};local cancelled;local live_pitch=60
lattice:new_sprocket{division=1/384,order=1,action=function()
 if now==5 or now==19 then lattice:realign_eligable_sprockets() end
 if now==10 then live_pitch=69;s.delayed_actions[cancelled]=nil end
end}
s=lattice:new_sprocket{division=24/384,realign=true,order=2,action=function()
 if first then
  first=false
  s:set_delayed_action(1.5,function() seen[#seen+1]={now,live_pitch,'first'} end)
  s:set_delayed_action(1.5,function() seen[#seen+1]={now,live_pitch,'second'} end)
  cancelled=s:set_delayed_action(2,function() error('Cancelled action executed') end)
 end
end}
lattice:start();for tick=0,100 do now=tick;lattice:pulse() end
assert(#seen==2 and seen[1][1]==36 and seen[2][1]==36 and seen[1][2]==69 and seen[2][2]==69 and seen[1][3]=='first' and seen[2][3]=='second','Deferred timing/order/live-value failure')
assert(not s._pending_clocks or #s._pending_clocks==0,'Cancelled group leaked')
print((checked+1)..' pending dynamic-rate, cancellation and deferred-value cases passed')
