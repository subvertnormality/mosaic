-- Supplementary cache/render contract; native screen and MIDI tests are required.
grid_abstraction=dofile('lib/grid_abstraction.lua');grid_abstraction.init()
local channels={}
for n=1,16 do
  channels[n]={cells={}}
  for step=n,65-n do channels[n].cells[step]=(step%3==0) and 15 or 2 end
end
program={get=function() return {selected_song_pattern=1} end,
  get_channel=function(_,channel) return channels[channel] end}
fn={dirty_screen=function() end}
sequencer={new=function() return {draw=function(_,channel,emit)
  for step,level in pairs(channel.cells) do emit((step-1)%16+1,math.floor((step-1)/16)+4,level) end
end} end}
local px,py,level,dots
screen={move=function(x,y) px=x;py=y end,level=function(v) level=v end,font_size=function() end,
  text=function(s) if s=='.' then dots[px..':'..py]=level end end}
local Viewer=dofile(arg[1] or 'lib/ui_components/grid_viewer.lua')
local viewer=Viewer:new(0,3)
local checked=0
for _,direction in ipairs({1,-1,1,-1}) do
  for index=1,16 do
    local channel=direction==1 and index or 17-index
    viewer.selected_channel=channel;dots={};viewer:draw()
    for step=1,64 do
      local x=(step-1)%16+1;local y=math.floor((step-1)/16)+4
      local expected=channels[channel].cells[step] or 0
      assert(dots[(-3+x*7)..':'..(-2+y*7)]==expected,'Stale rendered cell '..step..' on channel '..channel)
      checked=checked+1
    end
  end
end
-- Shrink the same channel without changing selection, including an empty frame.
for _,cells in ipairs({{[1]=15,[4]=2},{},{[64]=15}}) do
  channels[1].cells=cells;viewer.selected_channel=1;dots={};viewer:draw()
  for step=1,64 do
    local x=(step-1)%16+1;local y=math.floor((step-1)/16)+4
    assert(dots[(-3+x*7)..':'..(-2+y*7)]==(cells[step] or 0),'Stale shrunken/empty cell')
    checked=checked+1
  end
end
print(checked..' rendered-cell refresh checks passed')
