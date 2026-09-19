-- README.md Musical Merge / Voice leading persistence: optional requested
-- configuration copies with every song slot, round-trips, and never aliases.
local harmony_config=include("mosaic/lib/harmony/config")
local merge_config=include("mosaic/lib/musical_merge/config")
local validation=include("mosaic/lib/project_validation")

local function configured_source()
  program.init();globals.reset();params.reset();memory.init();program.set_selected_song_pattern(1)
  local song=program.get_song_pattern(1);song.patterns[1].trig_values[1]=1;song.channels[1].selected_patterns[1]=true
  local group=harmony_config.new_group(1);group.enabled=true
  song.voicing={schema_version=1,groups={[7]=group}}
  song.channels[1].voicing=harmony_config.new_channel("ensemble");song.channels[1].voicing.group_id=7
  song.channels[2].musical_merge=merge_config.new();song.channels[2].musical_merge.mode="foundation";song.channels[2].musical_merge.anchor=1
  song.channels[2].selected_patterns[1]=true;song.channels[2].musical_merge.target={kind="chord",group_id=7}
  return song
end

function test_optional_config_copies_independently_through_all_ninety_six_song_slots()
  local source=configured_source()
  for slot=2,96 do program.set_song_pattern(1,slot)end
  local last=program.get_song_pattern(96)
  luaunit.assert_equals(last.voicing.groups[7].members[1].channel,1)
  luaunit.assert_equals(last.channels[2].musical_merge.target.group_id,7)
  last.voicing.groups[7].members[1].channel=3
  last.channels[2].musical_merge.amount=12
  luaunit.assert_equals(source.voicing.groups[7].members[1].channel,1)
  luaunit.assert_equals(source.channels[2].musical_merge.amount,100)
end

function test_optional_config_round_trip_keeps_requested_data_and_omits_transient_frames()
  configured_source();local prepared=program.prepare_for_save();local saved=fn.deep_copy(prepared)
  luaunit.assert_true(validation.check({"fixture",saved}))
  program.set(saved);local restored=program.get_song_pattern(1)
  luaunit.assert_equals(restored.channels[1].voicing.mode,"ensemble")
  luaunit.assert_equals(restored.channels[2].musical_merge.target,{kind="chord",group_id=7})
  luaunit.assert_nil(restored.channels[1].voicing.prepared)
  luaunit.assert_nil(restored.voicing.groups[7].consumed)
end

function test_optional_config_invalid_import_rejects_without_mutating_live_project()
  local live=configured_source();local saved=fn.deep_copy(program.prepare_for_save())
  saved.song_patterns[1].channels[1].voicing.schema_version=99
  local ok,reason=validation.check({"bad",saved})
  luaunit.assert_nil(ok);luaunit.assert_not_nil(reason:match("voicing version"))
  luaunit.assert_is(program.get_song_pattern(1),live)
  luaunit.assert_equals(live.channels[1].voicing.schema_version,1)
end
