-- Actual lattice, independent rational-window oracle for inactive settings.
util={clamp=function(n,a,b) return math.max(a,math.min(b,n)) end}
local Lattice=dofile(arg[1] or 'lib/clock/m_lattice.lua')
local checked=0
for _,ratio in ipairs({{3,2},{240,53},{24,5},{120,13},{240,13},{312,5},{636,5}}) do
 for _,operation in ipairs({'feel','basis','both'}) do
  local lattice=Lattice:new{auto=false,ppqn=96};local ticks={};local now=0
  local s=lattice:new_sprocket{division=ratio[1]/ratio[2]/384,swing_or_shuffle=1,shuffle_feel=1,shuffle_basis=1,action=function() ticks[#ticks+1]=now end}
  lattice:start()
  for tick=0,1536*5 do
   now=tick
   if tick>0 and tick%1536==0 then
    local value=1+(tick/1536)%2
    if operation~='basis' then s:set_shuffle_feel(value);assert(s.shuffle_feel==value) end
    if operation~='feel' then s:set_shuffle_basis(value);assert(s.shuffle_basis==value) end
   end
   lattice:pulse()
  end
  for i=1,#ticks-ratio[2] do assert(ticks[i+ratio[2]]-ticks[i]==ratio[1],'Inactive '..operation..' moved rational clock phase') end
  s:set_shuffle_amount(100);s:set_swing_or_shuffle(2)
  assert(s.swing_or_shuffle==2 and s.shuffle_amount==1,'Stored settings lost on activation')
  checked=checked+1
 end
end
print(checked..' inactive shuffle traces preserve rational windows and stored settings')
