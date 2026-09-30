local range_validation = include("mosaic/lib/project_validation")

local function range_saved_fixture()
  local channels = {}
  for i=1,17 do channels[i]={start_trig={1,4},end_trig={16,7}} end
  return {"fixture", {song_patterns={[1]={global_pattern_length=64,channels=channels}}}}
end

function test_saved_range_validation_all_endpoint_pairs()
  local saved=range_saved_fixture();local channel=saved[2].song_patterns[1].channels[1]
  for first=1,64 do
    for last=1,64 do
      channel.start_trig={((first-1)%16)+1,math.floor((first-1)/16)+4}
      channel.end_trig={((last-1)%16)+1,math.floor((last-1)/16)+4}
      local start_ref,end_ref=channel.start_trig,channel.end_trig
      local valid,reason=range_validation.check(saved)
      luaunit.assert_equals(valid==true,first<=last)
      if first>last then luaunit.assert_equals(reason,"Slot 1 ch 1 reversed") end
      luaunit.assert_is(channel.start_trig,start_ref);luaunit.assert_is(channel.end_trig,end_ref)
    end
  end
end

function test_saved_range_validation_invalid_coordinates_and_types()
  local invalid={false,true,"1",{},-math.huge,math.huge,0/0,-1,0,1.5,17}
  for _,field in ipairs({"start_trig","end_trig"}) do
    for _,value in ipairs(invalid) do
      local saved=range_saved_fixture();saved[2].song_patterns[1].channels[1][field]={value,4}
      luaunit.assert_nil(range_validation.check(saved))
    end
    for _,value in ipairs({false,true,"4",{},-math.huge,math.huge,0/0,0,3,4.5,8}) do
      local saved=range_saved_fixture();saved[2].song_patterns[1].channels[1][field]={1,value}
      luaunit.assert_nil(range_validation.check(saved))
    end
    for _,value in ipairs({false,true,"table",3,{},{1},{[2]=4}}) do
      local saved=range_saved_fixture();saved[2].song_patterns[1].channels[1][field]=value
      luaunit.assert_nil(range_validation.check(saved))
    end
    local saved=range_saved_fixture();saved[2].song_patterns[1].channels[1][field]=nil
    luaunit.assert_nil(range_validation.check(saved))
  end
end

function test_saved_range_validation_global_lengths_and_inactive_scale()
  for _,value in ipairs({false,true,"1",{},-math.huge,math.huge,0/0,-1,0,1.5,65}) do
    local saved=range_saved_fixture();saved[2].song_patterns[1].global_pattern_length=value
    luaunit.assert_nil(range_validation.check(saved))
  end
  local saved=range_saved_fixture();saved[2].song_patterns[1].global_pattern_length=nil
  luaunit.assert_nil(range_validation.check(saved))
  for length=1,64 do
    saved=range_saved_fixture();saved[2].song_patterns[1].global_pattern_length=length
    saved[2].song_patterns[1].channels[1].start_trig={15,7}
    luaunit.assert_true(range_validation.check(saved)) -- Endpoint64 may exceed cap.
  end
  saved=range_saved_fixture();saved[2].song_patterns[64]=range_saved_fixture()[2].song_patterns[1]
  saved[2].song_patterns[64].channels[17].start_trig={16,7}
  saved[2].song_patterns[64].channels[17].end_trig={15,7}
  local valid,reason=range_validation.check(saved)
  luaunit.assert_nil(valid);luaunit.assert_equals(reason,"Slot 64 ch 17 reversed")
end

function test_saved_range_validation_sparse_legacy_and_containers()
  local saved=range_saved_fixture();local songs=saved[2].song_patterns
  saved[2].sequencer_patterns=songs;saved[2].song_patterns=nil
  luaunit.assert_true(range_validation.check(saved))
  luaunit.assert_nil(saved[2].song_patterns);luaunit.assert_is(saved[2].sequencer_patterns,songs)
  luaunit.assert_true(range_validation.check({"sparse",{song_patterns={}}}))
  for _,value in ipairs({false,true,1,"project",{}}) do luaunit.assert_nil(range_validation.check(value)) end
  luaunit.assert_nil(range_validation.check(nil))
  for _,where in ipairs({"song","channels","channel"}) do
    saved=range_saved_fixture()
    if where=="song" then saved[2].song_patterns[1]=false
    elseif where=="channels" then saved[2].song_patterns[1].channels=false
    else saved[2].song_patterns[1].channels[17]=nil end
    luaunit.assert_nil(range_validation.check(saved))
  end
end


function test_saved_range_validation_all_96_song_slots()
  for slot=1,96 do
    local saved=range_saved_fixture();local song=saved[2].song_patterns[1]
    saved[2].song_patterns={[slot]=song}
    luaunit.assert_true(range_validation.check(saved))
    song.channels[17].start_trig={4,4};song.channels[17].end_trig={2,4}
    local valid,reason=range_validation.check(saved)
    luaunit.assert_nil(valid);luaunit.assert_equals(reason,"Slot "..slot.." ch 17 reversed")
  end
  for _,slot in ipairs({0,97,-1,1.5,"1"}) do
    local saved=range_saved_fixture();saved[2].song_patterns={[slot]=saved[2].song_patterns[1]}
    luaunit.assert_nil(range_validation.check(saved))
  end
end

function test_saved_optional_harmony_and_merge_schemas_are_validated_without_mutation()
  local harmony=include("mosaic/lib/harmony/config")
  local merge=include("mosaic/lib/musical_merge/config")
  local saved=range_saved_fixture();local song=saved[2].song_patterns[1]
  song.voicing={schema_version=1,groups={[1]=harmony.new_group(2)}}
  song.channels[2].voicing=harmony.new_channel("ensemble")
  song.channels[2].voicing.group_id=1
  song.channels[2].musical_merge=merge.new()
  luaunit.assert_true(range_validation.check(saved))

  local before=song.channels[2].musical_merge
  song.channels[2].musical_merge.schema_version=99
  local valid,reason=range_validation.check(saved)
  luaunit.assert_nil(valid);luaunit.assert_equals(reason,"Slot 1 merge schema version")
  luaunit.assert_is(song.channels[2].musical_merge,before)

  song.channels[2].musical_merge=merge.new()
  song.voicing.schema_version=99
  valid,reason=range_validation.check(saved)
  luaunit.assert_nil(valid);luaunit.assert_equals(reason,"Slot 1 voicing schema version")
end

function test_saved_chord_target_rejects_a_dangling_harmony_material_source()
  local merge=include("mosaic/lib/musical_merge/config")
  local saved=range_saved_fixture();local song=saved[2].song_patterns[1]
  song.channels[1].musical_merge=merge.new()
  song.channels[1].musical_merge.target={kind="chord",group_id=4}
  local valid,reason=range_validation.check(saved)
  luaunit.assert_nil(valid);luaunit.assert_equals(reason,"Slot 1 ch 1 merge target group missing")
end

-- README "Musical Merge and Voice Leading": unknown schema versions reject the
-- project before it replaces the active project. The v1 -> v2 canonical
-- migration on detached decoded data is docs/musical-merge-extensions-plan.md §0
-- (characterisation of the approved plan).
local function v1_merge(extra)
  local value={schema_version=1,mode="foundation",anchor=2,amount=40,accent=90,gap=1,seed=99,ranking_version=1,
    cycles=2,shape="answer",percentages={100,25},variation="fixed",keep_anchor_pitch=false,target={kind="legacy"}}
  for key,item in pairs(extra or{})do value[key]=item end
  return value
end

function test_saved_v1_merge_validates_and_migrates_detached_data_to_canonical_v2()
  local merge=include("mosaic/lib/musical_merge/config")
  local saved=range_saved_fixture();local song=saved[2].song_patterns[1]
  song.channels[3].musical_merge=v1_merge({interlock="collides",unknown={1},target={kind="legacy",extra=true}})
  song.channels[4].musical_merge=v1_merge({mode="off"})
  luaunit.assert_true(range_validation.check(saved))
  local expected=merge.canonicalize(v1_merge())
  luaunit.assert_true(range_validation.migrate(saved))
  luaunit.assert_equals(song.channels[3].musical_merge,expected)
  local off=merge.new();off.cycles,off.shape,off.percentages=2,"answer",{100,25};off.amount,off.accent,off.gap,off.seed,off.anchor=40,90,1,99,2
  luaunit.assert_equals(song.channels[4].musical_merge,off)
  luaunit.assert_nil(song.channels[5].musical_merge)
  -- Migration is idempotent and the migrated data is valid v2.
  luaunit.assert_true(range_validation.check(saved))
  luaunit.assert_true(range_validation.migrate(saved))
  luaunit.assert_equals(song.channels[3].musical_merge,expected)
end

function test_saved_v2_merge_rejects_unknown_keys_and_self_leaders_before_migration()
  local merge=include("mosaic/lib/musical_merge/config")
  local saved=range_saved_fixture();local song=saved[2].song_patterns[1]
  song.channels[6].musical_merge=merge.new();song.channels[6].musical_merge.fragments.extra=1
  local before=song.channels[6].musical_merge
  luaunit.assert_equals({range_validation.check(saved)},{nil,"Slot 1 merge fragments"})
  luaunit.assert_is(song.channels[6].musical_merge,before)
  song.channels[6].musical_merge=merge.new();song.channels[6].musical_merge.interlock.leader=6
  luaunit.assert_equals({range_validation.check(saved)},{nil,"Slot 1 merge interlock"})
  song.channels[6].musical_merge.interlock.leader=5
  luaunit.assert_true(range_validation.check(saved))
  song.channels[6].musical_merge=v1_merge({amount=101})
  luaunit.assert_equals({range_validation.check(saved)},{nil,"Slot 1 merge amount"})
  luaunit.assert_equals({range_validation.migrate(saved)},{nil,"Slot 1 merge amount"})
end
