-- The real cooperative scheduler (the unit harness normally installs scheduler_mock,
-- which runs every job to completion). Debounced UI and working-pattern updates rely on
-- these semantics; a performance sweep of scheduler.update must keep them.
local function real_scheduler() return dofile("../../lib/scheduler.lua") end

function test_scheduler_debounce_runs_only_the_latest_call()
  local s = real_scheduler()
  local seen = {}
  local job = s.debounce(function(value) seen[#seen + 1] = value end)
  job(1); job(2); job(3)
  for _ = 1, 3 do s.update() end
  luaunit.assert_equals(seen, {3})
  luaunit.assert_equals(s.active_count, 0)
end

function test_scheduler_advances_each_job_one_slice_per_update_in_start_order()
  local s = real_scheduler()
  local trace = {}
  for name in ("ab"):gmatch(".") do
    s.start(coroutine.create(function()
      for i = 1, 3 do trace[#trace + 1] = name .. i; coroutine.yield() end
    end))
  end
  s.update(); luaunit.assert_equals(trace, {"a1", "b1"})
  s.update(); luaunit.assert_equals(trace, {"a1", "b1", "a2", "b2"})
  for _ = 1, 3 do s.update() end
  luaunit.assert_equals(trace, {"a1", "b1", "a2", "b2", "a3", "b3"})
  luaunit.assert_equals(s.active_count, 0)
end

function test_scheduler_removes_a_failing_job_and_keeps_the_others()
  local s = real_scheduler()
  local original_print = print
  print = function() end
  local done = false
  s.start(coroutine.create(function() error("boom") end))
  s.start(coroutine.create(function() coroutine.yield(); done = true end))
  s.update(); s.update()
  print = original_print
  luaunit.assert_true(done)
  luaunit.assert_equals(s.active_count, 0)
  luaunit.assert_nil(s.start("not a thread"))
end
