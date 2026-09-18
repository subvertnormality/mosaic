-- The bounded cancellable queue behind lock lookahead. One earliest-deadline
-- wakeup serves every pending value, so the queue must order by deadline, drop
-- cancelled generations without paying for them at send time, and refuse to
-- exceed its cap rather than silently losing a value that is still wanted.
local lookahead = include("mosaic/lib/clock/lock_lookahead_queue")

local function drain(q, now)
  local out = {}
  while true do
    local payload = q:pop_due(now)
    if payload == nil then break end
    out[#out + 1] = payload
  end
  return out
end

function test_lookahead_queue_serves_values_in_deadline_order()
  local q = lookahead.new()
  q:push(3.0, {name = "c"})
  q:push(1.0, {name = "a"})
  q:push(2.0, {name = "b"})
  local served = drain(q, 5.0)
  luaunit.assert_equals(#served, 3)
  luaunit.assert_equals(served[1].name, "a")
  luaunit.assert_equals(served[2].name, "b")
  luaunit.assert_equals(served[3].name, "c")
end

function test_lookahead_queue_breaks_equal_deadlines_by_insertion_order()
  -- Same intended time: the existing slot order decides, so insertion wins.
  local q = lookahead.new()
  q:push(1.0, {name = "first"})
  q:push(1.0, {name = "second"})
  q:push(1.0, {name = "third"})
  local served = drain(q, 1.0)
  luaunit.assert_equals({served[1].name, served[2].name, served[3].name},
    {"first", "second", "third"})
end

function test_lookahead_queue_serves_nothing_before_its_earliest_deadline()
  local q = lookahead.new()
  q:push(2.0, {name = "a"})
  luaunit.assert_equals(drain(q, 1.999), {})
  luaunit.assert_equals(#drain(q, 2.0), 1)
end

function test_lookahead_queue_reports_one_earliest_deadline_for_a_single_wakeup()
  local q = lookahead.new()
  luaunit.assert_nil(q:earliest())
  q:push(3.0, {name = "c"})
  q:push(1.5, {name = "a"})
  luaunit.assert_equals(q:earliest(), 1.5)
  drain(q, 1.5)
  luaunit.assert_equals(q:earliest(), 3.0)
  drain(q, 3.0)
  luaunit.assert_nil(q:earliest())
end

function test_lookahead_queue_cancels_by_generation_without_serving_them()
  local q = lookahead.new()
  q:push(1.0, {name = "old"}, 1)
  q:push(2.0, {name = "new"}, 2)
  q:cancel_generation(1)
  local served = drain(q, 5.0)
  luaunit.assert_equals(#served, 1)
  luaunit.assert_equals(served[1].name, "new")
end

function test_lookahead_queue_skips_cancelled_entries_when_reporting_the_next_wakeup()
  -- A cancelled value must not hold a wakeup that would serve nothing.
  local q = lookahead.new()
  q:push(1.0, {name = "old"}, 1)
  q:push(4.0, {name = "new"}, 2)
  q:cancel_generation(1)
  luaunit.assert_equals(q:earliest(), 4.0)
end

function test_lookahead_queue_cancels_a_matching_subset_only()
  local q = lookahead.new()
  q:push(1.0, {channel = 1}, 1)
  q:push(2.0, {channel = 2}, 1)
  q:push(3.0, {channel = 1}, 1)
  q:cancel(function(payload) return payload.channel == 1 end)
  local served = drain(q, 5.0)
  luaunit.assert_equals(#served, 1)
  luaunit.assert_equals(served[1].channel, 2)
end

function test_lookahead_queue_cancels_everything_on_a_pattern_boundary()
  local q = lookahead.new()
  q:push(1.0, {name = "a"}, 1)
  q:push(2.0, {name = "b"}, 2)
  q:cancel_all()
  luaunit.assert_equals(drain(q, 5.0), {})
  luaunit.assert_nil(q:earliest())
  -- The queue stays usable for the incoming pattern.
  q:push(3.0, {name = "c"}, 3)
  luaunit.assert_equals(#drain(q, 5.0), 1)
end

function test_lookahead_queue_refuses_to_exceed_its_cap_and_keeps_live_values()
  local q = lookahead.new(3)
  luaunit.assert_true(q:push(1.0, {name = "a"}))
  luaunit.assert_true(q:push(2.0, {name = "b"}))
  luaunit.assert_true(q:push(3.0, {name = "c"}))
  local accepted, reason = q:push(4.0, {name = "d"})
  luaunit.assert_false(accepted)
  luaunit.assert_equals(reason, "horizon-limit")
  -- Rejection never costs an already accepted value.
  local served = drain(q, 5.0)
  luaunit.assert_equals(#served, 3)
  luaunit.assert_equals(q:stats().rejected, 1)
end

function test_lookahead_queue_reuses_room_freed_by_cancellation()
  local q = lookahead.new(2)
  q:push(1.0, {name = "a"}, 1)
  q:push(2.0, {name = "b"}, 1)
  luaunit.assert_false(q:push(3.0, {name = "c"}, 2))
  q:cancel_generation(1)
  luaunit.assert_true(q:push(3.0, {name = "c"}, 2))
  local served = drain(q, 5.0)
  luaunit.assert_equals(#served, 1)
  luaunit.assert_equals(served[1].name, "c")
end

function test_lookahead_queue_compacts_cancelled_entries_instead_of_growing()
  local q = lookahead.new(64)
  for round = 1, 20 do
    for i = 1, 8 do q:push(round + i / 10, {round = round}, round) end
    q:cancel_generation(round)
  end
  -- Nothing live remains, and the storage did not keep every cancelled entry.
  luaunit.assert_nil(q:earliest())
  luaunit.assert_equals(q:stats().live, 0)
  luaunit.assert_true(q:stats().stored <= 64,
    "compaction must bound storage, stored=" .. q:stats().stored)
end

function test_lookahead_queue_records_its_high_water_marks()
  local q = lookahead.new(16)
  q:push(1.0, {name = "a"}, 1)
  q:push(2.0, {name = "b"}, 1)
  q:push(3.0, {name = "c"}, 2)
  luaunit.assert_equals(q:stats().max_live, 3)
  q:cancel_generation(1)
  luaunit.assert_equals(q:stats().live, 1)
  luaunit.assert_equals(q:stats().max_live, 3)
end

function test_lookahead_queue_caps_at_the_documented_bundle_maximum_by_default()
  -- Sixteen channels, sixty-four horizon occurrences, ten parameter slots.
  luaunit.assert_equals(lookahead.MAX_BUNDLES, 16 * 64 * 10)
  luaunit.assert_equals(lookahead.new():stats().capacity, 16 * 64 * 10)
end

function test_lookahead_queue_serves_a_late_deadline_promptly_rather_than_dropping_it()
  -- A missed deadline is still owed: it leaves at the next service, marked late
  -- by the caller, never redefined into a successful lead or discarded.
  local q = lookahead.new()
  q:push(1.0, {name = "overdue"})
  local served = drain(q, 9.0)
  luaunit.assert_equals(#served, 1)
  luaunit.assert_equals(served[1].name, "overdue")
end

function test_lookahead_queue_serves_a_reused_generation_number_after_cancelling_it()
  -- Cancellation applies to the entries present at the time. Remembering the
  -- number instead would silently discard a later value that reused it, and
  -- would do so only until the next compaction.
  local q = lookahead.new()
  q:push(1.0, {name = "old"}, 7)
  q:cancel_generation(7)
  q:push(2.0, {name = "new"}, 7)
  local served = drain(q, 5.0)
  luaunit.assert_equals(#served, 1)
  luaunit.assert_equals(served[1].name, "new")
end
