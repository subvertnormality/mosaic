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
