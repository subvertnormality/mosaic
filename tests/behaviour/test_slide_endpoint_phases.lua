-- Actual lattice and slide scheduler, literal interpolation and endpoint rules.
util={clamp=function(v,a,b)return math.max(a,math.min(b,v))end}
program={};function include()return {clock_divisions={}}end
local Lattice=dofile('lib/clock/m_lattice.lua')
local function up(fn,name)
 for i=1,100 do local k,v=debug.getupvalue(fn,i);if k==name then return v end;if not k then break end end
 error('Missing actual scheduler upvalue '..name)
end
local function check(division,swing,length,offset,distance,target)
 local mc=dofile('lib/clock/m_clock.lua');up(mc.init,'init_ring_buffer')()
 local sample=up(mc.init,'process_ring_buffer');local l=Lattice:new{auto=false,ppqn=96,pattern_length=length};clock_lattice=l
 local events,onsets={},{};local s
 local function emit(v,last)if v~=last then events[#events+1]={time=l.transport,value=v} end end
 s=l:new_sprocket{division=division,swing=swing,order=2,action=function(t)
   onsets[#onsets+1]=t
   if #onsets==1 then
     emit(24);mc.execute_action_across_steps_by_pulses{channel_number=1,trig_lock=1,start_step=1,end_step=(distance==64 and 1 or distance+1),distance=distance,start_value=24,end_value=target,quant=1,func=emit}
   elseif #onsets==distance+1 then
     if not mc.handoff_spread_lock(1,1,(distance==64 and 1 or distance+1),target) then emit(target) end
     assert(not mc.channel_is_sliding({number=1},1),'Endpoint retains slide ownership')
   end
 end};mc.channel_1_clock=s
 l:new_sprocket{division=1/48,order=5,delay_offset=offset,action=sample};l.enabled=true
 local ticks=0;while #onsets<distance+3 do l:pulse();ticks=ticks+1;assert(ticks<10000) end
 local start,finish=onsets[1],onsets[distance+1];local endpoint=0
 for _,e in ipairs(events)do
   assert(e.time<=finish,'Stale write after destination')
   if e.time==finish then assert(e.value==target);endpoint=endpoint+1 end
   local ideal=24+(target-24)*(e.time-start)/(finish-start)
   assert(math.abs(e.value-ideal)<=.50000001,'Interpolation does not follow actual musical elapsed pulses')
 end
 assert(endpoint==1,'Destination lock must write exactly once before its note even if rounding reached target early')
end
local total,failed=0,0
for _,division in ipairs({1/16,1/56,1/224})do for _,swing in ipairs({-50,0,50})do
 for _,length in ipairs({3,4})do for offset=0,7 do for _,distance in ipairs({1,3,64})do for _,target in ipairs({25,96})do
   total=total+1;local ok,err=pcall(check,division,swing,length,offset,distance,target)
   if not ok then failed=failed+1;if failed<=12 then print(string.format('FAIL div=%s swing=%d len=%d phase=%d distance=%d target=%d: %s',division,swing,length,offset,distance,target,tostring(err)))end end
 end end end end
end end
print(string.format('Collected %d phase/interpolation cases; passed %d; failed %d',total,total-failed,failed));os.exit(failed==0 and 0 or 1)
