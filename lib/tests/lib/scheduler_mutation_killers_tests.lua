-- Mutation killers for lib/scheduler.lua (the real cooperative scheduler; the harness
-- normally installs scheduler_mock). -- characterisation: README does not describe the
-- scheduler; these pin the debounce contract its callers (UI refreshes) rely on.
local function real_scheduler() return dofile("../../lib/scheduler.lua") end

-- A debounced call made after the previous call's job has already finished (and been
-- pruned) must simply run; it must not try to deactivate the finished job.
function test_schedk_debounce_after_the_previous_job_finished_runs_the_new_call()
  local s = real_scheduler()
  local seen = {}
  local job = s.debounce(function(value) seen[#seen + 1] = value end)
  job("first")
  s.update()
  luaunit.assert_equals(seen, {"first"})
  luaunit.assert_equals(s.active_count, 0)
  job("second")
  luaunit.assert_equals(s.active_count, 1)
  s.update()
  luaunit.assert_equals(seen, {"first", "second"})
  luaunit.assert_equals(s.active_count, 0)
end

-- The same, while an unrelated long job keeps the finished entry from being pruned: the
-- finished job is inactive, so replacing it must not decrement the live count.
function test_schedk_debounce_does_not_recount_a_finished_unpruned_job()
  local s = real_scheduler()
  local seen = {}
  local job = s.debounce(function(value) seen[#seen + 1] = value end)
  job("first")
  for _ = 1, 2 do
    s.start(coroutine.create(function() for _ = 1, 10 do coroutine.yield() end end))
  end
  s.update()
  luaunit.assert_equals(seen, {"first"})
  luaunit.assert_equals(s.active_count, 2)
  job("second")
  luaunit.assert_equals(s.active_count, 3)
  s.update()
  luaunit.assert_equals(seen, {"first", "second"})
  luaunit.assert_equals(s.active_count, 2)
end
