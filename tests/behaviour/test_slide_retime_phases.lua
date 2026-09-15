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
 if name=='mosaic/lib/clock/transport_lifecycle' then return dofile('lib/clock/transport_lifecycle.lua') end
 if name=='mosaic/lib/clock/arp_lifetime' then return dofile('lib/clock/arp_lifetime.lua') end
 local slide_lifetime=include_slide_lifetime(name)
 if slide_lifetime then return slide_lifetime end
 return {clock_divisions={}}
end
local Lattice=dofile('lib/clock/m_lattice.lua')

local count=0
for _,edit in ipairs({8,12,16,24,32,36,40}) do
 for _,factor in ipairs({0.5,2}) do
  local mc=dofile('lib/clock/m_clock.lua');slide_state:reset()
  local sample=function() return slide_state:process() end
  local l=Lattice:new{auto=false,ppqn=96,pattern_length=4};clock_lattice=l
  local events,onsets={},{};local channel
  local function emit(value,last)if value~=last then events[#events+1]={at=l.transport,value=value}end end
  channel=l:new_sprocket{division=1/16,order=2,action=function(t)
   onsets[#onsets+1]=t
   if #onsets==1 then
    emit(24);mc.execute_action_across_steps_by_pulses{channel_number=1,trig_lock=1,start_step=1,end_step=4,distance=3,start_value=24,end_value=96,quant=1,func=emit}
   elseif #onsets==4 then
    if not mc.handoff_spread_lock(1,1,4,96) then emit(96) end
   end
  end};mc.channel_1_clock=channel
  channel.end_of_clock_processor=l:new_sprocket{division=1/16,order=4,action=function()end}
  l:new_sprocket{division=1/48,order=5,action=sample};l.enabled=true
  for pulse=1,200 do
   if l.transport==edit+1 then mc.set_channel_division(1,4/factor) end
   l:pulse()
  end
  local destination=1+edit+(72-edit)*factor
  assert(onsets[1]==1 and onsets[4]==destination,string.format('Independent destination edit=%s factor=%s first=%s expected=%s actual=%s',edit,factor,onsets[1],destination,onsets[4]))
  local endpoint=0
  for _,event in ipairs(events)do
   local elapsed=event.at-1
   local ideal=elapsed<=edit and (24+elapsed) or (24+edit+(elapsed-edit)/factor)
   assert(event.at<=destination,'Output after destination')
   assert(math.abs(event.value-ideal)<=.50000001,string.format('Discontinuous retime at%d factor%s sample%d value%s ideal%s',edit,factor,event.at,event.value,ideal))
   if event.at==destination then endpoint=endpoint+1;assert(event.value==96)end
  end
  assert(endpoint==1,'Destination requires exactly one explicit write')
  assert(not mc.channel_is_sliding({number=1},1),'Completed slide retains ownership')
  count=count+1
 end
end
print(string.format('PASS %d live slowdown/acceleration phase cases with continuous interpolation and exact endpoints',count))
