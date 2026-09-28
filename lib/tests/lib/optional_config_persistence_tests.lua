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

-- docs/musical-merge-extensions-plan.md §0 Schema and migration (characterisation
-- of the approved plan; README requires only that saved optional configuration
-- round-trips and unknown schemas reject): load v1, save v2, reload v2, with the
-- same working pattern as the v1 configuration built.
local merge_state=include("mosaic/lib/musical_merge/state")
local pattern_module=include("mosaic/lib/pattern")
local transaction=include("mosaic/lib/optional_config_transaction")

local function v1_with_unknown_keys(mode)
  return {schema_version=1,mode=mode,anchor=1,amount=65,accent=80,gap=1,seed=2024,ranking_version=1,cycles=2,
    shape="build",percentages={50,100},variation="per_phrase",keep_anchor_pitch=true,
    target={kind="degrees",degrees={1,3},group_id=9,note="nested unknown"},
    unknown_top={deep={1}},interlock={leader=2,window=9},space=true,fragments={size=5},structure="anchors"}
end

local function merged(song)
  local channel=song.channels[2]
  local result=pattern_module.get_and_merge_patterns(2,channel.trig_merge_mode,channel.note_merge_mode,
    channel.velocity_merge_mode,channel.length_merge_mode,song)
  if result.foundation then result.foundation.config=nil end
  return result
end

local function v1_project(mode)
  program.init();globals.reset();params.reset();memory.init();program.set_selected_song_pattern(1);merge_state.reset()
  local song=program.get_song_pattern(1)
  for _,step in ipairs({1,5,9,13})do song.patterns[1].trig_values[step]=1 end
  for _,step in ipairs({2,3,6,7,10,11,14,15})do song.patterns[2].trig_values[step]=1;song.patterns[2].note_values[step]=step end
  song.channels[2].selected_patterns={[1]=true,[2]=true}
  song.channels[2].musical_merge=v1_with_unknown_keys(mode)
  return song
end

function test_optional_config_v1_load_save_v2_reload_keeps_pattern_values()
  for _,mode in ipairs({"foundation","off"})do
    local v1_song=v1_project(mode);local baseline=merged(v1_song)
    local saved=fn.deep_copy(program.prepare_for_save())
    luaunit.assert_equals(saved.song_patterns[1].channels[2].musical_merge.schema_version,1)
    luaunit.assert_true(validation.check({"v1",saved}));luaunit.assert_true(validation.migrate({"v1",saved}))
    merge_state.reset();program.set(saved);program.set_selected_song_pattern(1)
    local loaded=program.get_song_pattern(1);local config=loaded.channels[2].musical_merge
    luaunit.assert_equals(config,merge_config.canonicalize(v1_with_unknown_keys(mode)))
    luaunit.assert_equals(config.interlock,{window=0});luaunit.assert_equals(config.fragments,{size=8,keep_anchor=false})
    luaunit.assert_equals(merged(loaded),baseline,mode)
    local resaved=fn.deep_copy(program.prepare_for_save())
    luaunit.assert_equals(resaved.song_patterns[1].channels[2].musical_merge.schema_version,2)
    luaunit.assert_true(validation.check({"v2",resaved}));luaunit.assert_true(validation.migrate({"v2",resaved}))
    merge_state.reset();program.set(resaved);program.set_selected_song_pattern(1)
    local reloaded=program.get_song_pattern(1)
    luaunit.assert_equals(reloaded.channels[2].musical_merge,config)
    luaunit.assert_equals(merged(reloaded),baseline,mode)
  end
end

function test_optional_config_absent_merge_stays_absent_through_v2_round_trip()
  local song=v1_project("off");song.channels[2].musical_merge=nil;local baseline=merged(song)
  local saved=fn.deep_copy(program.prepare_for_save())
  luaunit.assert_true(validation.check({"absent",saved}));luaunit.assert_true(validation.migrate({"absent",saved}))
  merge_state.reset();program.set(saved);program.set_selected_song_pattern(1)
  local loaded=program.get_song_pattern(1)
  for number=1,17 do luaunit.assert_nil(loaded.channels[number].musical_merge) end
  luaunit.assert_equals(merged(loaded),baseline)
end

function test_optional_config_transaction_and_history_store_canonical_merge()
  configured_source();local song=program.get_song_pattern(1)
  local before=transaction.snapshot(song);local after=transaction.copy(before)
  after.channels[3].musical_merge=v1_with_unknown_keys("off")
  luaunit.assert_true(memory.record_optional_config(1,{3},before,after,"channel"))
  local canonical=merge_config.canonicalize(v1_with_unknown_keys("off"))
  luaunit.assert_equals(song.channels[3].musical_merge,canonical)
  memory.undo(3);luaunit.assert_nil(song.channels[3].musical_merge)
  memory.redo(3);luaunit.assert_equals(song.channels[3].musical_merge,canonical)
  local bad=transaction.snapshot(song);bad.channels[4].musical_merge=merge_config.new();bad.channels[4].musical_merge.extra=1
  luaunit.assert_equals({memory.record_optional_config(1,{4},transaction.snapshot(song),bad,"channel")},{nil,"merge field"})
  luaunit.assert_nil(song.channels[4].musical_merge)
end
