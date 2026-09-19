local inspection = {}
local registry=rawget(_G,"__mosaic_harmony_inspection")
if not registry then registry={songs=setmetatable({},{__mode="k"})};rawset(_G,"__mosaic_harmony_inspection",registry)end

local function copy(value,seen)
  if type(value)~="table"then return value end;seen=seen or{};if seen[value]then return seen[value]end
  local result={};seen[value]=result;for key,item in pairs(value)do result[copy(key,seen)]=copy(item,seen)end;return result
end
local function channel(song,number)
  local state=registry.songs[song];if not state then state={};registry.songs[song]=state end
  state[number]=state[number]or{};return state[number]
end

function inspection.plan(song,number,value)channel(song,number).planned=copy(value)end
function inspection.scheduled(song,number,pitch,source,context)
  local state=channel(song,number);local event=context or state.planned
  state.scheduled={pitch=pitch,source=source,step=event and event.step,status=event and event.status,bypass=event and event.bypass}
end
function inspection.emitted(song,number,pitch,source,context)
  local state=channel(song,number);local event=context or state.planned
  state.emitted={pitch=pitch,source=source,step=event and event.step,status=event and event.status,bypass=event and event.bypass}
end
function inspection.snapshot(song,number)return copy(channel(song,number))end
function inspection.reset_song(song)registry.songs[song]=nil end
function inspection.reset()for song in pairs(registry.songs)do registry.songs[song]=nil end end
return inspection
