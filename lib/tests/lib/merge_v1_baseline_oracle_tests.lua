-- Independent Off/v1 baseline oracle (docs/musical-merge-extensions-plan.md §0,
-- "Off stays exact" and the migration acceptance boundary: load-v1/save-v2/
-- reload-v2 with absent and explicit Off configurations, Foundation enabled,
-- unknown top-level and nested keys, collisions with each new field and a saved
-- Harmony Pattern map, comparing pattern values, emitted MIDI, RNG consumption
-- and lead-enabled lookahead with the pinned v1 baseline). README "Merge Shape"
-- and "Saving and loading projects": a project saved by an earlier release
-- loads and plays as it did. Characterisation of the approved plan beyond that.
--
-- The expectations are frozen observations of the BASE revision f908a553,
-- captured by lib/tests/fixtures/merge_v1_baseline/capture.sh running the
-- shared scenario under that revision's own harness. Nothing here regenerates
-- them: the candidate only loads the base-saved v1 project files through its
-- production load (project_validation.check + migrate via project_lifecycle),
-- saves v2 through its production save, reloads v2 and compares.

local FIXTURES = "./fixtures/merge_v1_baseline/"
local BASE_REVISION = "f908a5530e435a8c412a3f295783344a471a7b40"
local PROJECTS = {"absent", "explicit_off", "foundation", "unknown_keys", "foundation_harmony_pattern"}

local merge_config = include("mosaic/lib/musical_merge/config")

------------------------------------------------------------------------------
-- SHA-256 (FIPS 180-4), pure Lua 5.3, for fixture provenance checks.

local K = {
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
  0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
  0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
  0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
  0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
  0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2}

local function sha256(message)
  local M = 0xffffffff
  local function rotr(x, n) return ((x >> n) | (x << (32 - n))) & M end
  local length = #message
  message = message .. "\128" .. string.rep("\0", (55 - length) % 64) .. string.pack(">I8", length * 8)
  local h = {0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19}
  local w = {}
  for chunk = 1, #message, 64 do
    for i = 1, 16 do w[i] = string.unpack(">I4", message, chunk + (i - 1) * 4) end
    for i = 17, 64 do
      local a, b = w[i - 15], w[i - 2]
      local s0 = rotr(a, 7) ~ rotr(a, 18) ~ (a >> 3)
      local s1 = rotr(b, 17) ~ rotr(b, 19) ~ (b >> 10)
      w[i] = (w[i - 16] + s0 + w[i - 7] + s1) & M
    end
    local a, b, c, d, e, f, g, hh = h[1], h[2], h[3], h[4], h[5], h[6], h[7], h[8]
    for i = 1, 64 do
      local S1 = rotr(e, 6) ~ rotr(e, 11) ~ rotr(e, 25)
      local ch = (e & f) ~ (~e & g)
      local t1 = (hh + S1 + ch + K[i] + w[i]) & M
      local S0 = rotr(a, 2) ~ rotr(a, 13) ~ rotr(a, 22)
      local maj = (a & b) ~ (a & c) ~ (b & c)
      local t2 = (S0 + maj) & M
      hh, g, f, e, d, c, b, a = g, f, e, (d + t1) & M, c, b, a, (t1 + t2) & M
    end
    h[1], h[2], h[3], h[4] = (h[1] + a) & M, (h[2] + b) & M, (h[3] + c) & M, (h[4] + d) & M
    h[5], h[6], h[7], h[8] = (h[5] + e) & M, (h[6] + f) & M, (h[7] + g) & M, (h[8] + hh) & M
  end
  return string.format(string.rep("%08x", 8), table.unpack(h))
end

local function read(path)
  local file = assert(io.open(path, "rb"), "missing fixture " .. path)
  local text = file:read("a")
  file:close()
  return text
end

------------------------------------------------------------------------------

local scenario = dofile(FIXTURES .. "scenario.lua")
local manifest = dofile(FIXTURES .. "MANIFEST.lua")

local function oracle(name)
  return dofile(FIXTURES .. name .. ".oracle.lua")
end

-- First difference between two canonical values, as a readable path.
local function first_difference(expected, actual, path)
  if type(expected) ~= "table" or type(actual) ~= "table" then
    if scenario.serialize(expected) ~= scenario.serialize(actual) then
      return path .. ": base " .. scenario.serialize(expected):sub(1, 300) ..
        " / candidate " .. scenario.serialize(actual):sub(1, 300)
    end
    return nil
  end
  local keys, seen = {}, {}
  for key in pairs(expected) do keys[#keys + 1] = key; seen[key] = true end
  for key in pairs(actual) do if not seen[key] then keys[#keys + 1] = key end end
  table.sort(keys, function(a, b)
    if type(a) == type(b) and (type(a) == "number" or type(a) == "string") then return a < b end
    return type(a) < type(b)
  end)
  for _, key in ipairs(keys) do
    local found = first_difference(expected[key], actual[key], path .. "[" .. tostring(key) .. "]")
    if found then return found end
  end
  return nil
end

local function assert_same(expected, actual, label)
  local difference = first_difference(expected, actual, label)
  if difference then luaunit.fail("differs from f908a553 at " .. difference) end
end

-- Every observation of one load, per lead setting.
local function assert_observation(expected, actual, label)
  for _, lead in ipairs({"lead_0", "lead_25"}) do
    local e, a = expected[lead], actual[lead]
    luaunit.assert_true(#e.midi > 100, label .. " " .. lead .. " baseline has MIDI")
    assert_same(e.working, a.working, label .. "." .. lead .. ".working")
    assert_same(e.rebuilds, a.rebuilds, label .. "." .. lead .. ".rebuilds")
    assert_same(e.rng, a.rng, label .. "." .. lead .. ".rng")
    assert_same(e.midi, a.midi, label .. "." .. lead .. ".midi")
  end
end

local RECOGNISED = {"mode", "anchor", "amount", "accent", "gap", "seed", "ranking_version", "cycles",
  "shape", "percentages", "variation", "keep_anchor_pitch"}

-- Plan §0: recognised v1 semantics survive exactly; target fields by kind;
-- every unknown or colliding v1 key is discarded; new fields take defaults.
local function assert_migrated(base_loaded, song, label)
  for number = 1, 17 do
    local v1, v2 = base_loaded[number], song.channels[number].musical_merge
    if v1 == false then
      luaunit.assert_nil(v2, label .. " ch" .. number .. " stays absent")
    else
      luaunit.assert_equals(v2.schema_version, 2, label .. " ch" .. number)
      luaunit.assert_true(merge_config.validate(v2, number), label .. " ch" .. number .. " valid v2")
      for _, field in ipairs(RECOGNISED) do
        assert_same(v1[field], v2[field], label .. " ch" .. number .. "." .. field)
      end
      local target = {kind = v1.target.kind}
      if target.kind == "degrees" then target.degrees = v1.target.degrees end
      if target.kind == "chord" then target.group_id = v1.target.group_id end
      assert_same(target, v2.target, label .. " ch" .. number .. ".target")
      local defaults = merge_config.new()
      for _, field in ipairs({"interlock", "space", "fragments", "structure"}) do
        assert_same(defaults[field], v2[field], label .. " ch" .. number .. "." .. field)
      end
      for key in pairs(v2) do
        luaunit.assert_true(defaults[key] ~= nil or key == "anchor",
          label .. " ch" .. number .. " unexpected key " .. tostring(key))
      end
    end
  end
end

local function temporary_directory()
  local path = os.tmpname()
  os.remove(path)
  assert(os.execute("mkdir -p '" .. path .. "'"))
  return path
end

local function remove_directory(path)
  os.execute("rm -rf '" .. path .. "'")
end

-- load v1 -> observe; save v2 -> check file; reload v2 -> observe.
local function round_trip(name)
  local expected = oracle(name)
  local v1_path = FIXTURES .. name .. ".v1.ptn"
  local v1_saved = require("tabutil").load(v1_path)
  for _, song in pairs(v1_saved[2].song_patterns) do
    for number = 1, 17 do
      local merge = song.channels[number].musical_merge
      if merge ~= nil then luaunit.assert_equals(merge.schema_version, 1, name .. " fixture is v1") end
    end
  end

  -- The live project before the load is the one the capture had built and
  -- saved; the load then replaces it.
  for _, project in ipairs(scenario.projects) do
    if project.name == name then project.build() end
  end
  local from_v1 = scenario.observe(v1_path)
  assert_observation(expected, from_v1, name .. ".v1")
  assert_migrated(expected.loaded_merge, program.get_song_pattern(1), name .. ".v1")

  local directory = temporary_directory()
  local ok, err = pcall(function()
    local v2_path = scenario.save(directory, name .. ".v2")
    local v2_saved = require("tabutil").load(v2_path)
    for number = 1, 17 do
      local merge = v2_saved[2].song_patterns[1].channels[number].musical_merge
      if expected.loaded_merge[number] == false then
        luaunit.assert_nil(merge, name .. " v2 file ch" .. number .. " stays absent")
      else
        luaunit.assert_equals(merge.schema_version, 2, name .. " v2 file ch" .. number)
      end
    end
    local from_v2 = scenario.observe(v2_path)
    assert_observation(expected, from_v2, name .. ".v2")
    assert_migrated(expected.loaded_merge, program.get_song_pattern(1), name .. ".v2")
  end)
  remove_directory(directory)
  if not ok then error(err, 0) end
end

function test_merge_v1_oracle_fixtures_are_source_identified_and_unaltered()
  luaunit.assert_equals(manifest.source_revision, BASE_REVISION)
  luaunit.assert_equals(manifest.capture_script, "lib/tests/fixtures/merge_v1_baseline/capture.sh")
  -- The shared scenario and the capture tooling are exactly what produced the
  -- fixtures; editing any of them requires recapturing from f908a553.
  for input, digest in pairs(manifest.inputs) do
    luaunit.assert_equals(sha256(read(FIXTURES .. input)), digest, input .. " changed since capture")
  end
  local count = 0
  for file, digest in pairs(manifest.files) do
    local text = read(FIXTURES .. file)
    luaunit.assert_equals(sha256(text), digest, file .. " changed since capture")
    luaunit.assert_not_nil(text:find("-- source_revision: " .. BASE_REVISION, 1, true), file)
    count = count + 1
  end
  luaunit.assert_equals(count, 2 * #PROJECTS)
  for _, name in ipairs(PROJECTS) do
    luaunit.assert_not_nil(manifest.files[name .. ".v1.ptn"], name)
    luaunit.assert_not_nil(manifest.files[name .. ".oracle.lua"], name)
  end
end

function test_merge_v1_oracle_sha256_matches_known_vectors()
  luaunit.assert_equals(sha256(""), "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
  luaunit.assert_equals(sha256("abc"), "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
  luaunit.assert_equals(sha256(string.rep("a", 1000)),
    "41edece42d63e8d9bf515a9ba6932e1c20cbc9f5a5d134645adb5db1b9737ea3")
end

function test_merge_v1_oracle_absent_configuration_matches_base()
  round_trip("absent")
end

function test_merge_v1_oracle_explicit_off_matches_base()
  round_trip("explicit_off")
end

function test_merge_v1_oracle_foundation_phrases_variation_targets_match_base()
  round_trip("foundation")
end

function test_merge_v1_oracle_unknown_and_colliding_keys_match_base()
  round_trip("unknown_keys")
end

function test_merge_v1_oracle_foundation_with_harmony_pattern_map_matches_base()
  round_trip("foundation_harmony_pattern")
end
