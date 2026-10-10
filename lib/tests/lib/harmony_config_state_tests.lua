-- README.md Voice leading lifecycle: applied Harmony changes are immediate while
-- stopped, queued atomically while playing, and latest-confirmed wins at boundary.

local state = include("mosaic/lib/harmony/config_state")
local config = include("mosaic/lib/harmony/config")

function test_harmony_config_state_queue_coalesces_and_activates_at_pattern_boundary()
  state.reset()
  local song = {}
  local off = config.new_channel("off")
  luaunit.assert_equals(state.effective_channel(song, 1, off).mode, "off")
  local revoice = config.new_channel("revoice")
  luaunit.assert_equals(state.request_channel(song, 1, revoice, true), "queued")
  local pattern = config.new_channel("pattern")
  state.request_channel(song, 1, pattern, true)
  luaunit.assert_equals(state.effective_channel(song, 1, off).mode, "off")
  state.on_pattern_boundary(song)
  luaunit.assert_equals(state.effective_channel(song, 1, off).mode, "pattern")
end

function test_harmony_config_state_stop_activates_latest_requested_for_next_start()
  state.reset()
  local song, off = {}, config.new_channel("off")
  state.effective_channel(song, 2, off)
  state.request_channel(song, 2, config.new_channel("revoice"), true)
  state.stop(song)
  luaunit.assert_equals(state.effective_channel(song, 2, off).mode, "revoice")
  luaunit.assert_nil(state.status(song, 2).queued)
end

function test_harmony_config_state_stopped_apply_is_immediate_and_isolated()
  state.reset()
  local a, b = {}, {}
  state.request_channel(a, 1, config.new_channel("ensemble"), false)
  luaunit.assert_equals(state.effective_channel(a, 1, config.new_channel()).mode, "ensemble")
  luaunit.assert_equals(state.effective_channel(b, 1, config.new_channel()).mode, "off")
end

function test_harmony_config_state_song_groups_share_the_pattern_boundary_transaction()
  state.reset()
  local song={}
  local off={schema_version=1,groups={}}
  luaunit.assert_equals(state.effective_song(song,off).groups,{})
  local requested={schema_version=1,groups={[3]=config.new_group(2)}}
  luaunit.assert_equals(state.request_song(song,requested,true),"queued")
  luaunit.assert_nil(state.effective_song(song,off).groups[3])
  state.on_pattern_boundary(song)
  luaunit.assert_not_nil(state.effective_song(song,off).groups[3])
end

function test_harmony_config_state_is_shared_across_norns_include_callers()
  local writer=include("mosaic/lib/harmony/config_state")
  local reader=include("mosaic/lib/harmony/config_state")
  writer.reset();local song={};local off=config.new_channel("off")
  reader.effective_channel(song,4,off)
  writer.request_channel(song,4,config.new_channel("pattern"),true)
  luaunit.assert_equals(reader.effective_channel(song,4,off).mode,"off")
  reader.on_pattern_boundary(song)
  luaunit.assert_equals(writer.effective_channel(song,4,off).mode,"pattern")
end

function test_harmony_config_state_song_entry_uses_serialized_requested_snapshot()
  state.reset();local song={channels={},voicing={schema_version=1,groups={}}}
  for number=1,16 do song.channels[number]={}end
  local old=config.new_channel("off");state.effective_channel(song,1,old)
  song.channels[1].voicing=config.new_channel("revoice")
  state.enter_song(song)
  luaunit.assert_equals(state.effective_channel(song,1,old).mode,"revoice")
  luaunit.assert_nil(state.status(song,1).queued)
end
