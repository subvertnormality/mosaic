local pitch_resolution = include("mosaic/lib/musical_resolution/pitch_resolution")

local function resolver(options)
  local calls = {}
  local function record(name, ...)
    table.insert(calls, {name, ...})
  end

  local resolve = pitch_resolution.new(
    function(mask, scale)
      record("translate", mask, scale)
      return options.relative or 3, options.offset or 1
    end,
    function(note, octave, transpose, scale, pentatonic)
      record("process", note, octave, transpose, scale, pentatonic)
      return options.processed or 70
    end,
    function(note, scale, transpose)
      record("snap", note, scale, transpose)
      return options.snapped or 71
    end,
    function()
      record("global_full")
      return options.global_full or false
    end,
    function()
      record("read_snap")
      return options.snap or false
    end
  )

  return resolve, calls
end

-- Characterisation, not manual text: ordinary notes bypass both mask option
-- readers and retain the raw full-mask value for downstream chord processing.
function test_pitch_resolution_preserves_the_ordinary_note_path()
  for _, mask in ipairs({false, -1}) do
    local resolve, calls = resolver({processed = 64})
    local note, relative, offset, is_mask, full = resolve(2, mask, -1, 3, 4, 5, true, -1)

    luaunit.assert_equals(note, 64)
    luaunit.assert_nil(relative)
    luaunit.assert_equals(offset, 0)
    luaunit.assert_false(is_mask)
    luaunit.assert_equals(full, -1)
    luaunit.assert_equals(calls, {{"process", 7, -1, 3, 4, true}})
  end
end

-- Characterisation, not manual text: mask translation precedes raw, snap and
-- full resolution, and each branch receives the previous implementation's args.
function test_pitch_resolution_preserves_raw_snap_and_full_mask_paths()
  local resolve, calls = resolver({relative = 6, offset = 2})
  local note, relative, offset, is_mask, full = resolve(9, 60, 1, 4, 3, -2, false, 1)
  luaunit.assert_equals({note, relative, offset, is_mask, full}, {70, 6, 2, true, false})
  luaunit.assert_equals(calls, {{"global_full"}, {"translate", 60, 3}, {"read_snap"}})

  resolve, calls = resolver({relative = 6, offset = 2, snap = true, snapped = 67})
  note, relative, offset, is_mask, full = resolve(9, 60, 1, 4, 3, -2, false, 1)
  luaunit.assert_equals({note, relative, offset, is_mask, full}, {67, 6, 2, true, false})
  luaunit.assert_equals(calls, {
    {"global_full"},
    {"translate", 60, 3},
    {"read_snap"},
    {"snap", 70, 3, 4}
  })

  resolve, calls = resolver({relative = 6, offset = 2, global_full = true, processed = 65})
  note, relative, offset, is_mask, full = resolve(9, 60, 1, 4, 3, -2, true, nil)
  luaunit.assert_equals({note, relative, offset, is_mask, full}, {65, 6, 2, true, true})
  luaunit.assert_equals(calls, {
    {"global_full"},
    {"translate", 60, 3},
    {"process", 4, 3, 4, 3, true}
  })
end

-- Characterisation, not manual text: mask zero is active, and nil/-1/0 inherit
-- global full quantisation while 1 forces off and 2 forces on.
function test_pitch_resolution_preserves_full_mask_inheritance_sentinels()
  local cases = {
    {global = false, raw = nil, expected = false},
    {global = false, raw = -1, expected = false},
    {global = false, raw = 0, expected = false},
    {global = false, raw = 1, expected = false},
    {global = false, raw = 2, expected = true},
    {global = true, raw = nil, expected = true},
    {global = true, raw = -1, expected = true},
    {global = true, raw = 0, expected = true},
    {global = true, raw = 1, expected = false},
    {global = true, raw = 2, expected = true}
  }

  for _, case in ipairs(cases) do
    local resolve, calls = resolver({global_full = case.global})
    local _, relative, _, is_mask, full = resolve(8, 0, 0, 0, 1, 0, false, case.raw)

    luaunit.assert_equals(relative, 3)
    luaunit.assert_true(is_mask)
    luaunit.assert_equals(full, case.expected)
    luaunit.assert_equals(calls[1], {"global_full"})
    luaunit.assert_equals(calls[2], {"translate", 0, 1})
    if case.expected then
      luaunit.assert_equals(calls[3][1], "process")
      luaunit.assert_equals(#calls, 3)
    else
      luaunit.assert_equals(calls[3], {"read_snap"})
      luaunit.assert_equals(#calls, 3)
    end
  end
end
