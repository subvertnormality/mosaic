util={clamp=function(n,a,b) return math.max(a,math.min(b,n)) end}
local id=0;fn={generate_id=function() id=id+1;return id end}
local Lattice=dofile(arg[1] or 'lib/clock/m_lattice.lua');local checked=0
for _,child_length in ipairs({.5,1,1.5,2}) do
 for _,reset in ipairs({-1,5,17,23,24,25}) do
  local lattice=Lattice:new{auto=false,ppqn=96};local now=0;local first=true;local s;local events={}
  lattice:new_sprocket{division=1/384,order=1,action=function() if now==reset then lattice:realign_eligable_sprockets() end end}
  s=lattice:new_sprocket{division=24/384,realign=true,order=2,action=function()
   if first then first=false;s:set_delayed_action(1,function()
    events[#events+1]=now
    s:set_delayed_action(child_length,function() events[#events+1]=now end,true)
   end) end
  end}
  lattice:start();for tick=0,120 do now=tick;lattice:pulse() end
  assert(#events==2 and events[1]==24 and events[2]==24+child_length*24,'Callback child length='..child_length..' reset='..reset..' expected='..(24+child_length*24)..' actual='..tostring(events[2]))
  checked=checked+1
 end
end
-- Match m_clock.destroy_at_note_end_ids' actual tombstone cancellation form.
do
 local lattice=Lattice:new{auto=false,ppqn=96};local now=0;local s;local pending_id;local first=true
 lattice:new_sprocket{division=1/384,order=1,action=function()
  if now==5 then lattice:realign_eligable_sprockets() end
  if now==10 then s.delayed_actions[pending_id].action=function() end;s.delayed_actions[pending_id].length=math.huge end
 end}
 s=lattice:new_sprocket{division=24/384,realign=true,order=2,action=function()
  if first then first=false;pending_id=s:set_delayed_action(64,function() error('Cancelled work ran') end) end
 end}
 lattice:start();for tick=0,1000 do now=tick;lattice:pulse() end
 assert(not s._pending_clocks or #s._pending_clocks==0,'Tombstone retained timing group')
 assert(not s.delayed_actions[pending_id].timing,'Tombstone retained timing reference')
 checked=checked+1
end
print(checked..' callback-child and tombstone cancellation cases passed')
