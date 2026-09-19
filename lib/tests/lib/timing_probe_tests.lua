-- Checkpoint A diagnostic probe.  This is an instrumentation contract, not a
-- musical behaviour assertion: the default global must leave the recorder off.
local timing_probe = include("mosaic/lib/clock/timing_probe")
local Lattice = include("mosaic/lib/clock/m_lattice")

function test_timing_probe_is_numeric_bounded_and_overwrites_the_oldest_record()
  local now = 10
  local probe = timing_probe.new({capacity = 2, now = function() return now end})

  probe:record(1, 7, 41, 1.25, 2, 3, 4)
  now = 11
  probe:record(5, 8, 42, 1.5, 6, 7, 8)
  now = 12
  probe:record(9, 9, 43, 1.75, 10, 11, 12)

  local snapshot = probe:snapshot()
  luaunit.assert_equals(snapshot.schema_version, 1)
  luaunit.assert_equals(snapshot.capacity, 2)
  luaunit.assert_equals(snapshot.count, 2)
  luaunit.assert_equals(snapshot.dropped, 1)
  luaunit.assert_equals(snapshot.records, {
    {11, 5, 8, 42, 1.5, 6, 7, 8},
    {12, 9, 9, 43, 1.75, 10, 11, 12},
  })
end

function test_timing_probe_reset_reuses_its_fixed_capacity_and_clears_drops()
  local calls = 0
  local probe = timing_probe.new({capacity = 1, now = function() calls = calls + 1; return calls end})
  probe:record(1, 2, 3, 4, 5, 6, 7)
  probe:record(8, 9, 10, 11, 12, 13, 14)
  probe:reset()

  local snapshot = probe:snapshot()
  luaunit.assert_equals(snapshot.capacity, 1)
  luaunit.assert_equals(snapshot.count, 0)
  luaunit.assert_equals(snapshot.dropped, 0)
  luaunit.assert_equals(snapshot.records, {})
  luaunit.assert_equals(calls, 2)
end

function test_timing_probe_optional_kind_filter_skips_clock_count_and_drop_changes()
  local calls = 0
  local probe = timing_probe.new({capacity = 1, kinds = {[1] = true, [4] = true, [5] = true}, now = function() calls = calls + 1; return calls end})
  probe:record(2, 1, 1, 0, 1, 0, 0)
  luaunit.assert_equals(calls, 0)
  luaunit.assert_equals(probe:snapshot().count, 0)
  probe:record(1, 1, 1, 0, 1, 0, 0)
  luaunit.assert_equals(calls, 1)
  luaunit.assert_equals(probe:snapshot().count, 1)
  probe:record(6, 1, 1, 0, 1, 0, 0)
  luaunit.assert_equals(calls, 1)
  luaunit.assert_equals(probe:snapshot().dropped, 0)
end

function test_timing_probe_without_kind_filter_keeps_full_capture()
  local probe = timing_probe.new({capacity = 2, now = function() return 1 end})
  probe:record(2, 1, 1, 0, 1, 0, 0)
  luaunit.assert_equals(probe:snapshot().count, 1)
end

function test_timing_probe_records_paired_boundaries_as_independent_numeric_rows()
  local now = 100
  local probe = timing_probe.new({capacity = 4, now = function() now = now + 1; return now end})
  probe:record(3, 17, 99, 2.5, 1, 0, 0)
  probe:record(3, 17, 99, 2.5, 2, 3, 1)

  local records = probe:snapshot().records
  luaunit.assert_equals(#records, 2)
  luaunit.assert_equals({records[1][2], records[1][3], records[1][4], records[1][5]}, {3, 17, 99, 2.5})
  luaunit.assert_equals({records[1][6], records[2][6]}, {1, 2})
  luaunit.assert_equals({records[2][7], records[2][8]}, {3, 1})
end

function test_lattice_probe_hook_is_default_off_without_reading_the_clock()
  local saved_probe, saved_util = _G.mosaic_pulse_probe, _G.util
  _G.mosaic_pulse_probe = nil
  _G.util = {time = function() error("disabled probe must not read time") end}
  local lattice = Lattice:new({auto = false})
  local ok, err = pcall(function() lattice:pulse() end)
  _G.mosaic_pulse_probe, _G.util = saved_probe, saved_util
  luaunit.assert_true(ok, err)
end

function test_lattice_probe_hook_records_pulse_boundaries_when_explicitly_installed()
  local saved_probe = _G.mosaic_pulse_probe
  local rows = {}
  _G.mosaic_pulse_probe = {record = function(_, ...) rows[#rows + 1] = {...} end}
  local lattice = Lattice:new({auto = false})
  lattice:pulse()
  _G.mosaic_pulse_probe = saved_probe
  luaunit.assert_equals(rows, {{1, 1, 0, 0, 1}, {1, 1, 0, 0, 2}})
end
