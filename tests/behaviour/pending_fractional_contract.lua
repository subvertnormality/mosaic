-- Musical rational bounds are independent of a particular rounding origin.
-- Reset equality supplements these bounds; it is not the sole oracle.
util={clamp=function(n,a,b) return math.max(a,math.min(b,n)) end}
local id=0;fn={generate_id=function() id=id+1;return id end}
local Lattice=dofile(arg[1] or 'lib/clock/m_lattice.lua')
local checked=0;local windows=0;local gates=0
for _,ratio in ipairs({{3,2},{240,53},{24,5},{120,13},{240,13},{312,5},{636,5}}) do
 local p,q=ratio[1],ratio[2];local period=p/q
 local function run(start_phase,length,reset_offsets,expected_start)
  local lattice=Lattice:new{auto=false,ppqn=96};local now=0;local onsets={};local fired={};local start;local s
  lattice:new_sprocket{division=1/384,order=1,action=function()
   if start then
    for _,offset in ipairs(reset_offsets) do
     if now==start+offset then lattice:realign_eligable_sprockets() end
    end
   end
  end}
  s=lattice:new_sprocket{division=period/384,realign=true,order=2,action=function()
   onsets[#onsets+1]=now
   if not start and #onsets==start_phase+1 then
    start=now
    s:set_delayed_action(length,function() fired[#fired+1]=now end,true)
   end
  end}
  lattice:start()
  local cycles=math.max(start_phase+math.ceil(length)+4,q*3+2)
  for tick=0,math.ceil(cycles*period)+10 do now=tick;lattice:pulse() end
  assert(start and #fired==1,'Missing or duplicate pending deadline')
  if expected_start then assert(start==expected_start,'Reset fixture changed note origin') end
  assert(not s._pending_clocks or #s._pending_clocks==0,'Completed pending group leaked')
  return start,fired[1],onsets
 end
 -- Full rational windows and bounded phase independently constrain the base
 -- clock, including every possible rounding phase within the denominator.
 local _,_,trace=run(0,18,{})
 for n=2,#trace do
  local gap=trace[n]-trace[n-1]
  assert(gap==math.floor(period) or gap==math.ceil(period),'Nonmusical fractional interval')
  assert(math.abs(trace[n]-trace[1]-(n-1)*period)<1.000000001,'Unbounded fractional phase')
  if n>q then
   assert(trace[n]-trace[n-q]==p,'Complete rational window drift')
   windows=windows+1
  end
 end
 for phase=0,q-1 do
  for _,length in ipairs({.5,1,1.5,2,2.25,3,8.5,18,q+1,128}) do
   local start,deadline=run(phase,length,{})
   local elapsed=deadline-start
   -- Integer gates follow whole cycle boundaries (<one pulse phase error).
   -- Fractional gates additionally round upward within their last cycle.
   local bound=length%1==0 and 1.000000001 or 2.000000001
   assert(math.abs(elapsed-length*period)<bound,'Pending deadline violates musical bound')
   gates=gates+1
   for _,offsets in ipairs({{1},{math.max(1,elapsed-1)},{1,math.max(2,math.floor(elapsed/2)),math.max(3,elapsed-1)},{elapsed,elapsed+1}}) do
    local _,actual=run(phase,length,offsets,start)
    assert(actual==deadline,string.format('Reset changed deadline p=%s q=%s phase=%s length=%s expected=%s actual=%s',p,q,phase,length,deadline,actual))
    checked=checked+1
   end
  end
 end
end
print(string.format('%s exact reset/no-reset comparisons, %s independent pending musical bounds, %s complete rational windows passed',checked,gates,windows))
