util={clamp=function(n,a,b) return math.max(a,math.min(b,n)) end}
local id=0;fn={generate_id=function() id=id+1;return id end}
local Lattice=dofile(arg[1] or 'lib/clock/m_lattice.lua')
local operations={
 {'division',function(s) s:set_division(s.division*1.5) end},
 {'type',function(s) s:set_swing_or_shuffle(3-s.swing_or_shuffle) end},
 {'feel',function(s) s:set_shuffle_feel(2) end},
 {'basis',function(s) s:set_shuffle_basis(2) end},
 {'amount',function(s) s:set_shuffle_amount(30) end},
 {'swing',function(s) s:set_swing(37) end},
 {'delay',function(s) s:set_delay(.5) end},
}
local checked=0
for _,mode in ipairs({1,2}) do
 for _,operation in ipairs(operations) do
  for _,period in ipairs({1.5,240/53,24,216}) do
   for _,length in ipairs({.5,1,2,18,53.25}) do
    local function run(reset)
     local lattice=Lattice:new{auto=false,ppqn=96};local now=0;local s;local first=true;local fired={}
     lattice:new_sprocket{division=1/384,order=1,action=function()
      if reset and (now==5 or now==17 or now==29) then lattice:realign_eligable_sprockets() end
      if now==10 then operation[2](s) end
     end}
     s=lattice:new_sprocket{division=period/384,swing_or_shuffle=mode,shuffle_amount=100,shuffle_feel=1,shuffle_basis=1,realign=true,order=2,action=function()
      if first then first=false;s:set_delayed_action(length,function() fired[#fired+1]=now end,true) end
     end}
     lattice:start()
     for tick=0,math.ceil(period*(length+3)*8+100) do
      now=tick;lattice:pulse()
      if #fired>0 then break end
     end
     assert(#fired==1,'Missing callback')
     return fired[1]
    end
    local reference=run(false);local reset=run(true)
    assert(reference==reset,string.format('mode=%s setter=%s period=%s length=%s no-reset=%s reset=%s',mode,operation[1],period,length,reference,reset))
    checked=checked+1
   end
  end
 end
end
print(checked..' metamorphic setting-change/reset pairs preserve pending timing (supplements independent deadline tests)')
