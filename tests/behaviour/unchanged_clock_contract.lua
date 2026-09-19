-- Real lattice with a rational musical oracle and unchanged-setting controls.
util={clamp=function(n,a,b) return math.max(a,math.min(b,n)) end}
local Lattice=dofile(arg[1] or 'lib/clock/m_lattice.lua')
local ratios={{3,2},{240,53},{24,5},{120,13},{240,13},{312,5},{636,5}}
local checked=0
for _,ratio in ipairs(ratios) do
 for _,operation in ipairs({'none','type','feel','basis','division','all'}) do
  local lattice=Lattice:new{auto=false,ppqn=96};local ticks={};local now=0
  local s=lattice:new_sprocket{division=ratio[1]/ratio[2]/384,shuffle_feel=1,shuffle_basis=1,swing_or_shuffle=1,action=function() ticks[#ticks+1]=now end}
  lattice:start()
  for tick=0,1536*5 do
   now=tick
   if tick>0 and tick%1536==0 then
    if operation=='type' or operation=='all' then s:set_swing_or_shuffle(1) end
    if operation=='feel' or operation=='all' then s:set_shuffle_feel(1) end
    if operation=='basis' or operation=='all' then s:set_shuffle_basis(1) end
    if operation=='division' or operation=='all' then s:set_division(ratio[1]/ratio[2]/384) end
   end
   lattice:pulse()
  end
  for i=1,#ticks-ratio[2] do
   assert(ticks[i+ratio[2]]-ticks[i]==ratio[1],'Unchanged '..operation..' moved rational clock phase for '..ratio[1]..'/'..ratio[2])
  end
  checked=checked+1
 end
end
print(checked..' unchanged-setting lattice traces preserve every rational window across five boundaries')
