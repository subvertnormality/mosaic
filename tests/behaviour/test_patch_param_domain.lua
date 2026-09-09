local norns_root=assert(arg[1])
package.path=norns_root.."/lua/?.lua;"..norns_root.."/lua/core/?.lua;"..norns_root.."/lua/lib/?.lua;"..package.path
util=require("util");controlspec=require("controlspec")
norns={pmap={data={}}}
local Control=require("params/control")
function include(path)return dofile((path:gsub("^mosaic/",""))..".lua") end
params={lookup={}}
function params:add_group(id,name,count) self.lookup[id]={name=name} end
function params:add_control(id,name,spec) self.lookup[id]=Control.new(id,name,spec) end
function params:lookup_param(id)return assert(self.lookup[id],id) end
function params:set_action(id,action)self:lookup_param(id).action=action end
function params:show(id)end
function params:hide(id)end
local edits=0
channel_edit_page_ui={refresh_trig_lock_values=function()edits=edits+1 end}
function autosave_reset()edits=edits+1 end
_menu={rebuild_params=function()end}
local stock={{id="none"}}
device_map={get_stock_params=function()return stock end}
-- Policy fixture only; MIDI emission and project persistence are separate native tests.
program={get=function()return {nrpn_policy_version=1,nrpn_stored_modes={}} end}
local sent={}
m_midi={cc=function(...)sent[#sent+1]={...} end,nrpn=function(...)sent[#sent+1]={...} end}
local manager=include("mosaic/lib/devices/param_manager");manager.init()
local function configure(minimum,maximum,off,nrpn)
  local val={id="test",name="Test",off_value=off,cc_msb=1,cc_min_value=minimum,cc_max_value=maximum}
  if nrpn then val.nrpn_msb=1;val.nrpn_lsb=2;val.nrpn_min_value=minimum;val.nrpn_max_value=maximum end
  local previous=#sent;manager.add_device_params(1,{type="midi",name="Test",params={val}},7,2,true)
  local p=params:lookup_param("midi_device_params_channel_1_2")
  assert(p:get()==off,"Configured off value was clamped away")
  assert(#sent==previous,"Initialization invoked stale MIDI action")
  return p
end
local p=configure(0,127,-1);p:delta(1);assert(p:get()==0);p:set(-1);assert(p:get()==-1)
for _,off in ipairs({-1,0,200}) do
  p=configure(100,127,off)
  p:set(100);p:delta(-1);assert(p:get()==(off<100 and off or 100))
  p:set(127);p:delta(1);assert(p:get()==(off>127 and off or 127))
  for value=100,127 do p:set(value);assert(p:get()==value,"Numeric persistence roundtrip") end
  local spec=p.controlspec;local copy=spec:copy()
  for i=0,1000 do
    local value=spec:map(i/1000);assert(value==off or value>=100 and value<=127,"Sparse gap exposed")
    assert(copy:map(i/1000)==value,"Copied domain changed")
  end
  for value=1,99 do if value~=off then assert(spec:constrain(value)==100);assert(copy:constrain(value)==100) end end
end
p=configure(100,100,-1);p:delta(1);assert(p:get()==100);p:delta(1);assert(p:get()==100);p:delta(-1);assert(p:get()==-1)
p=configure(0,127,64);p:delta(1);assert(p:get()==65);p:set(63);assert(p:get()==63)
p=configure(0,16383,-1,true)
for _,value in ipairs({0,1,127,128,129,16382,16383,-1}) do p:set(value);assert(p:get()==value) end
-- A reused parameter must not keep the old sparse mapping or MIDI action.
stock={{id="none"},{id="stock",name="Stock",off_value=-1,cc_min_value=-1,cc_max_value=127}}
manager.add_device_params(1,{type="midi",name="Stock",params={}},1,1,true)
p=params:lookup_param("midi_device_params_channel_1_2");local count=#sent;p:delta(1);assert(p:get()==0);assert(#sent==count)
stock={{id="none"}};p=configure(100,127,200);p:set(100);count=#sent
manager.add_device_params(1,nil,1,1,true);assert(#sent==count,"Hiding device emitted its previous MIDI action")
print("PASS actual norns Control/ControlSpec + Mosaic parameter manager: contiguous, sparse, custom-off, singleton, NRPN numeric roundtrip, copying and reuse")

-- Actual official Control objects use the same fine-editor quantum. Expected
-- values enumerate the configured domain, not the implementation's mapping.
local domain=include("mosaic/lib/devices/midi_value_domain")
local positions=0
for _,bounds in ipairs({{0,127,-1},{100,127,-1},{100,127,200},{100,100,-1},{0,127,64},{0,16383,-1}}) do
  local minimum,maximum,off=table.unpack(bounds)
  local control=configure(minimum,maximum,off,maximum>127)
  control.controlspec.quantum=domain.unit_quantum(minimum,maximum,off)
  local values={}
  if off<minimum then values[#values+1]=off end
  for value=minimum,maximum do values[#values+1]=value end
  if off>maximum then values[#values+1]=off end
  control:set(values[1],true)
  for i=2,#values do
    control:delta(1);assert(control:get()==values[i],"Editor skipped value "..values[i]);positions=positions+1
  end
  control:delta(1);assert(control:get()==values[#values],"Upper clamp")
  for i=#values-1,1,-1 do
    control:delta(-1);assert(control:get()==values[i],"Reverse editor skipped value "..values[i]);positions=positions+1
  end
  control:delta(-1);assert(control:get()==values[1],"Lower clamp")
end
print("PASS editor domain forward/reverse "..positions.." positions, including off and singleton bounds")
