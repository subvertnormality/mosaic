util={clamp=function(n,a,b) return math.max(a,math.min(b,n)) end}
local id=0;fn={generate_id=function() id=id+1;return id end}
function include(path)
 if path=='mosaic/lib/clock/m_clock' then return m_clock end
 if path=='mosaic/lib/quantiser' then return {} end -- Unused by note release.
 return dofile(path:gsub('^mosaic/','')..'.lua')
end
local channel={number=1}
program={get=function() return {selected_song_pattern=1} end,get_channel=function() return channel end,
 get_effective_swing=function() return 0 end,get_effective_swing_shuffle_type=function() return 1 end,
 get_effective_shuffle_basis=function() return 0 end,get_effective_shuffle_feel=function() return 0 end,get_effective_shuffle_amount=function() return 0 end}
local Lattice=dofile('lib/clock/m_lattice.lua');local checked=0;local failures=0
for _,period in ipairs({24,216,408}) do
 for _,division in ipairs({1/24,1/12,1/16,1/8,1/6,1/4,1/3,3/8,1/2,5/8,2/3,3/4,5/6,7/8,1,1.25,1.5,2}) do
  dofile('lib/clock/m_clock.lua');clock_lattice=Lattice:new{auto=false,ppqn=96}
  local _, play_arp_note = dofile('lib/clock/voice_lifetime.lua').new(m_clock)
  local now=0;local first=true;local voices={};local release_ids={};local gate=16
  local function note(offset)
   local v={on=now};voices[#voices+1]=v
   local container={channel=1,midi_channel=1,midi_device=1,player={note_off=function(_,pitch,velocity,chan,device)
    assert(pitch==60 and velocity==127 and chan==1 and device==1,'Wrong release data')
    assert(not v.off,'Duplicate release');v.off=now
   end}}
   local id=play_arp_note(60,container,127,division,function(pitch,velocity,chan,device)
    assert(pitch==60 and velocity==127 and chan==1 and device==1,'Wrong onset data')
   end,offset)
   if id then release_ids[#release_ids+1]=id end
  end
  m_clock.channel_1_clock=clock_lattice:new_sprocket{division=period/384,order=2,action=function()
   if first then first=false;note();m_clock.new_arp_sprocket(1,division,0,1,gate,function(_,offset) note(offset) end,release_ids) end
  end}
  clock_lattice:start();for tick=0,period*(gate+3) do now=tick;clock_lattice:pulse() end
  local bad
  for _,v in ipairs(voices) do
   local expected=math.min(v.on+math.ceil(division*period-1e-9),gate*period)
   if v.off~=expected then bad=string.format('on=%s expectedoff=%s actualoff=%s',v.on,expected,tostring(v.off));break end
  end
  if bad then failures=failures+1;print(string.format('period=%s division=%s: %s',period,division,bad)) end
  checked=checked+1
 end
end
print(string.format('%s failures / %s actual arp+parent release cases',failures,checked))
os.exit(failures==0 and 0 or 1)
