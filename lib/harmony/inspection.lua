local inspection = {}
local registry=rawget(_G,"__mosaic_harmony_inspection")
if not registry then registry={songs=setmetatable({},{__mode="k"})};rawset(_G,"__mosaic_harmony_inspection",registry)end

local function copy(value,seen)
  if type(value)~="table"then return value end;seen=seen or{};if seen[value]then return seen[value]end
  local result={};seen[value]=result;for key,item in pairs(value)do result[copy(key,seen)]=copy(item,seen)end;return result
end
local function channel(song,number)
  local state=registry.songs[song];if not state then state={};registry.songs[song]=state end
  state[number]=state[number]or{next_id=0,events={},by_step={}};return state[number]
end

function inspection.plan(song,number,value)
  local state=channel(song,number);state.next_id=state.next_id+1
  local previous=value.step~=nil and state.by_step[value.step]or nil
  if previous then state.events[previous]=nil end
  value.event_id=state.next_id
  local event={planned=copy(value)}
  state.events[value.event_id]=event
  if value.step~=nil then state.by_step[value.step]=value.event_id end
  state.latest_id=value.event_id
end
function inspection.scheduled(song,number,pitch,source,context)
  local state=channel(song,number);local latest=state.latest_id and state.events[state.latest_id]
  local event=context or(latest and latest.planned)
  local stage={pitch=pitch,source=source,step=event and event.step,status=event and event.status,
    bypass=event and event.bypass,event_id=event and event.event_id}
  local record=event and event.event_id and state.events[event.event_id]
  if record then record.scheduled=stage end
end
function inspection.emitted(song,number,pitch,source,context)
  local state=channel(song,number);local latest=state.latest_id and state.events[state.latest_id]
  local event=context or(latest and latest.planned)
  local stage={pitch=pitch,source=source,step=event and event.step,status=event and event.status,
    bypass=event and event.bypass,event_id=event and event.event_id}
  local record=event and event.event_id and state.events[event.event_id]
  if record then record.emitted=stage end
end
function inspection.snapshot(song,number,step)
  local state=channel(song,number)
  local id;if step~=nil then id=state.by_step[step]else id=state.latest_id end
  return copy(id and state.events[id]or{})
end
function inspection.reset_song(song)registry.songs[song]=nil end
function inspection.reset()for song in pairs(registry.songs)do registry.songs[song]=nil end end
return inspection
