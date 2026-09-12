local root=assert(arg[1])
local environment=setmetatable({include=function() return {} end,
 scheduler=assert(loadfile(root..'/lib/scheduler.lua'))(),midi={vports={1}},
 fn=assert(loadfile(root..'/lib/helpers/functions.lua'))()},{__index=_G})
environment.include=function(name)
 if name=='mosaic/lib/devices/midi_wire_output' or name=='mosaic/lib/devices/nrpn_codec' then
  return assert(loadfile(root..'/'..name:gsub('^mosaic/', '')..'.lua','t',environment))()
 end
 return {}
end
local implementation=assert(loadfile(root..'/lib/m_midi.lua','t',environment))()
local sent={}
environment.midi_devices[1]={device={},
 note_off=function(_,note,velocity,channel) table.insert(sent,{128+channel-1,note,velocity}) end,
 note_on=function(_,note,velocity,channel) table.insert(sent,{144+channel-1,note,velocity}) end}
implementation.panic()
for _=1,32 do environment.scheduler.update() end
assert(sent[#sent][2]==31,'Sweep must already have cleared pitch24')
implementation:note_on(24,100,1,1)
local onset=#sent
implementation:note_on(100,90,1,1)
local future_onset=#sent
for _=1,110 do environment.scheduler.update() end
assert(sent[#sent][2]==127,'Complete the sweep after the new onset')
local future_releases=0
for i=future_onset+1,#sent do if sent[i][1]==128 and sent[i][2]==100 then future_releases=future_releases+1 end end
assert(future_releases==1,"The later sweep position must release the newer high note")
local before_stop=#sent
implementation:all_notes_off()
local releases=0
for i=onset+1,#sent do if sent[i][1]==128 and sent[i][2]==24 then releases=releases+1 end end
print(string.format('onset=%d sweep_end=%d after_stop=%d releases_after_onset=%d',onset,before_stop,#sent,releases))
assert(releases==1,'Stop cleanup lost the live note played after its panic sweep position')

assert(#sent==before_stop+1 and sent[#sent][1]==128 and sent[#sent][2]==24,"Stop must not retain a note already swept")
print("Live-note ownership contract passed: behind sweep retained, ahead swept, exact Stop release")
