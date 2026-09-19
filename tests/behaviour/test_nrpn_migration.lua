local codec=dofile("lib/devices/nrpn_codec.lua")
local a={id="a",type="midi",nrpn_lsb_mode="standard",params={
 {id="n",nrpn_msb=4,nrpn_lsb=5},{id="unassigned",nrpn_msb=6,nrpn_lsb=7},
 {id="cc",cc_msb=3}}}
local b={id="b",type="midi",nrpn_lsb_mode="legacy-half",params={{id="n",nrpn_msb=1,nrpn_lsb=2}}}
local maps={a=a,b=b}
local function lookup(id)return maps[id] end
local lock={id="n",nrpn_msb=4,nrpn_lsb=5}
local explicit={id="n",nrpn_msb=4,nrpn_lsb=5,nrpn_lsb_mode="standard"}
local cc={id="cc",cc_msb=3}
local undo={id="n",nrpn_msb=4,nrpn_lsb=5}
local state={devices={{device_map="a"},{device_map="b"}},song_patterns={
 {channels={{trig_lock_params={lock,explicit,cc},step_trig_lock_banks={{126,127}}}}}},
 memory={serialized={channels={{buffer={undo}}}}},nrpn_stored_modes={[2]={b={n="standard"}}}}
state.shared=lock;state.cycle=state
assert(codec.migrate(state,lookup)==state)
assert(state.nrpn_policy_version==1)
assert(lock.nrpn_lsb_mode=="legacy-half" and undo.nrpn_lsb_mode=="legacy-half")
assert(explicit.nrpn_lsb_mode=="standard" and cc.nrpn_lsb_mode==nil)
assert(state.song_patterns[1].channels[1].step_trig_lock_banks[1][1]==126)
assert(codec.stored_mode(state,1,a.params[1],a)=="legacy-half")
assert(codec.stored_mode(state,1,a.params[2],a)=="legacy-half")
assert(codec.stored_mode(state,2,b.params[1],b)=="standard")
assert(codec.stored_mode(state,1,b.params[1],b)=="legacy-half")
assert(codec.stored_mode(state,3,a.params[1],a)=="standard")
assert(codec.stored_mode(state,1,a.params[1],a)=="legacy-half")
-- Modern projects and parameters added after migration take declared defaults.
local new={nrpn_policy_version=1,devices={{device_map="a"}}}
codec.migrate(new,lookup)
assert(new.nrpn_stored_modes==nil)
assert(codec.stored_mode(new,1,a.params[1],a)=="standard")
local added={id="later",nrpn_msb=7,nrpn_lsb=8}
a.params[#a.params+1]=added
codec.migrate(state,lookup)
assert(codec.stored_mode(state,1,added,a)=="standard")
assert(state.nrpn_stored_modes[2].b.n=="standard")
assert(not pcall(codec.migrate,{nrpn_policy_version=2},lookup))
assert(not pcall(codec.migrate,{nrpn_msb=0,nrpn_lsb=0,nrpn_lsb_mode="typo"},lookup))
print("PASS NRPN migration: old locks, serialized undo, unassigned controls, explicit choices, numeric preservation, cycles, idempotence, channels/devices, new projects and later parameters")

local missing={devices={{device_map='a'}},nrpn_stored_modes={[1]={a={n='standard'}}}}
codec.migrate(missing,function()return nil end)
assert(codec.stored_mode(missing,1,a.params[1],a)=='standard')
assert(codec.stored_mode(missing,1,a.params[2],a)=='legacy-half')
assert(codec.stored_mode(missing,2,a.params[2],a)=='standard')
local nonmidi={devices={{device_map='voice'}}}
codec.migrate(nonmidi,function()return {id='voice',type='norns'} end)
assert(next(nonmidi.nrpn_stored_modes)==nil)
codec.convert(state,'standard')
assert(lock.nrpn_lsb_mode=='standard' and undo.nrpn_lsb_mode=='standard')
assert(codec.stored_mode(state,1,a.params[1],a)=='standard')
assert(codec.stored_mode(state,2,b.params[1],b)=='standard')
assert(state.song_patterns[1].channels[1].step_trig_lock_banks[1][1]==126)
assert(state.song_patterns[1].channels[1].step_trig_lock_banks[1][2]==127)
codec.convert(state,'legacy-half')
assert(codec.stored_mode(state,1,a.params[1],a)=='legacy-half')
assert(explicit.nrpn_lsb_mode=='legacy-half')
assert(not pcall(codec.convert,state,nil))
assert(not pcall(codec.convert,state,'typo'))
print('PASS missing-map migration isolation, non-MIDI exclusion and explicit bidirectional conversion without numeric changes')
