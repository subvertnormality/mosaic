-- Supplementary pulse-level regression; native MIDI behaviour tests remain required.
-- Run from the repository root: lua tests/behaviour/lattice_duration_contract.lua
util = {clamp=function(x, lo, hi) return math.max(lo, math.min(hi, x)) end}
local serial = 0
fn = {generate_id=function() serial=serial+1; return "action-"..serial end}
local Lattice = dofile(arg[1] or "lib/clock/m_lattice.lua")
-- Independent durations in sixteenth steps, including rounding to a full cycle.
local lengths = {1/24,1/12,1/8,1/6,1/4,1/3,3/8,1/2,5/8,2/3,3/4,5/6,7/8,.99,1,1.25,1.5,1.75,1.99,2,3.25,3.75,4}
for _, tagged in ipairs({false,true}) do
for _, length in ipairs(lengths) do
  local lattice = Lattice:new{auto=false,ppqn=96}
  local tick, fired, scheduled, sprocket = 0, nil, false, nil
  sprocket = lattice:new_sprocket{division=1/16,action=function()
    if not scheduled then
      scheduled=true
      sprocket:set_delayed_action(length,function() fired=tick end,tagged)
    end
  end}
  lattice:start()
  local expected=math.ceil(24*length)
  for i=0,expected+2 do tick=i; lattice:pulse() end
  assert(fired==expected,"length "..length..": expected pulse "..expected..", got "..tostring(fired))
  assert(next(sprocket.delayed_actions)==nil and #sprocket.delayed_action_order==0,"Completed action retained")
end
end
print("46 tagged/untagged fractional/integer pulse-duration and cleanup contracts passed")
