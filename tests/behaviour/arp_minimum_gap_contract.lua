util={clamp=function(n,a,b) return math.max(a,math.min(b,n)) end}
local id=0;fn={generate_id=function() id=id+1;return id end}
function include(path) return dofile(path:gsub('^mosaic/','')..'.lua') end
local channel={number=1};local swing=0
program={get=function() return {selected_song_pattern=1} end,get_channel=function() return channel end,
 get_effective_swing=function() return swing end,get_effective_swing_shuffle_type=function() return 1 end,
 get_effective_shuffle_basis=function() return 0 end,get_effective_shuffle_feel=function() return 0 end,get_effective_shuffle_amount=function() return 0 end}
local Lattice=dofile('lib/clock/m_lattice.lua')
local failures=0
for _,amount in ipairs({-50,50}) do
 swing=amount
 dofile('lib/clock/m_clock.lua');clock_lattice=Lattice:new{auto=false,ppqn=96}
 local now=0;local seen={};local first=true
 m_clock.channel_1_clock=clock_lattice:new_sprocket{division=(24/5)/384,swing=swing,order=2,action=function()
  if first then first=false;m_clock.new_arp_sprocket(1,.5,1/24,-4,16,function() seen[#seen+1]=now end) end
 end}
 clock_lattice:start()
 for t=0,100 do now=t;clock_lattice:pulse() end
 local expected=amount<0 and {1,4,5,6} or {4,5,6,7}
 local same=#seen==4
 for i,t in ipairs(expected) do if seen[i]~=t then same=false end end
 print('swing='..amount..' callbacks='..table.concat(seen,','))
 if not same then failures=failures+1 end
end
assert(failures==0,'Positive short gaps lost or moved '..failures..' signed cases')
print('Both signed minimum swung-gap regressions passed')

-- Startup itself previously rounded below one pulse for the shortest division.
for _,amount in ipairs({-50,50}) do
 swing=amount
 dofile('lib/clock/m_clock.lua');clock_lattice=Lattice:new{auto=false,ppqn=96}
 local now=0;local seen={};local first=true
 m_clock.channel_1_clock=clock_lattice:new_sprocket{division=(24/5)/384,swing=swing,order=2,action=function()
  if first then first=false;m_clock.new_arp_sprocket(1,1/24,0,0,16,function() seen[#seen+1]=now end) end
 end}
 clock_lattice:start();for t=0,100 do now=t;clock_lattice:pulse() end
 local expected=amount<0 and {1,2,3,5,6,7,8,10} or {1,2,4,5,6,7,9,10}
 for i,t in ipairs(expected) do assert(seen[i]==t,'Minimum startup gap mismatch') end
 for i=2,#seen do assert(seen[i]>seen[i-1] and seen[i]-seen[i-1]<=2,'Nonpositive/unbounded startup cycle') end
end
print('Both zero-rounded-startup regressions passed')
