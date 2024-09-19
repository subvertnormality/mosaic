_norns = {}
_norns.clock = {}
_norns.clock.run = function(func) 
  print("Running function")
  func() 
end
_norns.clock.sleep = function() end
_norns.clock_cancel = function() end
_norns.clock_schedule_sleep = function() end
_norns.clock_schedule_sync = function() end

_norns.clock_get_tempo = function() return 120 end

clock = include("mosaic/lib/tests/test_artefacts/norns_test_artefact/lua/core/clock")

clock.sleep = function() end
clock.cancel = function() end
