-- Actual scheduler/lattice; model dependency supplies a literal channel range.
util={clamp=function(v,a,b)return math.max(a,math.min(b,v))end}
program={get=function()return {selected_song_pattern=1}end,get_channel=function()return {number=1}end,get_channel_step_bounds=function()return 1,4 end}
function include()return {clock_divisions={}}end
local Lattice=dofile('lib/clock/m_lattice.lua')
local function up(fn,name)
 for i=1,100 do local key,value=debug.getupvalue(fn,i);if key==name then return value end;if not key then break end end
 error('Missing actual scheduler upvalue '..name)
end
local mc=dofile('lib/clock/m_clock.lua');up(mc.init,'init_ring_buffer')()
local sample=up(mc.init,'process_ring_buffer')
local l=Lattice:new{auto=false,ppqn=96,pattern_length=4};clock_lattice=l
local events={};local initial=true;local reset=false;local after_reset=0;local destination
local function emit(value,last)if value~=last then events[#events+1]={at=l.transport,value=value}end end
local channel=l:new_sprocket{division=1/16,order=2,realign=true,action=function(t)
 if initial then
  initial=false;emit(24)
  mc.execute_action_across_steps_by_pulses{channel_number=1,trig_lock=1,start_step=4,end_step=3,distance=3,start_value=24,end_value=96,quant=1,func=emit}
 elseif reset then
  after_reset=after_reset+1
  if after_reset==3 then
   destination=t
   if not mc.handoff_spread_lock(1,1,3,96) then emit(96) end
  end
 end
end};mc.channel_1_clock=channel
channel.end_of_clock_processor=l:new_sprocket{division=1/16,order=4,realign=true,action=function()end}
l:new_sprocket{division=1/48,order=5,action=sample};l.enabled=true
for pulse=1,150 do
 if l.transport==37 then mc.set_channel_division(1,2);reset=true;mc.realign_sprockets() end
 l:pulse()
end
assert(destination==133,'Reset step1 at37 then step3 at133')
local failures=0;local endpoint=0
for _,event in ipairs(events)do
 local ideal=event.at<=37 and (24+event.at-1) or (60+(event.at-37)*36/96)
 if event.at>destination or math.abs(event.value-ideal)>.50000001 then
  failures=failures+1;print(string.format('FAIL pulse=%s value=%s expected=%s',event.at,event.value,ideal))
 end
 if event.at==destination then endpoint=endpoint+1;assert(event.value==96)end
end
assert(endpoint==1,'Exactly one endpoint at reset destination')
print(string.format('Reset ownership: checked%d emissions; failed%d',#events,failures));os.exit(failures==0 and 0 or 1)
