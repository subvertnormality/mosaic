util={clamp=function(n,a,b) return math.max(a,math.min(b,n)) end}
local id=0;fn={generate_id=function() id=id+1;return id end}
function include(path) return dofile(path:gsub('^mosaic/','')..'.lua') end
local channel={number=1}
program={get=function() return {selected_song_pattern=1} end,get_channel=function() return channel end,
 get_effective_swing=function() return 0 end,get_effective_swing_shuffle_type=function() return 1 end,
 get_effective_shuffle_basis=function() return 0 end,get_effective_shuffle_feel=function() return 0 end,get_effective_shuffle_amount=function() return 0 end}
local Lattice=dofile('lib/clock/m_lattice.lua');local checked=0;local failures=0
for _,period in ipairs({24,216,408,240/53,24/5,120/13}) do
 for _,division in ipairs({.25,.5,1,2}) do
  for _,length in ipairs({.5,1,2,4}) do
   dofile(arg[1] or 'lib/clock/m_clock.lua')
   clock_lattice=Lattice:new{auto=false,ppqn=96}
   local now=0;local seen={};local first=true
   m_clock.channel_1_clock=clock_lattice:new_sprocket{division=period/384,order=2,action=function()
    if first then first=false;m_clock.new_arp_sprocket(1,division,0,1,length,function() seen[#seen+1]=now end) end
   end}
   clock_lattice:start();for tick=0,math.ceil(period*(length+5))+10 do now=tick;clock_lattice:pulse() end
   local interval=math.max(1,period*division)
   local bad
   for n,tick in ipairs(seen) do
    if math.abs(tick-n*interval)>1.00000001 then bad='phase '..tick..' expected near '..n*interval;break end
    if period%1==0 and interval%1==0 and tick~=n*interval then bad='integer phase';break end
   end
   if period%1==0 then
    local expected=math.max(0,math.ceil(period*length/interval)-1)
    if #seen~=expected then bad='count '..#seen..' expected '..expected end
   end
   if bad then failures=failures+1;print(string.format('period=%s division=%s length=%s: %s',period,division,length,bad)) end
   checked=checked+1
  end
 end
end
print(string.format('%s failures / %s actual m_clock+lattice arp cadence cases',failures,checked))
os.exit(failures==0 and 0 or 1)
