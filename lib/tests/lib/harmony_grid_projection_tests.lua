-- The Note grid is a read-only view of the last effective event for each
-- channel step.  Its coordinate may change with Harmony, but the owning source
-- value remains the value edited by the existing fader gesture.
local projection=include("mosaic/lib/harmony/grid_projection")
local inspection=include("mosaic/lib/harmony/inspection")
local config=include("mosaic/lib/harmony/config")
local config_state=include("mosaic/lib/harmony/config_state")

local function setup(mode)
  inspection.reset();config_state.reset()
  local song={channels={{voicing=config.new_channel(mode or"pattern")}}}
  local channel=song.channels[1]
  config_state.request_channel(song,1,channel.voicing,false)
  return song,channel
end

function test_harmony_grid_projection_uses_played_harmony_value_without_mutating_source()
  local song,channel=setup("pattern")
  inspection.plan(song,1,{step=2,merge=2,grid={ordinary=2,harmony=-5},status="ok"})
  local source={value=2}
  local value,stage=projection.value(song,1,2,source.value)
  luaunit.assert_equals(value,-5)
  luaunit.assert_equals(stage,"harmony")
  luaunit.assert_equals(source.value,2)
  luaunit.assert_equals(channel.voicing.mode,"pattern")
end

function test_harmony_grid_projection_off_and_bypass_recover_ordinary_value_immediately()
  local song,channel=setup("pattern")
  inspection.plan(song,1,{step=1,merge=0,grid={ordinary=0,harmony=-7},status="ok"})
  channel.voicing.mode="off";config_state.request_channel(song,1,channel.voicing,false)
  luaunit.assert_equals({projection.value(song,1,1,0)},{0,"ordinary"})

  channel.voicing.mode="pattern";config_state.request_channel(song,1,channel.voicing,false)
  inspection.plan(song,1,{step=1,merge=0,grid={ordinary=4,harmony=9},status="note_mask",bypass="note_mask"})
  luaunit.assert_equals({projection.value(song,1,1,0)},{4,"ordinary"})
end

function test_harmony_grid_projection_absent_legacy_config_is_off()
  inspection.reset();config_state.reset()
  local song={channels={{}}}
  inspection.plan(song,1,{step=1,source=0,grid={ordinary=0,harmony=-7},status="ok"})
  luaunit.assert_equals({projection.value(song,1,1,0)},{0,"ordinary"})
end

function test_harmony_grid_projection_rejects_stale_events_and_names_out_of_range()
  local song=setup("pattern")
  inspection.plan(song,1,{step=3,merge=4,grid={ordinary=4,harmony=nil},status="ok"})
  luaunit.assert_equals({projection.value(song,1,3,4)},{nil,"out_of_range"})
  -- A source edit changes the effective merged value before the next played
  -- event.  The old projection must not be flattened into that new source.
  luaunit.assert_equals({projection.value(song,1,3,5)},{5,"source"})
  luaunit.assert_equals({projection.value(song,1,4,6)},{6,"source"})
end

function test_harmony_grid_projection_inverts_only_exact_native_grid_positions()
  local resolver=function(value)local offset=({[0]=0,[1]=2,[2]=4,[3]=5,[4]=7})[value]
    return offset and 60+offset or nil end
  luaunit.assert_equals(projection.capture(2,64,67,resolver),{ordinary=2,harmony=4})
  luaunit.assert_equals(projection.capture(2,64,61,resolver),{ordinary=2})
end
