function include(name) if name == "mosaic/lib/devices/param_slots" then return dofile("lib/devices/param_slots.lua") end assert(name == "mosaic/lib/devices/nrpn_codec"); return dofile("lib/devices/nrpn_codec.lua") end
-- Focused routing contract; native behaviour tests separately prove the UI path.
local recall=dofile("lib/devices/midi_patch_recall.lua")
local devices={}
for i=1,16 do devices[i]={device_map="none",midi_channel=i,midi_device=1} end
program={get=function()return {devices=devices} end}
local definitions={
  a={type="midi",params={
    {id="cc",cc_msb=1,cc_max_value=127},
    {id="off",cc_msb=2,cc_max_value=127,off_value=200},
    {id="pair",cc_msb=3,cc_lsb=35,cc_max_value=16383,channel=16},
    {id="nrpn",nrpn_msb=4,nrpn_lsb=5,nrpn_max_value=16383,channel=2},
    {id="none"},{id="stock",param_type="stock"}}},
  b={type="midi",params={{id="cc",cc_msb=7,cc_max_value=127,off_value=0}}},
  n={type="norns",params={{id="audio"}}}}
device_map={get_device=function(id)return definitions[id] end,get_stock_params=function()return {{id="none"},{id="stock"}} end}
devices[1]={device_map="a",midi_channel=7,midi_device=3}
devices[16]={device_map="b",midi_channel=12,midi_device=2}
devices[2].device_map="n"
local values={midi_device_params_channel_1_3=63,midi_device_params_channel_1_4=200,
  midi_device_params_channel_1_5=129,midi_device_params_channel_1_6=16383,
  midi_device_params_channel_16_3=1}
params={get=function(_,id)return assert(values[id],"Unexpected parameter read: "..id) end}
local sent={}
m_midi={cc=function(a,b,v,c,d)sent[#sent+1]=table.concat({"cc",a,b or "nil",v,c,d},":") end,
  nrpn=function(a,b,v,c,d)sent[#sent+1]=table.concat({"nrpn",a,b,v,c,d},":") end}
local expected={"cc:1:nil:63:7:3","cc:3:35:129:16:3","nrpn:4:5:16383:2:3","cc:7:nil:1:12:2"}
for repetition=1,2 do
  recall.send()
  assert(#sent==4*repetition,"Missing or extra recalled values")
  for i=1,4 do assert(sent[(repetition-1)*4+i]==expected[i],sent[(repetition-1)*4+i]) end
end
-- Routes are resolved afresh; no cached port/channel or parameter action.
devices[1].midi_channel=4;devices[1].midi_device=2
values.midi_device_params_channel_1_3=-1
values.midi_device_params_channel_1_5=-1
values.midi_device_params_channel_1_6=-1
values.midi_device_params_channel_16_3=0
sent={};recall.send();assert(#sent==0,"Off parameters emitted MIDI")
values.midi_device_params_channel_1_3=0
recall.send();assert(#sent==1 and sent[1]=="cc:1:nil:0:4:2","Fresh route or zero value lost")
print("PASS patch recall: all-channel enumeration, stock/none/norns exclusion, custom/default off, zero, repeated recall, current ports/channels and parameter overrides")
