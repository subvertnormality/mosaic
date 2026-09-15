-- Musical callback ordering contract; native user-input/MIDI tests are primary.
util = {clamp=function(x,lo,hi) return math.max(lo,math.min(hi,x)) end}
local serial=0
fn={generate_id=function() serial=serial+1;return "order-"..serial end}
local Lattice=dofile(arg[1] or "lib/clock/m_lattice.lua")
local lattice=Lattice:new{auto=false,ppqn=96}
local tick=0
local order={}
local sprocket
sprocket=lattice:new_sprocket{division=1/16,action=function()
  table.insert(order,"on:"..tick)
  if tick==0 then
    -- A note release and a strummed note share the next step deadline.
    -- Release must precede retrigger; strum must see the new step's scale.
    sprocket:set_delayed_action(1,function() table.insert(order,"release:"..tick) end,true)
    sprocket:set_delayed_action(1,function() table.insert(order,"strum:"..tick) end)
  elseif tick==24 then
    sprocket:set_delayed_action(0,function() table.insert(order,"immediate:"..tick) end)
  end
end}
lattice:start()
for i=0,24 do tick=i;lattice:pulse() end
local actual=table.concat(order,",")
assert(actual=="on:0,release:24,on:24,strum:24,immediate:24",actual)
assert(next(sprocket.delayed_actions)==nil and #sprocket.delayed_action_order==0)
print("Boundary release precedes onset; strum and new immediate action follow onset; cleanup complete")
