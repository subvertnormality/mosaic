-- Actual MIDI panic implementation and coroutine scheduler; output device spies only.
local root = arg[1] or "."
local function scenario(repeat_during, repeat_after, disconnected, background_jobs)
  background_jobs=background_jobs or 0
  local environment = setmetatable({include=function() return {} end,
    scheduler=assert(loadfile(root.."/lib/scheduler.lua"))(),
    midi={vports={1,2,3}}}, {__index=_G})
  environment.include=function(name)
    if name=='mosaic/lib/devices/midi_wire_output' or name=='mosaic/lib/devices/nrpn_codec' or name=='mosaic/lib/devices/midi_input' then
      return assert(loadfile(root..'/'..name:gsub('^mosaic/', '')..'.lua','t',environment))()
    end
    return {}
  end
  local implementation=assert(loadfile(root.."/lib/m_midi.lua","t",environment))()
  local sent={{},{},{}}
  for id=1,3 do
    local port=id
    environment.midi_devices[id]={device=id~=disconnected and {} or nil,
      note_off=function(_,note,velocity,channel)
        assert(note>=0 and note<=127 and velocity==0 and channel>=1 and channel<=16)
        table.insert(sent[port],{note,velocity,channel})
      end}
  end
  for _=1,background_jobs do
    environment.scheduler.start(coroutine.create(function() while true do coroutine.yield() end end))
  end
  local function check_counts(stage)
    local actual=0
    for _,job in pairs(environment.scheduler.coroutines) do if job.active then actual=actual+1 end end
    assert(environment.scheduler.active_count==actual,"Scheduler counter mismatch "..stage..": "..environment.scheduler.active_count.."/"..actual)
  end
  implementation.panic()
  check_counts("initial panic")
  local prefix=0
  if repeat_during then
    for _=1,20 do environment.scheduler.update() end
    prefix=320;implementation.panic()
  end
  for _=1,130 do environment.scheduler.update() end
  if repeat_after then
    implementation.panic()
    check_counts("completed repeat")
    for _=1,130 do environment.scheduler.update() end
  end
  for port=1,3 do
    local expected=port==disconnected and 0 or prefix+2048*(repeat_after and 2 or 1)
    assert(#sent[port]==expected,string.format("port%d: got%d expected%d",port,#sent[port],expected))
    if expected>0 then
      for i=1,2048 do
        local event=sent[port][#sent[port]-2048+i]
        assert(event[1]==math.floor((i-1)/16) and event[2]==0 and event[3]==(i-1)%16+1)
      end
    end
  end
  check_counts("final drain")
  assert(environment.scheduler.active_count==background_jobs,"Panic coroutine leaked")
end
scenario(false,false,nil)
scenario(true,false,nil)
scenario(false,true,nil)
scenario(false,false,2)
scenario(false,true,nil,4)
print("5 panic scheduler scenarios passed, including completed repeat with persistent background jobs")
