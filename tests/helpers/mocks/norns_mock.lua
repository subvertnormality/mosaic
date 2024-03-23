_norns = {}
_norns.clock = {}
_norns.clock_schedule_sleep = function() end
_norns.clock_schedule_sync = function() end

clock = include("mosaic/tests/test_artefacts/norns_test_artefact/lua/core/clock")
