util={clamp=function(n,a,b) return math.max(a,math.min(b,n)) end}
local id=0;fn={generate_id=function() id=id+1;return id end}
function include(path) return dofile(path:gsub('^mosaic/','')..'.lua') end
local channel={number=1};local swing=0
program={get=function() return {selected_song_pattern=1} end,get_channel=function() return channel end,
 get_effective_swing=function() return swing end,get_effective_swing_shuffle_type=function() return 1 end,
 get_effective_shuffle_basis=function() return 0 end,get_effective_shuffle_feel=function() return 0 end,get_effective_shuffle_amount=function() return 0 end}
local Lattice=dofile('lib/clock/m_lattice.lua');local checked=0
for _,amount in ipairs({-50,50}) do
 swing=amount
 for _,period in ipairs({24,216,408}) do
  for _,division in ipairs({.25,.5,1,2}) do
   dofile('lib/clock/m_clock.lua');clock_lattice=Lattice:new{auto=false,ppqn=96}
   local now=0;local seen={};local first=true
   m_clock.channel_1_clock=clock_lattice:new_sprocket{division=period/384,swing=swing,order=2,action=function()
    if first then first=false;m_clock.new_arp_sprocket(1,division,0,1,4,function() seen[#seen+1]=now end) end
   end}
   local expected={};local tick=0;local n=1
   while true do
    tick=tick+period*division*(1+(n%2==1 and swing or -swing)/100)
    if tick>=period*4 then break end
    expected[#expected+1]=tick;n=n+1
   end
   clock_lattice:start();for t=0,period*5 do now=t;clock_lattice:pulse() end
   assert(#seen==#expected,'Wrong swung onset count')
   for i,t in ipairs(expected) do assert(seen[i]==t,string.format('Swing%s period%s division%s onset%s expected%s actual%s',swing,period,division,i,t,seen[i])) end
   checked=checked+1
  end
 end
end
print(checked..' exact positive/negative swing arp startup and alternating-interval cases passed')
