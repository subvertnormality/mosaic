local inspection=include("mosaic/lib/harmony/inspection")
local config_state=include("mosaic/lib/harmony/config_state")

local projection={}
local GRID_LOW,GRID_HIGH=-7,13

local function inverse(pitch,resolver,anchor)
  if pitch==nil or type(resolver)~="function"then return nil end
  local best,best_distance
  for value=GRID_LOW,GRID_HIGH do
    local ok,resolved=pcall(resolver,value)
    if ok and resolved==pitch then
      local distance=math.abs(value-(anchor or value))
      if best==nil or distance<best_distance or(distance==best_distance and value<best)then
        best,best_distance=value,distance
      end
    end
  end
  return best
end

-- Capture grid coordinates while playback still owns the complete effective
-- scale/lock context.  Redraw never invokes the solver or advances musical
-- state; it only reads this immutable event result.
function projection.capture(source_value,ordinary_pitch,harmony_pitch,resolver)
  local ordinary
  if type(source_value)=="number"then
    local ok,resolved=pcall(resolver,source_value)
    if ok and resolved==ordinary_pitch and source_value>=GRID_LOW and source_value<=GRID_HIGH then
      ordinary=source_value
    end
  end
  ordinary=ordinary or inverse(ordinary_pitch,resolver,source_value)
  local harmony
  if harmony_pitch==ordinary_pitch then harmony=ordinary
  else harmony=inverse(harmony_pitch,resolver,ordinary or source_value)end
  return{ordinary=ordinary,harmony=harmony}
end

-- effective_source is the current channel-merge value and source_value is the
-- cell the existing Note fader edits.  A mismatch makes a played record stale;
-- source editing is shown directly until that changed event is played again.
function projection.value(song,channel_number,step,effective_source,source_value)
  source_value=source_value==nil and effective_source or source_value
  local event=inspection.snapshot(song,channel_number,step)
  local planned=event.planned
  local planned_source=planned and(planned.source~=nil and planned.source or planned.merge)
  if not planned or type(planned.grid)~="table"or
      (planned_source~=nil and effective_source~=nil and planned_source~=effective_source)then
    return source_value,"source"
  end
  local channel=song and song.channels and song.channels[channel_number]
  local active=config_state.effective_channel(song,channel_number,channel and channel.voicing or{})
  if not active or active.mode==nil or active.mode=="off"or planned.bypass then
    if planned.grid.ordinary==nil then return nil,"out_of_range"end
    return planned.grid.ordinary,"ordinary"
  end
  if planned.grid.harmony==nil then return nil,"out_of_range"end
  return planned.grid.harmony,"harmony"
end

projection.bounds=function()return GRID_LOW,GRID_HIGH end
return projection
