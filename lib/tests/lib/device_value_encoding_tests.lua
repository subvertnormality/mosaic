-- Unit tests for the MIDI device value path:
--   lib/devices/nrpn_codec.lua        (NRPN value encoding and LSB-mode policy)
--   lib/devices/midi_value_domain.lua (numeric ranges with a separate Off position)
--   lib/devices/midi_patch_recall.lua (stored device controls sent on Play)
--
-- Labelling: an assertion whose expected value follows from the MIDI 1.0
-- specification says so. Every other expectation is marked "characterisation":
-- current behaviour pinned so a refactor cannot change it silently, not a claim
-- that a manual or README states it.

local nrpn_codec = include("mosaic/lib/devices/nrpn_codec")
local midi_value_domain = include("mosaic/lib/devices/midi_value_domain")
local midi_patch_recall = include("mosaic/lib/devices/midi_patch_recall")

-- midi_value_domain reads the norns `controlspec` global at call time. The unit
-- runner does not install it, so load the pinned norns core module and install
-- it only for the duration of one test.
local norns_controlspec = dofile("./test_artefacts/norns_test_artefact/lua/core/controlspec.lua")

local function with_controlspec(run)
  local original = controlspec
  controlspec = norns_controlspec
  local ok, err = pcall(run)
  controlspec = original
  if not ok then error(err, 0) end
end

local EPSILON = 1e-12

local function assert_close(actual, expected)
  luaunit.assert_almost_equals(actual, expected, EPSILON)
end

local function assert_encodes(value, mode, expected_msb, expected_lsb)
  local msb, lsb = nrpn_codec.encode(value, mode)
  luaunit.assert_equals({msb, lsb}, {expected_msb, expected_lsb},
    "encode("..tostring(value)..", "..tostring(mode)..")")
end

----------------------------------------------------------------------------
-- nrpn_codec.resolve
----------------------------------------------------------------------------

-- characterisation: precedence is explicit override > parameter > device > "standard".
function test_nrpn_codec_resolve_prefers_override_then_parameter_then_device()
  local parameter = {nrpn_lsb_mode = "legacy-half"}
  local device = {nrpn_lsb_mode = "legacy-half"}
  luaunit.assert_equals(nrpn_codec.resolve("standard", parameter, device), "standard")
  luaunit.assert_equals(nrpn_codec.resolve(nil, {nrpn_lsb_mode = "standard"}, device), "standard")
  luaunit.assert_equals(nrpn_codec.resolve(nil, parameter, {nrpn_lsb_mode = "standard"}), "legacy-half")
  luaunit.assert_equals(nrpn_codec.resolve(nil, {}, {nrpn_lsb_mode = "legacy-half"}), "legacy-half")
  luaunit.assert_equals(nrpn_codec.resolve(nil, {}, {nrpn_lsb_mode = "standard"}), "standard")
  luaunit.assert_equals(nrpn_codec.resolve("legacy-half", {nrpn_lsb_mode = "standard"}, nil), "legacy-half")
end

-- characterisation: with no mode anywhere (and nil parameter/device) the default is "standard".
function test_nrpn_codec_resolve_defaults_to_standard()
  luaunit.assert_equals(nrpn_codec.resolve(), "standard")
  luaunit.assert_equals(nrpn_codec.resolve(nil, nil, nil), "standard")
  luaunit.assert_equals(nrpn_codec.resolve(nil, {}, {}), "standard")
  luaunit.assert_equals(nrpn_codec.resolve(nil, nil, {}), "standard")
end

-- characterisation: only the two named modes are accepted, wherever they come from.
function test_nrpn_codec_resolve_rejects_unknown_modes_from_every_source()
  luaunit.assert_error_msg_contains("Unknown NRPN LSB mode: bogus",
    nrpn_codec.resolve, "bogus")
  luaunit.assert_error_msg_contains("Unknown NRPN LSB mode: Standard",
    nrpn_codec.resolve, "Standard")
  luaunit.assert_error_msg_contains("Unknown NRPN LSB mode: half",
    nrpn_codec.resolve, nil, {nrpn_lsb_mode = "half"})
  luaunit.assert_error_msg_contains("Unknown NRPN LSB mode: legacy",
    nrpn_codec.resolve, nil, {}, {nrpn_lsb_mode = "legacy"})
  -- false is not nil, so it is not "absent": it is an unknown mode.
  luaunit.assert_error_msg_contains("Unknown NRPN LSB mode: false",
    nrpn_codec.resolve, false, {nrpn_lsb_mode = "standard"})
end

----------------------------------------------------------------------------
-- nrpn_codec.encode
----------------------------------------------------------------------------

-- MIDI 1.0 NRPN data entry: the 14-bit value is sent as Data Entry MSB (CC 6)
-- = value >> 7 and Data Entry LSB (CC 38) = value & 0x7F. encode returns that
-- (msb, lsb) pair in "standard" mode.
function test_nrpn_codec_encode_standard_splits_fourteen_bits_into_msb_and_lsb()
  assert_encodes(0, "standard", 0, 0)
  assert_encodes(1, "standard", 0, 1)
  assert_encodes(127, "standard", 0, 127)
  assert_encodes(128, "standard", 1, 0)
  assert_encodes(129, "standard", 1, 1)
  assert_encodes(300, "standard", 2, 44)
  assert_encodes(8191, "standard", 63, 127)
  assert_encodes(8192, "standard", 64, 0)
  assert_encodes(16256, "standard", 127, 0)
  assert_encodes(16383, "standard", 127, 127)
end

-- MIDI 1.0 split as above; characterisation: a nil mode resolves to "standard".
function test_nrpn_codec_encode_without_mode_uses_standard_split()
  assert_encodes(0, nil, 0, 0)
  assert_encodes(255, nil, 1, 127)
  assert_encodes(16383, nil, 127, 127)
end

-- characterisation: legacy-half keeps the MSB split but halves only an EVEN low
-- byte and sends 0 for an ODD one (documented in nrpn_codec.lua as preserving the
-- historical norns serializer bytes, where a fractional x.5 became 0).
function test_nrpn_codec_encode_legacy_half_halves_even_lsb_and_zeroes_odd_lsb()
  assert_encodes(0, "legacy-half", 0, 0)
  assert_encodes(1, "legacy-half", 0, 0)
  assert_encodes(2, "legacy-half", 0, 1)
  assert_encodes(3, "legacy-half", 0, 0)
  assert_encodes(126, "legacy-half", 0, 63)
  assert_encodes(127, "legacy-half", 0, 0)
  assert_encodes(128, "legacy-half", 1, 0)
  assert_encodes(129, "legacy-half", 1, 0)
  assert_encodes(130, "legacy-half", 1, 1)
  assert_encodes(300, "legacy-half", 2, 22)
  assert_encodes(8191, "legacy-half", 63, 0)
  assert_encodes(8192, "legacy-half", 64, 0)
  assert_encodes(16382, "legacy-half", 127, 63)
  assert_encodes(16383, "legacy-half", 127, 0)
end

-- characterisation: every even low byte maps to lsb/2 and every odd one to 0, and
-- the MSB is identical in both modes, across the whole 14-bit range.
function test_nrpn_codec_encode_modes_agree_on_msb_across_full_range()
  for value = 0, 16383 do
    local standard_msb, standard_lsb = nrpn_codec.encode(value, "standard")
    local legacy_msb, legacy_lsb = nrpn_codec.encode(value, "legacy-half")
    luaunit.assert_equals(standard_msb, value // 128)
    luaunit.assert_equals(standard_lsb, value % 128)
    luaunit.assert_equals(legacy_msb, standard_msb)
    if standard_lsb % 2 == 0 then
      luaunit.assert_equals(legacy_lsb, standard_lsb // 2)
    else
      luaunit.assert_equals(legacy_lsb, 0)
    end
  end
end

-- characterisation: an integral float is accepted and encodes like its integer.
function test_nrpn_codec_encode_accepts_integral_floats()
  assert_encodes(128.0, "standard", 1, 0)
  assert_encodes(16383.0, "standard", 127, 127)
  assert_encodes(254.0, "legacy-half", 1, 63)
end

-- MIDI 1.0: an NRPN value is 14 bits, 0..16383. characterisation: anything else,
-- including non-integers and non-numbers, is refused with this message.
function test_nrpn_codec_encode_rejects_values_outside_fourteen_bit_integers()
  local message = "NRPN value must be an integer from 0 to 16383"
  for _, bad in ipairs({-1, 16384, -0.5, 0.5, 1.5, 16382.5, math.huge, -math.huge, 0/0}) do
    luaunit.assert_error_msg_contains(message, nrpn_codec.encode, bad, "standard")
    luaunit.assert_error_msg_contains(message, nrpn_codec.encode, bad, "legacy-half")
  end
  luaunit.assert_error_msg_contains(message, nrpn_codec.encode, "64", "standard")
  luaunit.assert_error_msg_contains(message, nrpn_codec.encode, nil, "standard")
  luaunit.assert_error_msg_contains(message, nrpn_codec.encode, true)
end

-- characterisation: the mode is validated before the value.
function test_nrpn_codec_encode_rejects_unknown_mode_before_value()
  luaunit.assert_error_msg_contains("Unknown NRPN LSB mode: half", nrpn_codec.encode, 64, "half")
  luaunit.assert_error_msg_contains("Unknown NRPN LSB mode: half", nrpn_codec.encode, -1, "half")
end

----------------------------------------------------------------------------
-- nrpn_codec.stored_mode
----------------------------------------------------------------------------

-- characterisation: with nothing stored, stored_mode falls back to resolve().
function test_nrpn_codec_stored_mode_falls_back_to_parameter_device_and_default()
  local device = {id = "synth"}
  luaunit.assert_equals(nrpn_codec.stored_mode({}, 1, {id = "cutoff"}, device), "standard")
  luaunit.assert_equals(nrpn_codec.stored_mode({}, 1, {id = "cutoff", nrpn_lsb_mode = "legacy-half"}, device),
    "legacy-half")
  luaunit.assert_equals(nrpn_codec.stored_mode({}, 1, {id = "cutoff"}, {id = "synth", nrpn_lsb_mode = "legacy-half"}),
    "legacy-half")
  luaunit.assert_equals(nrpn_codec.stored_mode({nrpn_stored_modes = {}}, 1, {id = "cutoff"}, device), "standard")
  luaunit.assert_equals(nrpn_codec.stored_mode({nrpn_stored_modes = {[1] = {}}}, 1, {id = "cutoff"}, device),
    "standard")
  luaunit.assert_equals(nrpn_codec.stored_mode({nrpn_stored_modes = {[1] = {synth = {}}}}, 1, {id = "cutoff"}, device),
    "standard")
end

-- characterisation: a stored entry is scoped by channel, device id AND parameter id.
function test_nrpn_codec_stored_mode_is_scoped_by_channel_device_and_parameter()
  local data = {nrpn_stored_modes = {[2] = {synth = {cutoff = "legacy-half"}}}}
  local parameter = {id = "cutoff"}
  luaunit.assert_equals(nrpn_codec.stored_mode(data, 2, parameter, {id = "synth"}), "legacy-half")
  luaunit.assert_equals(nrpn_codec.stored_mode(data, 3, parameter, {id = "synth"}), "standard")
  luaunit.assert_equals(nrpn_codec.stored_mode(data, 2, parameter, {id = "other"}), "standard")
  luaunit.assert_equals(nrpn_codec.stored_mode(data, 2, {id = "resonance"}, {id = "synth"}), "standard")
  -- Without a device there is no device scope, so nothing stored applies.
  luaunit.assert_equals(nrpn_codec.stored_mode(data, 2, parameter, nil), "standard")
end

-- characterisation: per-parameter entry > device "*" entry > parameter/device mode.
function test_nrpn_codec_stored_mode_uses_wildcard_after_exact_parameter()
  local data = {nrpn_stored_modes = {[4] = {synth = {["*"] = "legacy-half", cutoff = "standard"}}}}
  local device = {id = "synth", nrpn_lsb_mode = "standard"}
  luaunit.assert_equals(nrpn_codec.stored_mode(data, 4, {id = "cutoff"}, device), "standard")
  luaunit.assert_equals(nrpn_codec.stored_mode(data, 4, {id = "resonance"}, device), "legacy-half")
  luaunit.assert_equals(nrpn_codec.stored_mode(data, 4, {id = "resonance", nrpn_lsb_mode = "standard"}, device),
    "legacy-half")
end

-- characterisation: a stored override beats the parameter's own mode.
function test_nrpn_codec_stored_mode_override_beats_parameter_mode()
  local data = {nrpn_stored_modes = {[1] = {synth = {cutoff = "standard"}}}}
  luaunit.assert_equals(
    nrpn_codec.stored_mode(data, 1, {id = "cutoff", nrpn_lsb_mode = "legacy-half"}, {id = "synth"}), "standard")
end

-- characterisation: an invalid stored mode is refused rather than ignored.
function test_nrpn_codec_stored_mode_rejects_invalid_stored_value()
  local data = {nrpn_stored_modes = {[1] = {synth = {cutoff = "halved"}}}}
  luaunit.assert_error_msg_contains("Unknown NRPN LSB mode: halved",
    nrpn_codec.stored_mode, data, 1, {id = "cutoff"}, {id = "synth"})
end

----------------------------------------------------------------------------
-- nrpn_codec.migrate
----------------------------------------------------------------------------

local function recording_get_device(devices_by_id)
  local calls = {}
  local function get_device(id)
    calls[#calls + 1] = id == nil and "<nil>" or id
    return devices_by_id[id]
  end
  return get_device, calls
end

local function sorted(list)
  local copy = {}
  for i, v in ipairs(list) do copy[i] = v end
  table.sort(copy)
  return copy
end

-- characterisation: an already-versioned project is returned untouched and no
-- device lookup happens.
function test_nrpn_codec_migrate_leaves_version_one_projects_untouched()
  local assignment = {nrpn_msb = 1, nrpn_lsb = 2}
  local data = {nrpn_policy_version = 1, lock = assignment, devices = {[1] = {device_map = "synth"}}}
  local get_device, calls = recording_get_device({})
  local result = nrpn_codec.migrate(data, get_device)
  luaunit.assert_is(result, data)
  luaunit.assert_nil(assignment.nrpn_lsb_mode)
  luaunit.assert_nil(data.nrpn_stored_modes)
  luaunit.assert_equals(data.nrpn_policy_version, 1)
  luaunit.assert_equals(calls, {})
end

-- characterisation: any version other than nil or 1 is refused.
function test_nrpn_codec_migrate_rejects_unsupported_policy_versions()
  for _, version in ipairs({0, 2, "1", false}) do
    luaunit.assert_error_msg_contains("Unsupported NRPN policy version",
      nrpn_codec.migrate, {nrpn_policy_version = version})
  end
end

-- characterisation: every table carrying BOTH nrpn_msb and nrpn_lsb, however deep
-- (song state, undo history), defaults to legacy-half; explicit modes survive and
-- tables missing either address byte are not touched.
function test_nrpn_codec_migrate_marks_unversioned_nrpn_assignments_legacy_half()
  local unmarked = {nrpn_msb = 0, nrpn_lsb = 74}
  local explicit = {nrpn_msb = 1, nrpn_lsb = 2, nrpn_lsb_mode = "standard"}
  local explicit_legacy = {nrpn_msb = 1, nrpn_lsb = 3, nrpn_lsb_mode = "legacy-half"}
  local msb_only = {nrpn_msb = 5}
  local lsb_only = {nrpn_lsb = 6}
  local cc = {cc_msb = 74}
  local deep = {nrpn_msb = 9, nrpn_lsb = 10}
  local data = {
    songs = {{channels = {{trig_lock_params = {unmarked, explicit, explicit_legacy, msb_only, lsb_only, cc}}}}},
    undo_stack = {{{{deep}}}},
  }
  local result = nrpn_codec.migrate(data)
  luaunit.assert_is(result, data)
  luaunit.assert_equals(unmarked, {nrpn_msb = 0, nrpn_lsb = 74, nrpn_lsb_mode = "legacy-half"})
  luaunit.assert_equals(explicit.nrpn_lsb_mode, "standard")
  luaunit.assert_equals(explicit_legacy.nrpn_lsb_mode, "legacy-half")
  luaunit.assert_equals(msb_only, {nrpn_msb = 5})
  luaunit.assert_equals(lsb_only, {nrpn_lsb = 6})
  luaunit.assert_equals(cc, {cc_msb = 74})
  luaunit.assert_equals(deep.nrpn_lsb_mode, "legacy-half")
  luaunit.assert_equals(data.nrpn_policy_version, 1)
  luaunit.assert_equals(data.nrpn_stored_modes, {})
end

-- characterisation: shared and cyclic tables are visited once and migration ends.
function test_nrpn_codec_migrate_terminates_on_shared_and_cyclic_tables()
  local assignment = {nrpn_msb = 3, nrpn_lsb = 4}
  assignment.self = assignment
  local data = {a = assignment, b = {assignment, {back = nil}}}
  data.b[2].back = data
  nrpn_codec.migrate(data)
  luaunit.assert_equals(assignment.nrpn_lsb_mode, "legacy-half")
  luaunit.assert_equals(data.nrpn_policy_version, 1)
end

-- characterisation: an invalid mode found in an assignment is refused.
function test_nrpn_codec_migrate_rejects_invalid_assignment_mode()
  local data = {lock = {nrpn_msb = 1, nrpn_lsb = 2, nrpn_lsb_mode = "odd"}}
  luaunit.assert_error_msg_contains("Unknown NRPN LSB mode: odd", nrpn_codec.migrate, data)
end

-- characterisation: for each routed MIDI device the NRPN parameters (both address
-- bytes present) are recorded legacy-half per parameter id; existing entries and
-- other devices' entries survive; non-MIDI devices, "none" and nil maps get nothing;
-- a missing map gets a device-scoped "*" legacy-half fallback. get_device receives
-- each route's device_map.
function test_nrpn_codec_migrate_records_stored_modes_per_routed_device()
  local synth = {id = "synth", type = "midi", params = {
    {id = "cutoff", nrpn_msb = 0, nrpn_lsb = 74},
    {id = "resonance", nrpn_msb = 0, nrpn_lsb = 71},
    {id = "level", cc_msb = 7},
    {id = "msb_only", nrpn_msb = 1},
    {id = "lsb_only", nrpn_lsb = 1},
  }}
  local voice = {id = "voice", type = "norns", params = {{id = "x", nrpn_msb = 1, nrpn_lsb = 2}}}
  local get_device, calls = recording_get_device({synth = synth, voice = voice})
  local data = {
    devices = {
      [1] = {device_map = "synth"},
      [2] = {device_map = "voice"},
      [3] = {device_map = "none"},
      [4] = {device_map = "missing_map"},
      [5] = {},
    },
    nrpn_stored_modes = {[1] = {synth = {resonance = "standard"}, other = {x = "standard"}}},
  }
  nrpn_codec.migrate(data, get_device)
  luaunit.assert_equals(data.nrpn_stored_modes, {
    [1] = {synth = {cutoff = "legacy-half", resonance = "standard"}, other = {x = "standard"}},
    [4] = {missing_map = {["*"] = "legacy-half"}},
  })
  luaunit.assert_equals(sorted(calls), {"<nil>", "missing_map", "none", "synth", "voice"})
  luaunit.assert_equals(data.nrpn_policy_version, 1)
  -- The device map itself is not project data and is not rewritten.
  luaunit.assert_nil(synth.params[1].nrpn_lsb_mode)
end

-- characterisation: an existing "*" fallback for a missing map is kept.
function test_nrpn_codec_migrate_keeps_existing_missing_map_fallback()
  local data = {
    devices = {[1] = {device_map = "gone"}},
    nrpn_stored_modes = {[1] = {gone = {["*"] = "standard", cutoff = "legacy-half"}}},
  }
  nrpn_codec.migrate(data, function() return nil end)
  luaunit.assert_equals(data.nrpn_stored_modes, {[1] = {gone = {["*"] = "standard", cutoff = "legacy-half"}}})
end

-- characterisation: without a get_device function every non-"none" map is treated
-- as missing and receives the "*" fallback.
function test_nrpn_codec_migrate_without_device_lookup_uses_wildcard_fallback()
  local data = {devices = {[1] = {device_map = "synth"}, [2] = {device_map = "none"}}}
  nrpn_codec.migrate(data)
  luaunit.assert_equals(data.nrpn_stored_modes, {[1] = {synth = {["*"] = "legacy-half"}}})
end

-- characterisation: an invalid mode already stored for a MIDI parameter is refused.
function test_nrpn_codec_migrate_rejects_invalid_stored_parameter_mode()
  local synth = {id = "synth", type = "midi", params = {{id = "cutoff", nrpn_msb = 0, nrpn_lsb = 74}}}
  local data = {devices = {[1] = {device_map = "synth"}},
    nrpn_stored_modes = {[1] = {synth = {cutoff = "sideways"}}}}
  luaunit.assert_error_msg_contains("Unknown NRPN LSB mode: sideways",
    nrpn_codec.migrate, data, function() return synth end)
end

-- characterisation: an invalid "*" fallback already stored for a missing map is refused.
function test_nrpn_codec_migrate_rejects_invalid_stored_wildcard_mode()
  local data = {devices = {[1] = {device_map = "gone"}},
    nrpn_stored_modes = {[1] = {gone = {["*"] = "sideways"}}}}
  luaunit.assert_error_msg_contains("Unknown NRPN LSB mode: sideways",
    nrpn_codec.migrate, data, function() return nil end)
end

-- characterisation: after migration, stored_mode answers legacy-half for a migrated
-- NRPN parameter and still "standard" for a parameter migration did not record.
function test_nrpn_codec_migrate_then_stored_mode_round_trip()
  local synth = {id = "synth", type = "midi", params = {
    {id = "cutoff", nrpn_msb = 0, nrpn_lsb = 74}, {id = "level", cc_msb = 7}}}
  local data = {devices = {[3] = {device_map = "synth"}}}
  nrpn_codec.migrate(data, function(id) return id == "synth" and synth or nil end)
  luaunit.assert_equals(nrpn_codec.stored_mode(data, 3, synth.params[1], synth), "legacy-half")
  luaunit.assert_equals(nrpn_codec.stored_mode(data, 3, synth.params[2], synth), "standard")
  luaunit.assert_equals(nrpn_codec.stored_mode(data, 2, synth.params[1], synth), "standard")
end

----------------------------------------------------------------------------
-- nrpn_codec.convert
----------------------------------------------------------------------------

-- characterisation: the mode argument is mandatory and validated, and the version
-- checked, before any mutation.
function test_nrpn_codec_convert_refuses_before_mutating()
  local assignment = {nrpn_msb = 1, nrpn_lsb = 2}
  local data = {lock = assignment}
  luaunit.assert_error_msg_contains("An explicit NRPN mode is required", nrpn_codec.convert, data)
  luaunit.assert_error_msg_contains("An explicit NRPN mode is required", nrpn_codec.convert, data, nil)
  luaunit.assert_error_msg_contains("Unknown NRPN LSB mode: both", nrpn_codec.convert, data, "both")
  luaunit.assert_equals(data, {lock = {nrpn_msb = 1, nrpn_lsb = 2}})
  local future = {nrpn_policy_version = 2, lock = assignment}
  luaunit.assert_error_msg_contains("Unsupported NRPN policy version", nrpn_codec.convert, future, "standard")
  luaunit.assert_nil(assignment.nrpn_lsb_mode)
  luaunit.assert_nil(future.nrpn_stored_modes)
  luaunit.assert_equals(future.nrpn_policy_version, 2)
end

-- characterisation: convert overwrites every assignment mode, collapses every
-- stored device entry to {"*" = mode}, adds one for every routed non-"none" map,
-- and stamps version 1.
function test_nrpn_codec_convert_rewrites_all_nrpn_metadata_to_one_mode()
  for _, mode in ipairs({"standard", "legacy-half"}) do
    local legacy = {nrpn_msb = 1, nrpn_lsb = 2, nrpn_lsb_mode = "legacy-half"}
    local standard = {nrpn_msb = 1, nrpn_lsb = 3, nrpn_lsb_mode = "standard"}
    local unmarked = {nrpn_msb = 1, nrpn_lsb = 4}
    local msb_only = {nrpn_msb = 1}
    legacy.self = legacy
    local data = {
      locks = {legacy, standard, {{unmarked}}, msb_only},
      nrpn_stored_modes = {
        [1] = {dev_a = {p1 = "legacy-half", p2 = "standard"}},
        [9] = {old = {["*"] = "legacy-half"}},
      },
      devices = {[1] = {device_map = "dev_a"}, [2] = {device_map = "dev_b"}, [3] = {device_map = "none"}, [4] = {}},
    }
    local result = nrpn_codec.convert(data, mode)
    luaunit.assert_is(result, data)
    luaunit.assert_equals(legacy.nrpn_lsb_mode, mode)
    luaunit.assert_equals(standard.nrpn_lsb_mode, mode)
    luaunit.assert_equals(unmarked.nrpn_lsb_mode, mode)
    luaunit.assert_equals(msb_only, {nrpn_msb = 1})
    luaunit.assert_equals(data.nrpn_stored_modes, {
      [1] = {dev_a = {["*"] = mode}},
      [2] = {dev_b = {["*"] = mode}},
      [9] = {old = {["*"] = mode}},
    })
    luaunit.assert_equals(data.nrpn_policy_version, 1)
    luaunit.assert_equals(nrpn_codec.stored_mode(data, 1, {id = "p2", nrpn_lsb_mode = "legacy-half"}, {id = "dev_a"}),
      mode)
  end
end

-- characterisation: an already-versioned project can be converted again.
function test_nrpn_codec_convert_accepts_version_one_projects()
  local data = {nrpn_policy_version = 1, lock = {nrpn_msb = 0, nrpn_lsb = 0, nrpn_lsb_mode = "legacy-half"}}
  nrpn_codec.convert(data, "standard")
  luaunit.assert_equals(data.lock.nrpn_lsb_mode, "standard")
  luaunit.assert_equals(data.nrpn_stored_modes, {})
  luaunit.assert_equals(data.nrpn_policy_version, 1)
end

----------------------------------------------------------------------------
-- midi_value_domain.unit_quantum
----------------------------------------------------------------------------

-- characterisation: one encoder step is 1/intervals, where an Off position outside
-- the range adds one interval; the default off is -1; the floor is one interval.
function test_midi_value_domain_unit_quantum_counts_off_as_an_interval()
  assert_close(midi_value_domain.unit_quantum(0, 127), 1 / 128)
  assert_close(midi_value_domain.unit_quantum(0, 127, -1), 1 / 128)
  assert_close(midi_value_domain.unit_quantum(0, 127, 128), 1 / 128)
  assert_close(midi_value_domain.unit_quantum(0, 127, 0), 1 / 127)
  assert_close(midi_value_domain.unit_quantum(0, 127, 64), 1 / 127)
  assert_close(midi_value_domain.unit_quantum(0, 127, 127), 1 / 127)
  assert_close(midi_value_domain.unit_quantum(-1, 127), 1 / 128)
  assert_close(midi_value_domain.unit_quantum(0, 16383, -1), 1 / 16384)
  assert_close(midi_value_domain.unit_quantum(0, 1), 1 / 2)
  assert_close(midi_value_domain.unit_quantum(5, 5), 1)
  assert_close(midi_value_domain.unit_quantum(5, 5, 5), 1)
  assert_close(midi_value_domain.unit_quantum(5, 5, 6), 1)
  assert_close(midi_value_domain.unit_quantum(5, 6, 5), 1)
  -- An inverted range is not validated here; the floor keeps the result at 1.
  assert_close(midi_value_domain.unit_quantum(7, 5, 6), 1)
end

-- characterisation: unit_quantum equals the quantum new() builds with units = 1.
function test_midi_value_domain_unit_quantum_matches_new_quantum()
  with_controlspec(function()
    for _, case in ipairs({{0, 127}, {0, 127, 0}, {0, 127, 127}, {0, 127, 200}, {10, 20, 0},
                           {-64, 63}, {-64, 63, -100}, {5, 5}, {5, 5, 5}, {0, 16383, -1}}) do
      local minimum, maximum, off = case[1], case[2], case[3]
      assert_close(midi_value_domain.new(minimum, maximum, off).quantum,
        midi_value_domain.unit_quantum(minimum, maximum, off))
    end
  end)
end

----------------------------------------------------------------------------
-- midi_value_domain.new: validation
----------------------------------------------------------------------------

-- characterisation: ranges must be numeric with minimum <= maximum.
function test_midi_value_domain_new_rejects_invalid_ranges()
  with_controlspec(function()
    luaunit.assert_error_msg_contains("Invalid MIDI parameter range", midi_value_domain.new, 5, 4)
    luaunit.assert_error_msg_contains("Invalid MIDI parameter range", midi_value_domain.new, "0", 127)
    luaunit.assert_error_msg_contains("Invalid MIDI parameter range", midi_value_domain.new, 0, "127")
    luaunit.assert_error_msg_contains("Invalid MIDI parameter range", midi_value_domain.new, nil, 127)
    luaunit.assert_error_msg_contains("Invalid MIDI parameter range", midi_value_domain.new, 0, nil)
  end)
end

-- characterisation: bounds and off must be integers (off may not be a string).
function test_midi_value_domain_new_rejects_non_integer_bounds_and_off()
  with_controlspec(function()
    local message = "MIDI parameter bounds and off value must be integers"
    luaunit.assert_error_msg_contains(message, midi_value_domain.new, 0.5, 127)
    luaunit.assert_error_msg_contains(message, midi_value_domain.new, 0, 127.5)
    luaunit.assert_error_msg_contains(message, midi_value_domain.new, 0, 127, 1.5)
    luaunit.assert_error_msg_contains(message, midi_value_domain.new, 0, 127, "off")
    luaunit.assert_error_msg_contains(message, midi_value_domain.new, 0, 127, false)
  end)
end

-- characterisation: equal bounds and integral floats are accepted.
function test_midi_value_domain_new_accepts_single_value_and_integral_floats()
  with_controlspec(function()
    local single = midi_value_domain.new(5, 5, 5)
    luaunit.assert_equals({single.minval, single.maxval, single.default}, {5, 5, 5})
    assert_close(single.quantum, 1)
    luaunit.assert_equals(single:map(0.7), 5)
    luaunit.assert_equals(single:unmap(5), 0)
    local floats = midi_value_domain.new(0.0, 127.0, 0.0)
    luaunit.assert_equals({floats.minval, floats.maxval}, {0, 127})
  end)
end

----------------------------------------------------------------------------
-- midi_value_domain.new: Off inside the range (a plain linear controlspec)
----------------------------------------------------------------------------

-- characterisation: an in-range off is just the default of a linear integer
-- controlspec whose quantum is units/(max-min).
function test_midi_value_domain_in_range_off_builds_plain_linear_spec()
  with_controlspec(function()
    local spec = midi_value_domain.new(0, 127, 0)
    luaunit.assert_equals({spec.minval, spec.maxval, spec.step, spec.default, spec.units},
      {0, 127, 1, 0, ""})
    assert_close(spec.quantum, 1 / 127)
    luaunit.assert_equals(spec:map(0), 0)
    luaunit.assert_equals(spec:map(0.5), 64)
    luaunit.assert_equals(spec:map(1), 127)
    luaunit.assert_equals(spec:map(-1), 0)
    luaunit.assert_equals(spec:map(2), 127)
    assert_close(spec:unmap(64), 64 / 127)
    assert_close(spec:unmap(500), 1)
    assert_close(spec:unmap(-5), 0)
    luaunit.assert_equals(spec:constrain(5.4), 5)
    luaunit.assert_equals(spec:constrain(5.5), 6)
    luaunit.assert_equals(spec:constrain(200), 127)
    luaunit.assert_equals(spec:constrain(-5), 0)
    local copy = spec:copy()
    luaunit.assert_equals(copy:constrain(5.4), 5)
    luaunit.assert_equals(copy:map(0.5), 64)
  end)
end

-- characterisation: the units argument scales the in-range quantum (NRPN uses 127).
function test_midi_value_domain_in_range_units_scale_quantum()
  with_controlspec(function()
    assert_close(midi_value_domain.new(0, 16383, 0, 127).quantum, 127 / 16383)
    assert_close(midi_value_domain.new(0, 16383, 0).quantum, 1 / 16383)
    assert_close(midi_value_domain.new(-1, 127).quantum, 1 / 128)
    luaunit.assert_equals(midi_value_domain.new(-1, 127).default, -1)
  end)
end

----------------------------------------------------------------------------
-- midi_value_domain.new: Off outside the range (one extra selectable position)
----------------------------------------------------------------------------

-- characterisation: default off (-1) below 0..127 gives 129 positions: raw 0 is
-- Off, each 1/128 step is the next active value, raw 1 is the maximum.
function test_midi_value_domain_off_below_range_maps_first_position_to_off()
  with_controlspec(function()
    local spec = midi_value_domain.new(0, 127)
    luaunit.assert_equals({spec.minval, spec.maxval, spec.step, spec.default, spec.units},
      {-1, 127, 1, -1, ""})
    assert_close(spec.quantum, 1 / 128)
    luaunit.assert_equals(spec:map(0), -1)
    luaunit.assert_equals(spec:map(1 / 128), 0)
    luaunit.assert_equals(spec:map(2 / 128), 1)
    luaunit.assert_equals(spec:map(0.5), 63)
    luaunit.assert_equals(spec:map(127 / 128), 126)
    luaunit.assert_equals(spec:map(1), 127)
    luaunit.assert_equals(spec:map(-3), -1)
    luaunit.assert_equals(spec:map(3), 127)
  end)
end

-- characterisation: raw positions round half up to the nearest index.
function test_midi_value_domain_off_below_range_rounds_raw_half_up()
  with_controlspec(function()
    local spec = midi_value_domain.new(0, 127)
    luaunit.assert_equals(spec:map(0.25 / 128), -1)
    luaunit.assert_equals(spec:map(0.5 / 128), 0)
    luaunit.assert_equals(spec:map(1.25 / 128), 0)
    luaunit.assert_equals(spec:map(1.5 / 128), 1)
  end)
end

-- characterisation: unmap is the inverse; out-of-range values clamp (below -> Off).
function test_midi_value_domain_off_below_range_unmaps_and_clamps()
  with_controlspec(function()
    local spec = midi_value_domain.new(0, 127)
    assert_close(spec:unmap(-1), 0)
    assert_close(spec:unmap(0), 1 / 128)
    assert_close(spec:unmap(64), 65 / 128)
    assert_close(spec:unmap(127), 1)
    assert_close(spec:unmap(500), 1)
    assert_close(spec:unmap(-9), 0)
    assert_close(spec:unmap(2.4), 3 / 128)
    for value = -1, 127 do
      luaunit.assert_equals(spec:map(spec:unmap(value)), value)
    end
  end)
end

-- characterisation: constrain is overridden to map(unmap(v)), so it rounds to the
-- nearest integer, clamps to max and snaps anything below the range to Off.
function test_midi_value_domain_off_below_range_constrain_preserves_domain()
  with_controlspec(function()
    local spec = midi_value_domain.new(0, 127)
    luaunit.assert_equals(spec:constrain(-1), -1)
    luaunit.assert_equals(spec:constrain(0), 0)
    luaunit.assert_equals(spec:constrain(63.4), 63)
    luaunit.assert_equals(spec:constrain(63.6), 64)
    luaunit.assert_equals(spec:constrain(500), 127)
    luaunit.assert_equals(spec:constrain(-9), -1)
  end)
end

-- characterisation: a sparse Off below the range (0 for 10..20) is ONE position;
-- values between Off and the minimum snap to the minimum, not to themselves.
function test_midi_value_domain_sparse_off_below_range_skips_the_gap()
  with_controlspec(function()
    local spec = midi_value_domain.new(10, 20, 0)
    luaunit.assert_equals({spec.minval, spec.maxval, spec.default}, {0, 20, 0})
    assert_close(spec.quantum, 1 / 11)
    luaunit.assert_equals(spec:map(0), 0)
    luaunit.assert_equals(spec:map(1 / 11), 10)
    luaunit.assert_equals(spec:map(6 / 11), 15)
    luaunit.assert_equals(spec:map(1), 20)
    assert_close(spec:unmap(0), 0)
    assert_close(spec:unmap(5), 1 / 11)
    assert_close(spec:unmap(10), 1 / 11)
    assert_close(spec:unmap(15), 6 / 11)
    assert_close(spec:unmap(20), 1)
    luaunit.assert_equals(spec:constrain(0), 0)
    luaunit.assert_equals(spec:constrain(5), 10)
    luaunit.assert_equals(spec:constrain(9), 10)
    luaunit.assert_equals(spec:constrain(15), 15)
    luaunit.assert_equals(spec:constrain(25), 20)
    luaunit.assert_equals(spec:constrain(-3), 0)
  end)
end

-- characterisation: an Off above the range is the LAST position; values between
-- the maximum and Off snap to the maximum, values beyond Off clamp to Off.
function test_midi_value_domain_off_above_range_maps_last_position_to_off()
  with_controlspec(function()
    local spec = midi_value_domain.new(10, 20, 30)
    luaunit.assert_equals({spec.minval, spec.maxval, spec.default}, {10, 30, 30})
    assert_close(spec.quantum, 1 / 11)
    luaunit.assert_equals(spec:map(0), 10)
    luaunit.assert_equals(spec:map(10 / 11), 20)
    luaunit.assert_equals(spec:map(1), 30)
    assert_close(spec:unmap(30), 1)
    assert_close(spec:unmap(10), 0)
    assert_close(spec:unmap(20), 10 / 11)
    assert_close(spec:unmap(25), 10 / 11)
    luaunit.assert_equals(spec:constrain(25), 20)
    luaunit.assert_equals(spec:constrain(30), 30)
    luaunit.assert_equals(spec:constrain(99), 30)
    luaunit.assert_equals(spec:constrain(3), 10)
    local adjacent = midi_value_domain.new(0, 10, 11)
    luaunit.assert_equals(adjacent:map(1), 11)
    luaunit.assert_equals(adjacent:map(0), 0)
    luaunit.assert_equals(adjacent:constrain(12), 11)
  end)
end

-- characterisation: negative ranges work the same way with a sparse negative Off.
function test_midi_value_domain_negative_range_with_off_below()
  with_controlspec(function()
    local spec = midi_value_domain.new(-64, 63, -100)
    luaunit.assert_equals({spec.minval, spec.maxval}, {-100, 63})
    assert_close(spec.quantum, 1 / 128)
    luaunit.assert_equals(spec:map(0), -100)
    luaunit.assert_equals(spec:map(1 / 128), -64)
    luaunit.assert_equals(spec:map(1), 63)
    luaunit.assert_equals(spec:constrain(-80), -64)
    luaunit.assert_equals(spec:constrain(-1), -1)
  end)
end

-- characterisation: with Off outside, units scale the quantum over max-min+1 intervals.
function test_midi_value_domain_off_outside_units_scale_quantum()
  with_controlspec(function()
    assert_close(midi_value_domain.new(0, 16383, -1, 127).quantum, 127 / 16384)
    assert_close(midi_value_domain.new(0, 127, -1, 127).quantum, 127 / 128)
  end)
end

-- characterisation: copy() (and a copy of a copy) keeps the Off-aware mapping and
-- constrain, and is a distinct table.
function test_midi_value_domain_copy_preserves_off_domain()
  with_controlspec(function()
    local spec = midi_value_domain.new(10, 20, 0)
    local copy = spec:copy()
    luaunit.assert_not_is(copy, spec)
    luaunit.assert_equals({copy.minval, copy.maxval, copy.default, copy.step}, {0, 20, 0, 1})
    assert_close(copy.quantum, 1 / 11)
    luaunit.assert_equals(copy:constrain(5), 10)
    luaunit.assert_equals(copy:map(0), 0)
    luaunit.assert_equals(copy:map(1 / 11), 10)
    assert_close(copy:unmap(15), 6 / 11)
    local second = copy:copy()
    luaunit.assert_not_is(second, copy)
    luaunit.assert_equals(second:constrain(5), 10)
    luaunit.assert_equals(second:constrain(-3), 0)
  end)
end

----------------------------------------------------------------------------
-- midi_patch_recall.send
----------------------------------------------------------------------------

-- Installs recording stubs for the globals recall reads, runs, then restores them.
local function with_recall_env(env, run)
  local saved = {program = program, device_map = device_map, params = params, m_midi = m_midi}
  local calls = {get_device = {}, params_get = {}, sent = {}}
  local params_stub = {}
  function params_stub.get(self, id)
    calls.params_get[#calls.params_get + 1] = {self == params_stub, id}
    return env.values[id]
  end
  program = {get = function() return env.program end}
  device_map = {
    get_device = function(id)
      calls.get_device[#calls.get_device + 1] = id
      return env.devices[id]
    end,
    get_stock_params = function() return env.stock end,
  }
  params = params_stub
  m_midi = {
    nrpn = function(...) calls.sent[#calls.sent + 1] = table.pack("nrpn", ...) end,
    cc = function(...) calls.sent[#calls.sent + 1] = table.pack("cc", ...) end,
  }
  local ok, err = pcall(run, calls)
  program, device_map, params, m_midi = saved.program, saved.device_map, saved.params, saved.m_midi
  if not ok then error(err, 0) end
end

local function sixteen_routes(overrides)
  local routes = {}
  for channel = 1, 16 do routes[channel] = overrides[channel] or {device_map = "none"} end
  return routes
end

local function recall_fixture()
  local synth = {id = "synth", type = "midi", params = {
    {id = "none", nrpn_msb = 0, nrpn_lsb = 1, nrpn_max_value = 127},
    {id = "stockish", param_type = "stock", cc_msb = 1, cc_max_value = 127},
    {id = "cutoff", nrpn_msb = 0, nrpn_lsb = 74, nrpn_max_value = 16383},
    {id = "resonance", cc_msb = 71, cc_max_value = 127},
    {id = "fine", cc_msb = 1, cc_lsb = 33, cc_max_value = 16383, channel = 12},
    {id = "default_off", cc_msb = 7, cc_max_value = 127},
    {id = "zero_off_at_off", cc_msb = 8, cc_max_value = 127, off_value = 0},
    {id = "zero_off_active", cc_msb = 9, cc_max_value = 127, off_value = 0},
    {id = "nrpn_without_max", nrpn_msb = 1, nrpn_lsb = 2, cc_msb = 10, cc_max_value = 127},
    {id = "nrpn_without_lsb", nrpn_msb = 1, nrpn_max_value = 127},
    {id = "cc_without_max", cc_msb = 11},
  }}
  local synth2 = {id = "synth2", type = "midi", params = {
    {id = "p", nrpn_msb = 2, nrpn_lsb = 3, nrpn_max_value = 16383},
  }}
  local voice = {id = "voice", type = "norns", params = {{id = "v", cc_msb = 1, cc_max_value = 127}}}
  local data = {
    devices = sixteen_routes({
      [1] = {device_map = "synth", midi_channel = 5, midi_device = 2},
      [2] = {device_map = "voice", midi_channel = 6, midi_device = 1},
      [4] = {device_map = "synth2", midi_channel = 9, midi_device = 3},
    }),
    nrpn_stored_modes = {
      [1] = {synth = {cutoff = "legacy-half"}},
      -- Same channel as synth2 but a different device id: must not leak.
      [4] = {synth = {["*"] = "legacy-half"}},
    },
  }
  local values = {
    midi_device_params_channel_1_5 = 8192,  -- cutoff
    midi_device_params_channel_1_6 = 0,     -- resonance (0 is not the default off)
    midi_device_params_channel_1_7 = 300,   -- fine
    midi_device_params_channel_1_8 = -1,    -- default_off at off
    midi_device_params_channel_1_9 = 0,     -- zero_off_at_off at off
    midi_device_params_channel_1_10 = 5,    -- zero_off_active
    midi_device_params_channel_1_11 = 64,   -- nrpn_without_max
    midi_device_params_channel_1_12 = 10,   -- nrpn_without_lsb
    midi_device_params_channel_1_13 = 20,   -- cc_without_max
    midi_device_params_channel_2_3 = 99,    -- non-MIDI device: never read
    midi_device_params_channel_4_3 = 16383, -- synth2.p
  }
  return {
    program = data,
    devices = {synth = synth, synth2 = synth2, voice = voice},
    stock = {{id = "none"}, {id = "stock_one"}},
    values = values,
  }
end

-- characterisation: recall sends each stored MIDI-device control that is not at
-- its Off value, using NRPN when nrpn_max_value+msb+lsb are all present, otherwise
-- CC when cc_msb+cc_max_value are present; parameter.channel overrides the route
-- channel; the NRPN mode is the channel/device/parameter stored mode.
function test_midi_patch_recall_sends_stored_controls_with_exact_arguments()
  local env = recall_fixture()
  with_recall_env(env, function(calls)
    midi_patch_recall.send()
    luaunit.assert_equals(calls.sent, {
      table.pack("nrpn", 0, 74, 8192, 5, 2, "legacy-half"),
      table.pack("cc", 71, nil, 0, 5, 2),
      table.pack("cc", 1, 33, 300, 12, 2),
      table.pack("cc", 9, nil, 5, 5, 2),
      table.pack("cc", 10, nil, 64, 5, 2),
      table.pack("nrpn", 2, 3, 16383, 9, 3, "standard"),
    })
  end)
end

-- characterisation: every channel 1..16 is looked up by its route's device_map, in
-- channel order.
function test_midi_patch_recall_looks_up_every_channel_route_in_order()
  local env = recall_fixture()
  with_recall_env(env, function(calls)
    midi_patch_recall.send()
    local expected = {}
    for channel = 1, 16 do expected[channel] = env.program.devices[channel].device_map end
    luaunit.assert_equals(calls.get_device, expected)
    luaunit.assert_equals(expected[1], "synth")
    luaunit.assert_equals(expected[2], "voice")
    luaunit.assert_equals(expected[4], "synth2")
  end)
end

-- characterisation: the param read for device parameter k on channel c is
-- "midi_device_params_channel_<c>_<#stock + k>"; "none" and stock-typed parameters
-- and non-MIDI devices are never read.
function test_midi_patch_recall_reads_param_ids_offset_by_stock_count()
  local env = recall_fixture()
  with_recall_env(env, function(calls)
    midi_patch_recall.send()
    local expected = {}
    for index = 3, 11 do expected[#expected + 1] = {true, "midi_device_params_channel_1_"..(2 + index)} end
    expected[#expected + 1] = {true, "midi_device_params_channel_4_3"}
    luaunit.assert_equals(calls.params_get, expected)
  end)
end

-- characterisation: the stock offset follows the stock list length.
function test_midi_patch_recall_param_offset_tracks_stock_list_length()
  local env = recall_fixture()
  env.stock = {{id = "a"}, {id = "b"}, {id = "c"}, {id = "d"}}
  env.program.devices = sixteen_routes({[7] = {device_map = "synth2", midi_channel = 1, midi_device = 4}})
  env.values = {midi_device_params_channel_7_5 = 1}
  with_recall_env(env, function(calls)
    midi_patch_recall.send()
    luaunit.assert_equals(calls.params_get, {{true, "midi_device_params_channel_7_5"}})
    luaunit.assert_equals(calls.sent, {table.pack("nrpn", 2, 3, 1, 1, 4, "standard")})
  end)
end

-- characterisation: with no MIDI device routed nothing is read or sent.
function test_midi_patch_recall_without_midi_devices_sends_nothing()
  local env = recall_fixture()
  env.program.devices = sixteen_routes({[2] = {device_map = "voice", midi_channel = 1, midi_device = 1}})
  with_recall_env(env, function(calls)
    midi_patch_recall.send()
    luaunit.assert_equals(calls.params_get, {})
    luaunit.assert_equals(calls.sent, {})
    luaunit.assert_equals(#calls.get_device, 16)
  end)
end

-- characterisation: the NRPN mode passed on is the stored per-parameter entry, then
-- the device "*" entry, then the parameter's own mode.
function test_midi_patch_recall_passes_stored_mode_precedence_to_nrpn()
  local device = {id = "synth", type = "midi", params = {
    {id = "exact", nrpn_msb = 0, nrpn_lsb = 1, nrpn_max_value = 16383},
    {id = "wild", nrpn_msb = 0, nrpn_lsb = 2, nrpn_max_value = 16383},
  }}
  local env = {
    program = {
      devices = sixteen_routes({[3] = {device_map = "synth", midi_channel = 2, midi_device = 1}}),
      nrpn_stored_modes = {[3] = {synth = {exact = "standard", ["*"] = "legacy-half"}}},
    },
    devices = {synth = device},
    stock = {},
    values = {midi_device_params_channel_3_1 = 129, midi_device_params_channel_3_2 = 130},
  }
  with_recall_env(env, function(calls)
    midi_patch_recall.send()
    luaunit.assert_equals(calls.sent, {
      table.pack("nrpn", 0, 1, 129, 2, 1, "standard"),
      table.pack("nrpn", 0, 2, 130, 2, 1, "legacy-half"),
    })
  end)
  env.program.nrpn_stored_modes = nil
  device.params[1].nrpn_lsb_mode = "legacy-half"
  with_recall_env(env, function(calls)
    midi_patch_recall.send()
    luaunit.assert_equals(calls.sent, {
      table.pack("nrpn", 0, 1, 129, 2, 1, "legacy-half"),
      table.pack("nrpn", 0, 2, 130, 2, 1, "standard"),
    })
  end)
end
