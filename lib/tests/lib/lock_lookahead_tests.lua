-- The lookahead scheduler under the pulse-advance contract. Values for a future
-- step are resolved early and held against the pulse that will send them, so
-- they leave inside a pulse the sequencer was already running. Nothing here uses
-- a timer, and a value that has been sent early must not be sent again when its
-- own step arrives.
local lookahead = include("mosaic/lib/clock/lock_lookahead")

local function recorder()
  local sent = {}
  return sent, function(bundle) sent[#sent + 1] = bundle end
end

function test_lock_lookahead_sends_a_value_at_the_pulse_it_was_scheduled_for()
  local sent, send = recorder()
  local scheduler = lookahead.new{send = send}
  scheduler:schedule(10, {channel = 1, step = 5, slot = 1, value = 64})
  scheduler:serve(9)
  luaunit.assert_equals(#sent, 0)
  scheduler:serve(10)
  luaunit.assert_equals(#sent, 1)
  luaunit.assert_equals(sent[1].value, 64)
end

function test_lock_lookahead_sends_each_value_once()
  local sent, send = recorder()
  local scheduler = lookahead.new{send = send}
  scheduler:schedule(10, {channel = 1, step = 5, slot = 1, value = 64})
  scheduler:serve(10)
  scheduler:serve(10)
  scheduler:serve(11)
  luaunit.assert_equals(#sent, 1)
end

function test_lock_lookahead_sends_a_pulse_that_was_skipped_rather_than_dropping_it()
  -- A pulse the sequencer never serviced still owes its values; they leave at
  -- the next service and are marked late rather than lost.
  local sent, send = recorder()
  local scheduler = lookahead.new{send = send}
  scheduler:schedule(10, {channel = 1, step = 5, slot = 1, value = 64})
  scheduler:schedule(11, {channel = 1, step = 6, slot = 1, value = 65})
  scheduler:serve(12)
  luaunit.assert_equals(#sent, 2)
  luaunit.assert_true(sent[1].late)
  luaunit.assert_equals(scheduler:stats().late, 2)
end

function test_lock_lookahead_sends_values_of_one_pulse_in_scheduling_order()
  local sent, send = recorder()
  local scheduler = lookahead.new{send = send}
  scheduler:schedule(10, {channel = 1, slot = 1, value = 1})
  scheduler:schedule(10, {channel = 1, slot = 2, value = 2})
  scheduler:schedule(10, {channel = 2, slot = 1, value = 3})
  scheduler:serve(10)
  luaunit.assert_equals({sent[1].value, sent[2].value, sent[3].value}, {1, 2, 3})
end

function test_lock_lookahead_records_what_it_sent_so_the_step_does_not_repeat_it()
  local sent, send = recorder()
  local scheduler = lookahead.new{send = send}
  scheduler:schedule(10, {channel = 1, step = 5, slot = 1, value = 64})
  luaunit.assert_false(scheduler:was_sent(1, 5, 1, 64))
  scheduler:serve(10)
  luaunit.assert_true(scheduler:was_sent(1, 5, 1, 64))
  -- Only the identical value is suppressed; a changed one must still be sent.
  luaunit.assert_false(scheduler:was_sent(1, 5, 1, 65))
  luaunit.assert_false(scheduler:was_sent(1, 5, 2, 64))
  luaunit.assert_false(scheduler:was_sent(2, 5, 1, 64))
end

function test_lock_lookahead_forgets_a_commit_once_its_step_has_been_played()
  -- The record exists to stop one duplicate send, not to suppress the value
  -- when that step comes round again.
  local sent, send = recorder()
  local scheduler = lookahead.new{send = send}
  scheduler:schedule(10, {channel = 1, step = 5, slot = 1, value = 64})
  scheduler:serve(10)
  luaunit.assert_true(scheduler:was_sent(1, 5, 1, 64))
  scheduler:clear_commit(1, 5)
  luaunit.assert_false(scheduler:was_sent(1, 5, 1, 64))
end

function test_lock_lookahead_discards_everything_pending_at_a_pattern_boundary()
  -- No outgoing pattern's value may leave at or after a global reset.
  local sent, send = recorder()
  local scheduler = lookahead.new{send = send}
  scheduler:schedule(10, {channel = 1, step = 5, slot = 1, value = 64})
  scheduler:cancel_all()
  scheduler:serve(10)
  luaunit.assert_equals(#sent, 0)
  -- The scheduler stays usable for the incoming pattern.
  scheduler:schedule(11, {channel = 1, step = 1, slot = 1, value = 7})
  scheduler:serve(11)
  luaunit.assert_equals(#sent, 1)
end

function test_lock_lookahead_cancels_one_channel_without_touching_the_others()
  local sent, send = recorder()
  local scheduler = lookahead.new{send = send}
  scheduler:schedule(10, {channel = 1, step = 5, slot = 1, value = 1})
  scheduler:schedule(10, {channel = 2, step = 5, slot = 1, value = 2})
  scheduler:cancel_channel(1)
  scheduler:serve(10)
  luaunit.assert_equals(#sent, 1)
  luaunit.assert_equals(sent[1].channel, 2)
end

function test_lock_lookahead_replaces_an_unsent_value_for_the_same_target()
  -- An edit before the send replaces the pending value rather than queueing a
  -- second one, so the receiver never hears the superseded value.
  local sent, send = recorder()
  local scheduler = lookahead.new{send = send}
  scheduler:schedule(10, {channel = 1, step = 5, slot = 1, value = 64})
  scheduler:schedule(10, {channel = 1, step = 5, slot = 1, value = 90})
  scheduler:serve(10)
  luaunit.assert_equals(#sent, 1)
  luaunit.assert_equals(sent[1].value, 90)
end

function test_lock_lookahead_refuses_to_hold_more_than_its_cap()
  local sent, send = recorder()
  local scheduler = lookahead.new{send = send, capacity = 2}
  luaunit.assert_true(scheduler:schedule(10, {channel = 1, step = 1, slot = 1, value = 1}))
  luaunit.assert_true(scheduler:schedule(10, {channel = 1, step = 1, slot = 2, value = 2}))
  local accepted, reason = scheduler:schedule(10, {channel = 1, step = 1, slot = 3, value = 3})
  luaunit.assert_false(accepted)
  luaunit.assert_equals(reason, "horizon-limit")
  scheduler:serve(10)
  luaunit.assert_equals(#sent, 2)
  luaunit.assert_equals(scheduler:stats().horizon_limited, 1)
end

function test_lock_lookahead_frees_its_room_once_values_are_sent()
  local sent, send = recorder()
  local scheduler = lookahead.new{send = send, capacity = 1}
  luaunit.assert_true(scheduler:schedule(10, {channel = 1, step = 1, slot = 1, value = 1}))
  luaunit.assert_false(scheduler:schedule(11, {channel = 1, step = 2, slot = 1, value = 2}))
  scheduler:serve(10)
  luaunit.assert_true(scheduler:schedule(11, {channel = 1, step = 2, slot = 1, value = 2}))
end

function test_lock_lookahead_reports_nothing_pending_when_it_is_empty()
  local _, send = recorder()
  local scheduler = lookahead.new{send = send}
  luaunit.assert_equals(scheduler:stats().pending, 0)
  scheduler:schedule(10, {channel = 1, step = 1, slot = 1, value = 1})
  luaunit.assert_equals(scheduler:stats().pending, 1)
  scheduler:serve(10)
  luaunit.assert_equals(scheduler:stats().pending, 0)
end

function test_lock_lookahead_remembers_only_the_latest_step_sent_for_a_channel()
  -- The commit record is bounded to one step per channel. Keeping every step
  -- would grow without limit whenever a scheduled step was never played, which
  -- a pattern change can cause at any time.
  local sent, send = recorder()
  local scheduler = lookahead.new{send = send}
  scheduler:schedule(10, {channel = 1, step = 5, slot = 1, value = 1})
  scheduler:serve(10)
  scheduler:schedule(11, {channel = 1, step = 6, slot = 1, value = 2})
  scheduler:serve(11)
  luaunit.assert_true(scheduler:was_sent(1, 6, 1, 2))
  luaunit.assert_false(scheduler:was_sent(1, 5, 1, 1))
end

function test_lock_lookahead_drops_a_value_that_is_edited_before_it_leaves()
  -- The step will resolve the new value itself, so the stale one must not go.
  local sent, send = recorder()
  local scheduler = lookahead.new{send = send}
  scheduler:schedule(10, {channel = 1, step = 5, slot = 1, value = 64})
  scheduler:invalidate(1, 5, 1)
  scheduler:serve(10)
  luaunit.assert_equals(#sent, 0)
  luaunit.assert_false(scheduler:was_sent(1, 5, 1))
  luaunit.assert_equals(scheduler:stats().pending, 0)
end

function test_lock_lookahead_lets_the_step_resend_a_value_that_was_edited_after_it_left()
  -- Nothing can unsend what the receiver already heard, so the correction is
  -- that the step sends the new value at its own time, losing only the lead.
  local sent, send = recorder()
  local scheduler = lookahead.new{send = send}
  scheduler:schedule(10, {channel = 1, step = 5, slot = 1, value = 64})
  scheduler:serve(10)
  luaunit.assert_true(scheduler:was_sent(1, 5, 1, 64))
  scheduler:invalidate(1, 5, 1)
  luaunit.assert_false(scheduler:was_sent(1, 5, 1, 64))
end

function test_lock_lookahead_invalidation_leaves_other_slots_and_steps_alone()
  local sent, send = recorder()
  local scheduler = lookahead.new{send = send}
  scheduler:schedule(10, {channel = 1, step = 5, slot = 1, value = 1})
  scheduler:schedule(10, {channel = 1, step = 5, slot = 2, value = 2})
  scheduler:schedule(10, {channel = 2, step = 5, slot = 1, value = 3})
  scheduler:invalidate(1, 5, 1)
  scheduler:serve(10)
  luaunit.assert_equals(#sent, 2)
  luaunit.assert_equals({sent[1].value, sent[2].value}, {2, 3})
end

function test_lock_lookahead_invalidating_an_unknown_target_changes_nothing()
  local sent, send = recorder()
  local scheduler = lookahead.new{send = send}
  scheduler:schedule(10, {channel = 1, step = 5, slot = 1, value = 64})
  scheduler:invalidate(3, 9, 4)
  scheduler:serve(10)
  luaunit.assert_equals(#sent, 1)
end

function test_lock_lookahead_moves_a_rescheduled_value_to_its_new_pulse()
  -- Rewriting the pulse without moving the entry would fire it at the old time.
  local sent, send = recorder()
  local scheduler = lookahead.new{send = send}
  scheduler:schedule(10, {channel = 1, step = 5, slot = 1, value = 1})
  scheduler:schedule(20, {channel = 1, step = 5, slot = 1, value = 2})
  scheduler:serve(10)
  luaunit.assert_equals(#sent, 0, "the value must not leave at the pulse it no longer holds")
  scheduler:serve(20)
  luaunit.assert_equals(#sent, 1)
  luaunit.assert_equals(sent[1].value, 2)
end

function test_lock_lookahead_moves_a_rescheduled_value_earlier_too()
  local sent, send = recorder()
  local scheduler = lookahead.new{send = send}
  scheduler:schedule(20, {channel = 1, step = 5, slot = 1, value = 1})
  scheduler:schedule(10, {channel = 1, step = 5, slot = 1, value = 2})
  scheduler:serve(10)
  luaunit.assert_equals(#sent, 1)
  luaunit.assert_equals(sent[1].value, 2)
  scheduler:serve(20)
  luaunit.assert_equals(#sent, 1, "the retired entry must not fire again")
end

function test_lock_lookahead_invalidates_a_whole_step_when_its_locks_are_cleared()
  local sent, send = recorder()
  local scheduler = lookahead.new{send = send}
  scheduler:schedule(10, {channel = 1, step = 5, slot = 1, value = 1})
  scheduler:schedule(10, {channel = 1, step = 5, slot = 2, value = 2})
  scheduler:schedule(10, {channel = 1, step = 6, slot = 1, value = 3})
  scheduler:invalidate(1, 5, nil)
  scheduler:serve(10)
  luaunit.assert_equals(#sent, 1)
  luaunit.assert_equals(sent[1].step, 6)
end

function test_lock_lookahead_invalidates_a_whole_channel_when_its_locks_are_cleared()
  local sent, send = recorder()
  local scheduler = lookahead.new{send = send}
  scheduler:schedule(10, {channel = 1, step = 5, slot = 1, value = 1})
  scheduler:schedule(10, {channel = 2, step = 5, slot = 1, value = 2})
  scheduler:invalidate(1, nil, nil)
  scheduler:serve(10)
  luaunit.assert_equals(#sent, 1)
  luaunit.assert_equals(sent[1].channel, 2)
end

function test_lock_lookahead_forgets_what_it_sent_at_a_boundary()
  -- A value resolved from the outgoing pattern must not suppress the incoming
  -- pattern's lock for the same step, and must not survive a stop and restart.
  local sent, send = recorder()
  local scheduler = lookahead.new{send = send}
  scheduler:schedule(10, {channel = 1, step = 1, slot = 1, value = 64})
  scheduler:serve(10)
  luaunit.assert_true(scheduler:was_sent(1, 1, 1, 64))
  -- A boundary keeps what already left, so the step does not send it twice, and
  -- an incoming pattern whose value differs is not suppressed by it.
  scheduler:cancel_all()
  luaunit.assert_true(scheduler:was_sent(1, 1, 1, 64))
  luaunit.assert_false(scheduler:was_sent(1, 1, 1, 90))
  -- A restart forgets it, because patch recall may have replaced it.
  scheduler:forget_commits()
  luaunit.assert_false(scheduler:was_sent(1, 1, 1, 64))
end

-- A commit names where the value landed, not only which slot produced it. The
-- receiver holds one value per physical address, so only a write to that same
-- address can be the write the step would otherwise repeat.
function test_lock_lookahead_does_not_mistake_an_equal_value_at_another_address_for_its_commit()
  local sent, send = recorder()
  local scheduler = lookahead.new{send = send}
  scheduler:schedule(10, {channel = 1, step = 1, slot = 1, value = 64, destination = 501})
  scheduler:serve(10)
  luaunit.assert_true(scheduler:was_sent(1, 1, 1, 64, 501))
  -- The same slot and value, addressed elsewhere: nothing was sent there.
  luaunit.assert_false(scheduler:was_sent(1, 1, 1, 64, 502))
end

function test_lock_lookahead_forgets_a_commit_when_something_else_writes_its_address()
  -- A live control turned after the early send puts a different value on the
  -- receiver. The commit no longer describes what the receiver holds, so the
  -- step must send its lock again; the resend cache is told the same.
  local sent, send = recorder()
  local overridden = {}
  local scheduler = lookahead.new{send = send,
    on_override = function(channel, slot) overridden[#overridden + 1] = channel .. ":" .. slot end}
  scheduler:schedule(10, {channel = 1, step = 5, slot = 1, value = 64, destination = 501})
  scheduler:serve(10)
  luaunit.assert_true(scheduler:was_sent(1, 5, 1, 64, 501))
  scheduler:observe_write(501)
  luaunit.assert_false(scheduler:was_sent(1, 5, 1, 64, 501))
  luaunit.assert_equals(overridden, {"1:1"})
  -- A write to some other address leaves other commits alone.
  scheduler:schedule(11, {channel = 2, step = 5, slot = 3, value = 9, destination = 777})
  scheduler:serve(11)
  scheduler:observe_write(123)
  luaunit.assert_true(scheduler:was_sent(2, 5, 3, 9, 777))
  luaunit.assert_equals(#overridden, 1)
end

function test_lock_lookahead_keeps_the_commit_for_its_own_write()
  -- The early send itself goes through the same MIDI write path as everything
  -- else. It must be recognised as the commit, not as an override of it.
  local scheduler
  local overridden = 0
  scheduler = lookahead.new{
    send = function(bundle) scheduler:observe_write(bundle.destination) end,
    on_override = function() overridden = overridden + 1 end}
  scheduler:schedule(10, {channel = 1, step = 5, slot = 1, value = 64, destination = 501})
  scheduler:serve(10)
  luaunit.assert_true(scheduler:was_sent(1, 5, 1, 64, 501))
  luaunit.assert_equals(overridden, 0)
end

function test_lock_lookahead_stops_watching_an_address_once_its_step_has_played()
  -- The record is released with the step, so a later write to that address is
  -- not reported as overriding a value the step has already dealt with.
  local sent, send = recorder()
  local overridden = 0
  local scheduler = lookahead.new{send = send, on_override = function() overridden = overridden + 1 end}
  scheduler:schedule(10, {channel = 1, step = 5, slot = 1, value = 64, destination = 501})
  scheduler:serve(10)
  scheduler:clear_commit(1, 5)
  scheduler:observe_write(501)
  luaunit.assert_equals(overridden, 0)
  -- The same after the channel's record is invalidated or forgotten.
  scheduler:schedule(11, {channel = 1, step = 6, slot = 1, value = 64, destination = 501})
  scheduler:serve(11)
  scheduler:invalidate(1, 6, 1)
  scheduler:observe_write(501)
  luaunit.assert_equals(overridden, 0)
  scheduler:schedule(12, {channel = 1, step = 7, slot = 1, value = 64, destination = 501})
  scheduler:serve(12)
  scheduler:forget_commits()
  scheduler:observe_write(501)
  luaunit.assert_equals(overridden, 0)
end

function test_lock_lookahead_cancels_pending_values_for_addresses_that_became_shared()
  -- An address another track has just been assigned keeps lead-0 timing, so a
  -- value already resolved for it must leave at its own step, not early.
  local sent, send = recorder()
  local scheduler = lookahead.new{send = send}
  scheduler:schedule(10, {channel = 1, step = 5, slot = 1, value = 64, destination = 501})
  scheduler:schedule(10, {channel = 1, step = 5, slot = 2, value = 65, destination = 502})
  scheduler:cancel_destinations({[501] = true})
  scheduler:serve(10)
  luaunit.assert_equals(#sent, 1)
  luaunit.assert_equals(sent[1].value, 65)
  luaunit.assert_equals(scheduler:stats().pending, 0)
end
