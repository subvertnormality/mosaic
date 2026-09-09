-- Future occurrence projection versus actual native lattice callbacks.
util={clamp=function(v,a,b)return math.max(a,math.min(b,v))end}
local Lattice=dofile('lib/clock/m_lattice.lua')
local checked=0
for _,division in ipairs({1/16,1/56,1/224,1/384}) do
 for _,swing in ipairs({-50,0,50}) do
  for _,length in ipairs({3,4}) do
   local l=Lattice:new{auto=false,ppqn=96,pattern_length=length}
   local pending={};local clock;local armed=false;local creating=true
   local function query()
    if not armed or not creating then return end
    for distance=1,4 do
     local phase,carry,step=clock.phase,clock.ppqn_error,clock.step
     local target=(clock.onset_count or 0)+distance
     local delay=clock:project_onset_occurrence(target)
     assert(clock.phase==phase and clock.ppqn_error==carry and clock.step==step,'Projection mutated live timing')
     pending[#pending+1]={at=l.transport,target=target,delay=delay}
    end
   end
   clock=l:new_sprocket{division=division,order=2,action=function(t)
    for index=#pending,1,-1 do
     local request=pending[index]
     if request.target==clock.onset_count then
      assert(t-request.at==request.delay,string.format('Future onset mismatch division=%s swing=%s length=%s phase-delay=%s actual=%s',division,swing,length,request.delay,t-request.at))
      checked=checked+1;table.remove(pending,index)
     end
    end
    query()
   end}
   l:new_sprocket{division=1/384,order=3,action=query}
   l.enabled=true
   for pulse=1,600 do
    l:pulse()
    if pulse==17 then clock:set_division(division*2);clock:set_swing(swing);armed=true end
    if pulse==117 then creating=false end
    query()
   end
   assert(#pending==0,'Unresolved future onset observations')
  end
 end
end
print(string.format('PASS %d future-onset predictions at and between steps after live division/swing changes',checked))
