-- Independent 14-bit reconstruction: CC6 holds bits7..13, CC38 bits0..6.
-- https://midi.org/midi-1-0-control-change-messages
function include(path) if path == "mosaic/lib/devices/nrpn_codec" then return dofile("lib/devices/nrpn_codec.lua") end return {} end
local midi=dofile("lib/m_midi.lua")
local sent={}
midi_devices[3]={cc=function(_,controller,value,channel)sent[#sent+1]={controller,value,channel} end}
for value=0,16383 do
  sent={};midi.nrpn(4,5,value,16,3)
  assert(#sent==4 and sent[1][1]==99 and sent[1][2]==4 and sent[2][1]==98 and sent[2][2]==5)
  assert(sent[3][1]==6 and sent[4][1]==38)
  for _,packet in ipairs(sent) do assert(packet[3]==16);assert(packet[2]%1==0,"Fractional NRPN data at "..value) end
  assert(sent[3][2]>=0 and sent[3][2]<=127 and sent[4][2]>=0 and sent[4][2]<=127)
  assert(sent[3][2]*128+sent[4][2]==value,"NRPN numeric value changed at "..value)
end
print("PASS all 16384 NRPN values: exact numeric reconstruction, integer bytes, address and channel")

local invalid={
  function()midi.nrpn(4,5,-1,16,3)end,
  function()midi.nrpn(4,5,16384,16,3)end,
  function()midi.nrpn(4,5,0.5,16,3)end,
  function()midi.nrpn(4,5,1,16,3,'unknown')end,
  function()midi.nrpn(nil,5,1,16,3)end,
  function()midi.nrpn(4,nil,1,16,3)end,
  function()midi.nrpn(128,5,1,16,3)end,
  function()midi.nrpn(4,-1,1,16,3)end,
  function()midi.nrpn(4,5.5,1,16,3)end,
  function()midi.nrpn(4,5,1,0,3)end,
  function()midi.nrpn(4,5,1,17,3)end
}
for _,call in ipairs(invalid) do
  sent={};assert(not pcall(call),'Invalid message accepted');assert(#sent==0,'Partial NRPN selection escaped validation')
end
print('PASS invalid NRPN values, modes, addresses and channels emit no partial selection')
