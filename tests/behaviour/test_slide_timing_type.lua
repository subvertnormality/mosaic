-- Actual lattice/scheduler regression; native UI companion remains required.
util={clamp=function(v,a,b)return math.max(a,math.min(b,v))end}
program={};local slide_state
local function include_slide_lifetime(name)
 if name=='mosaic/lib/clock/slide_lifetime' then
  return {new=function(...)
   slide_state=dofile('lib/clock/slide_lifetime.lua').new(...)
   return slide_state
  end}
 end
end
function include(name)
 if name=='mosaic/lib/clock/arp_lifetime' then return dofile('lib/clock/arp_lifetime.lua') end
 local slide_lifetime=include_slide_lifetime(name)
 if slide_lifetime then return slide_lifetime end
 return {clock_divisions={}}
end
local Lattice=dofile('lib/clock/m_lattice.lua')

local mc=dofile('lib/clock/m_clock.lua');slide_state:reset()
local sample=function() return slide_state:process() end
local lattice=Lattice:new{auto=false,ppqn=96,pattern_length=4};clock_lattice=lattice
local events,onsets={},{};local channel
local function emit(value,last)
 if value~=last then events[#events+1]={pulse=lattice.transport,value=value} end
end
channel=lattice:new_sprocket{division=1/16,shuffle_feel=3,shuffle_basis=4,shuffle_amount=100,order=2,action=function(t)
 onsets[#onsets+1]=t
 if #onsets==1 then
  emit(24)
  mc.execute_action_across_steps_by_pulses{channel_number=1,trig_lock=1,start_step=1,end_step=4,distance=3,start_value=24,end_value=96,quant=1,func=emit}
 elseif #onsets==2 then
  -- One gap elapsed; activate Heavy6 shuffle for the remaining gaps.
  mc.set_swing_shuffle_type(1,2)
 elseif #onsets==4 then
  if not mc.handoff_spread_lock(1,1,4,96) then emit(96) end
 end
end}
mc.channel_1_clock=channel
channel.end_of_clock_processor=lattice:new_sprocket{division=1/16,order=4,action=function()end}
lattice:new_sprocket{division=1/48,order=5,action=sample};lattice.enabled=true
for pulse=1,145 do lattice:pulse() end
assert(onsets[2]-onsets[1]==24 and onsets[3]-onsets[2]==16 and onsets[4]-onsets[3]==16,'Independent24/16/16pulse onset contract')
local failures=0
for _,event in ipairs(events) do
 local elapsed=event.pulse-onsets[1]
 local ideal=elapsed<=24 and (24+elapsed) or (48+math.min(elapsed-24,32)*1.5)
 if math.abs(event.value-ideal)>.50000001 or event.pulse>onsets[4] then
  failures=failures+1
  print(string.format('FAIL elapsed=%d value=%s expected=%s',elapsed,event.value,ideal))
 end
end
assert(#events>3,'No meaningful slide output')
print(string.format('Live Swing-to-Shuffle onset gaps24/16/16; checked%d emissions; failed%d',#events,failures))
os.exit(failures==0 and 0 or 1)
