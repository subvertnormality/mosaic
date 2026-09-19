-- README.md Voice leading persistence: old projects remain Off; optional schema
-- is versioned and invalid imports are rejected before active state changes.

local loaded, config = pcall(include, "mosaic/lib/harmony/config")

function test_harmony_config_module_exists()
  luaunit.assert_true(loaded)
end

function test_harmony_config_absence_is_valid_and_does_not_eagerly_write_defaults()
  local song = {channels = {}}
  for channel = 1, 17 do song.channels[channel] = {number = channel} end
  local ok, reason = config.validate_song(song)
  luaunit.assert_true(ok, reason)
  luaunit.assert_nil(song.voicing)
  for channel = 1, 17 do luaunit.assert_nil(song.channels[channel].voicing) end
end

function test_harmony_config_four_part_preset_has_literal_ranges_and_stays_disabled()
  local group = config.four_part_smooth(1, {2, 3, 4, 5})
  luaunit.assert_false(group.enabled)
  luaunit.assert_equals(group.template.offsets, {0, 2, 4})
  luaunit.assert_equals(group.template.required, {true, true, true})
  luaunit.assert_equals(group.roles.bass, {min = 36, max = 55, centre = 43, preferred_leap = 12,
    strict_leap = false, enabled = true})
  luaunit.assert_equals(group.roles.inner1.min, 48)
  luaunit.assert_equals(group.roles.inner2.max, 74)
  luaunit.assert_equals(group.roles.top, {min = 60, max = 81, centre = 69, preferred_leap = 7,
    strict_leap = false, enabled = true})
  luaunit.assert_equals(group.members, {
    {role = "bass", channel = 2}, {role = "inner1", channel = 3},
    {role = "inner2", channel = 4}, {role = "top", channel = 5}
  })
end

function test_harmony_config_rejects_unknown_versions_ranges_and_duplicate_members()
  local song = {channels = {}}
  for channel = 1, 17 do song.channels[channel] = {number = channel} end
  song.voicing = {schema_version = 2, groups = {}}
  luaunit.assert_equals(({config.validate_song(song)})[2], "voicing schema version")

  song.voicing = {schema_version = 1, groups = {[1] = config.four_part_smooth(1, {2, 3, 4, 5})}}
  song.voicing.groups[1].roles.bass.min = 56
  luaunit.assert_equals(({config.validate_song(song)})[2], "group 1 bass range")

  song.voicing.groups[1] = config.four_part_smooth(1, {2, 2, 4, 5})
  luaunit.assert_equals(({config.validate_song(song)})[2], "group 1 duplicate member")
end

function test_harmony_config_rejects_cross_group_claims_track17_and_dangling_channel_modes()
  local song = {channels = {}}
  for channel = 1, 17 do song.channels[channel] = {number = channel} end
  local first = config.new_group(2)
  first.enabled = true
  local second = config.new_group(2)
  second.enabled = true
  song.voicing = {schema_version = 1, groups = {[1] = first, [2] = second}}
  luaunit.assert_equals(({config.validate_song(song)})[2], "channel 2 belongs to multiple groups")

  song.voicing.groups[2] = nil
  first.members[1].channel = 17
  luaunit.assert_equals(({config.validate_song(song)})[2], "group 1 member channel")

  first.members[1].channel = 2
  song.channels[3].voicing = config.new_channel("ensemble")
  song.channels[3].voicing.group_id = 9
  luaunit.assert_equals(({config.validate_song(song)})[2], "channel 3 missing group")
end

function test_harmony_config_pattern_map_accepts_inactive_aliases_and_rejects_invalid_roles()
  local song = {channels = {}}
  for channel = 1, 17 do song.channels[channel] = {number = channel} end
  song.channels[4].voicing = config.new_channel("pattern")
  song.channels[4].voicing.pattern_maps["p1|average"] = {
    schema_version = 1,
    assignments = {["-7"] = "bass", ["0"] = "inner1", ["12"] = "inner1"}
  }
  luaunit.assert_true(config.validate_song(song))
  song.channels[4].voicing.pattern_maps["p1|average"].assignments["3"] = "third"
  luaunit.assert_equals(({config.validate_song(song)})[2], "channel 4 pattern map role")
  song.channels[4].voicing.pattern_maps["p1|average"].assignments["3"]="inner2"
  song.channels[4].voicing.pattern_maps["p1|average"].assignments["14"]="top"
  luaunit.assert_equals(({config.validate_song(song)})[2],"channel 4 pattern map value")
end

function test_harmony_config_rejects_nonzero_root_and_pedals_outside_bass_register()
  local song={channels={}}
  for channel=1,17 do song.channels[channel]={number=channel}end
  local group=config.new_group(2);group.template.offsets[1]=1
  song.voicing={schema_version=1,groups={[1]=group}}
  luaunit.assert_equals(({config.validate_song(song)})[2],"group 1 root offset")
  group.template.offsets[1]=0;group.bass.mode="pedal";group.bass.pedal=80
  luaunit.assert_equals(({config.validate_song(song)})[2],"group 1 pedal range")
end

function test_harmony_config_non_chord_pedal_is_ensemble_only_and_rule_ranges_are_validated()
  local song={channels={}}
  for channel=1,17 do song.channels[channel]={number=channel}end
  song.channels[1].voicing=config.new_channel("revoice")
  song.channels[1].voicing.bass.non_chord_pedal=true
  luaunit.assert_equals(({config.validate_song(song)})[2],"channel 1 bass")
  song.channels[1].voicing.bass.non_chord_pedal=false
  song.channels[1].voicing.upper_spacing=128
  luaunit.assert_equals(({config.validate_song(song)})[2],"channel 1 voicing policy")
end
