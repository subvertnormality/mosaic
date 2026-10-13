-- Read-only musical header miniatures. The renderer receives literal poses;
-- clock sampling never starts transport, changes tempo or schedules notes.
local atlas=include("mosaic/lib/ui_mini_atlas")
local M={}
local function finite(v)return type(v)=="number" and v==v and v>=0 and v<math.huge end
function M.beat(mosaic_clock,norns_clock,enabled)
 if not enabled then return nil end
 local playing=false
 if mosaic_clock and type(mosaic_clock.is_playing)=="function" then
  local ok,value=pcall(mosaic_clock.is_playing);if not ok then return nil end
  playing=value==true
 end
 if playing then
  if type(mosaic_clock.get_clock_lattice)~="function" then return nil end
  local ok,lattice=pcall(mosaic_clock.get_clock_lattice)
  if not ok or type(lattice)~="table" or not finite(lattice.transport) or lattice.transport<1
   or not finite(lattice.ppqn) or lattice.ppqn<=0 then return nil end
  return (lattice.transport-1)/lattice.ppqn
 end
 if not norns_clock or type(norns_clock.get_beats)~="function" or type(norns_clock.get_tempo)~="function" then return nil end
 local good_tempo,tempo=pcall(norns_clock.get_tempo)
 if not good_tempo or not finite(tempo) or tempo<=0 then return nil end
 local good_beat,beat=pcall(norns_clock.get_beats)
 return good_beat and finite(beat) and beat or nil
end
function M.pose(id,beat)
 local a=atlas[id];if not a or not finite(beat) then return 0 end
 return math.floor((beat%a.loop)*#a.frames/a.loop)
end
function M.region(id,title_width,layout)
 local a=atlas[id];if not a or not finite(title_width) then return nil end
 local compact=layout=="overview_masks" or layout=="overview_params" or layout=="dashboard"
 local left=compact and 121 or math.max(96,1+title_width+2)
 if a.width>128-left then return nil end
 return {x=128-a.width,y=0,width=a.width,height=8}
end
local cache={}
local levels={a=7,b=11,c=15}
local function runs(id,pose)
 cache[id]=cache[id]or{}
 if cache[id][pose] then return cache[id][pose] end
 local r={[7]={},[11]={},[15]={}}
 for yy,row in ipairs(atlas[id].frames[pose+1])do
  local x=1
  while x<=#row do
   local ch=row:sub(x,x);local next_x=x+1
   while next_x<=#row and row:sub(next_x,next_x)==ch do next_x=next_x+1 end
   if levels[ch] then local group=r[levels[ch]];group[#group+1]={x-1,yy-1,next_x-x}end
   x=next_x
  end
 end
 cache[id][pose]=r;return r
end
function M.draw(id,title_width,layout,beat)
 local region=M.region(id,title_width,layout);if not region then return false end
 local pixels=runs(id,M.pose(id,beat))
 -- Same literal raster as one-pixel fills, grouped into integer horizontal runs.
 for _,level in ipairs({7,11,15})do
  screen.level(level)
  for _,r in ipairs(pixels[level])do screen.rect(region.x+r[1],region.y+r[2],r[3],1);screen.fill()end
 end
 return true,region
end
return M
