util={clamp=function(n,a,b) return math.max(a,math.min(b,n)) end}
local id=0;fn={generate_id=function() id=id+1;return id end}
function include(path) return dofile(path:gsub('^mosaic/','')..'.lua') end
local channel={number=1};local data={selected_song_pattern=1,song_patterns={}}
program={get=function() return data end,get_channel=function() return channel end,
 get_effective_swing=function() return 0 end,get_effective_swing_shuffle_type=function() return 1 end,
 get_effective_shuffle_basis=function() return 0 end,get_effective_shuffle_feel=function() return 0 end,get_effective_shuffle_amount=function() return 0 end}
local Lattice=dofile(arg[1] or 'lib/clock/m_lattice.lua')
dofile('lib/clock/m_clock.lua')
local stopped=false;local now=0;local events={};local first=true;local releases={};local inits=0
step={reset=function() end};nb={stop_all=function() end};m_midi={stop=function() end}
-- Keep the actual Stop/reset and old-lattice destruction; the new session's
-- unrelated application/page setup is outside this lifecycle fixture.
m_clock.init=function() inits=inits+1;clock_lattice=Lattice:new{auto=false,ppqn=96};clock_lattice:stop() end
clock_lattice=Lattice:new{auto=false,ppqn=96};local original=clock_lattice
local function release(name)
 events[#events+1]={name,now}
 if not stopped then stopped=true;m_clock:stop() end
end
m_clock.channel_2_clock=clock_lattice:new_sprocket{division=24/384,order=2,action=function() end}
m_clock.channel_1_clock=clock_lattice:new_sprocket{division=24/384,order=2,action=function()
 if first then
  first=false
  m_clock.delay_action(2,4,'must_execute',function() release('other-channel') end,true)
  for n=1,2 do
   local name='owned-'..n
   releases[#releases+1]=m_clock.delay_action(1,4,'execute_at_note_end',function() release(name) end,true)
  end
  m_clock.new_arp_sprocket(1,.5,0,1,1,function() end,releases)
 end
end}
original:start()
for tick=0,100 do now=tick;original:pulse() end
assert(stopped and inits==1 and not original.enabled and not clock_lattice.enabled,'Stop/restart lifecycle mismatch')
assert(#events==3,'Missing/duplicate release during reentrant Stop')
local seen={};for _,event in ipairs(events) do assert(event[2]==24 and not seen[event[1]],'Release order/time/duplication');seen[event[1]]=true end
assert(seen['owned-1'] and seen['owned-2'] and seen['other-channel'],'Cross-channel cleanup missed')
print('Actual arp gate reentrant Stop drains two owned releases and another channel exactly once; new lattice remains stopped')
