-- The lock lookahead scheduling rule. For a value intended at T with requested
-- lead L on a receiver channel whose latest protected anchor strictly before T is
-- A, the value is sent at S = max(T - L, (A + T) / 2), then clamped to the epoch
-- start and to the time the preview could first know it. The effective lead is
-- T - S and never negative.
--
-- The rule exists so a value cannot overtake the note before it: halfway between
-- the previous note and this one is the earliest a value may move without
-- landing on the wrong side of a note the player already heard.
local schedule = include("mosaic/lib/clock/lock_schedule")

function test_lock_schedule_sends_a_full_lead_before_an_unobstructed_value()
  local plan = schedule.plan{intended = 10.0, lead = 0.025}
  luaunit.assert_almost_equals(plan.send, 9.975, 1e-9)
  luaunit.assert_almost_equals(plan.effective_lead, 0.025, 1e-9)
  luaunit.assert_nil(plan.reason)
end

function test_lock_schedule_keeps_the_full_lead_when_the_previous_note_is_far_enough_away()
  -- Anchor two leads back: the midpoint is earlier than T - L, so L is honoured.
  local plan = schedule.plan{intended = 10.0, lead = 0.025, anchor = 9.9}
  luaunit.assert_almost_equals(plan.send, 9.975, 1e-9)
  luaunit.assert_almost_equals(plan.effective_lead, 0.025, 1e-9)
  luaunit.assert_nil(plan.reason)
end

function test_lock_schedule_waits_until_halfway_when_notes_are_closer_than_twice_the_lead()
  -- Steps 30 ms apart with a 25 ms lead: the value cannot precede its own note
  -- by more than half the gap without crossing the previous note.
  local plan = schedule.plan{intended = 10.0, lead = 0.025, anchor = 9.97}
  luaunit.assert_almost_equals(plan.send, 9.985, 1e-9)
  luaunit.assert_almost_equals(plan.effective_lead, 0.015, 1e-9)
  luaunit.assert_equals(plan.reason, "spacing")
end

function test_lock_schedule_reports_exactly_half_the_gap_at_the_spacing_boundary()
  -- Gap exactly twice the lead: the midpoint and T - L coincide, and the full
  -- lead is still honoured rather than reported as limited.
  local plan = schedule.plan{intended = 10.0, lead = 0.025, anchor = 9.95}
  luaunit.assert_almost_equals(plan.send, 9.975, 1e-9)
  luaunit.assert_almost_equals(plan.effective_lead, 0.025, 1e-9)
  luaunit.assert_nil(plan.reason)
end

function test_lock_schedule_never_sends_before_the_epoch_that_produced_the_value()
  -- No outgoing value may leave before a global pattern reset, even a repeat.
  local plan = schedule.plan{intended = 10.0, lead = 0.025, epoch_start = 9.99}
  luaunit.assert_almost_equals(plan.send, 9.99, 1e-9)
  luaunit.assert_almost_equals(plan.effective_lead, 0.01, 1e-9)
  luaunit.assert_equals(plan.reason, "pattern-boundary")
end

function test_lock_schedule_never_sends_before_the_preview_could_know_the_value()
  local plan = schedule.plan{intended = 10.0, lead = 0.025, available = 9.98}
  luaunit.assert_almost_equals(plan.send, 9.98, 1e-9)
  luaunit.assert_almost_equals(plan.effective_lead, 0.02, 1e-9)
  luaunit.assert_equals(plan.reason, "startup")
end

function test_lock_schedule_reports_the_latest_clamp_when_several_apply()
  -- The binding constraint is the one that actually moved the send.
  local plan = schedule.plan{intended = 10.0, lead = 0.025, anchor = 9.97,
                             epoch_start = 9.99, available = 9.96}
  luaunit.assert_almost_equals(plan.send, 9.99, 1e-9)
  luaunit.assert_equals(plan.reason, "pattern-boundary")
end

function test_lock_schedule_gives_a_zero_lead_when_the_value_is_only_known_at_its_step()
  -- Step one of a fresh transport: the lock is resolved at the step itself, so
  -- it leaves with its note and honestly reports no lead at all.
  local plan = schedule.plan{intended = 10.0, lead = 0.025, available = 10.0}
  luaunit.assert_almost_equals(plan.send, 10.0, 1e-9)
  luaunit.assert_equals(plan.effective_lead, 0)
  luaunit.assert_equals(plan.reason, "startup")
end

function test_lock_schedule_clamps_a_lead_that_would_precede_the_intended_time_backwards()
  -- Availability after T cannot pull the send later than the value's own time;
  -- a value already overdue leaves promptly and is marked late by the caller.
  local plan = schedule.plan{intended = 10.0, lead = 0.025, available = 10.5}
  luaunit.assert_almost_equals(plan.send, 10.5, 1e-9)
  luaunit.assert_equals(plan.effective_lead, 0)
  luaunit.assert_true(plan.late)
end

function test_lock_schedule_treats_a_zero_lead_as_the_existing_step_time_path()
  local plan = schedule.plan{intended = 10.0, lead = 0, anchor = 9.97}
  luaunit.assert_almost_equals(plan.send, 10.0, 1e-9)
  luaunit.assert_equals(plan.effective_lead, 0)
  luaunit.assert_nil(plan.reason)
end

function test_lock_schedule_ignores_an_anchor_that_is_not_strictly_before_the_value()
  -- A note at the same time as the value is not a previous note; only a strictly
  -- earlier protected anchor constrains the send.
  local plan = schedule.plan{intended = 10.0, lead = 0.025, anchor = 10.0}
  luaunit.assert_almost_equals(plan.send, 9.975, 1e-9)
  luaunit.assert_nil(plan.reason)
  local later = schedule.plan{intended = 10.0, lead = 0.025, anchor = 10.1}
  luaunit.assert_almost_equals(later.send, 9.975, 1e-9)
end

function test_lock_schedule_marks_a_send_that_is_already_overdue_without_restating_the_lead()
  -- now is past the computed send: the value is late, and its effective lead is
  -- what it will actually achieve, not the lead that was requested.
  local plan = schedule.plan{intended = 10.0, lead = 0.025, now = 9.99}
  luaunit.assert_true(plan.late)
  luaunit.assert_almost_equals(plan.send, 9.99, 1e-9)
  luaunit.assert_almost_equals(plan.effective_lead, 0.01, 1e-9)
end

function test_lock_schedule_is_not_late_when_the_send_is_still_ahead_of_now()
  local plan = schedule.plan{intended = 10.0, lead = 0.025, now = 9.9}
  luaunit.assert_false(plan.late)
  luaunit.assert_almost_equals(plan.send, 9.975, 1e-9)
end

-- The separate pulse-advance contract. The exact-millisecond rule above decides
-- the desired send time; this maps it onto the pulse train, so a value leaves
-- inside a pulse the sequencer was already running rather than from a timer
-- firing part way through a step. The lead is then quantised to the pulse grid:
-- less accurate against a requested figure, but consistent between events.
local function pulses(interval)
  return function(index) return index * interval end
end

function test_pulse_advance_uses_the_latest_pulse_at_or_before_the_desired_send()
  -- Pulses every 5 ms, value intended at 100 ms with a 25 ms lead: the desired
  -- send is 75 ms, which is exactly pulse 15.
  local plan = schedule.pulse_plan{intended = 0.100, send = 0.075, intended_pulse = 20,
                                   pulse_time = pulses(0.005)}
  luaunit.assert_equals(plan.pulse, 15)
  luaunit.assert_almost_equals(plan.send, 0.075, 1e-9)
  luaunit.assert_almost_equals(plan.effective_lead, 0.025, 1e-9)
end

function test_pulse_advance_takes_the_latest_pulse_at_or_before_the_desired_send()
  -- Desired send 73 ms falls between pulses. The latest pulse at or before it is
  -- 14 at 70 ms, so the lead rounds up to 30 ms. Rounding the other way would
  -- deliver less lead than asked for and could cross the permitted floor.
  local plan = schedule.pulse_plan{intended = 0.100, send = 0.073, intended_pulse = 20,
                                   pulse_time = pulses(0.005)}
  luaunit.assert_equals(plan.pulse, 14)
  luaunit.assert_almost_equals(plan.send, 0.070, 1e-9)
  luaunit.assert_almost_equals(plan.effective_lead, 0.030, 1e-9)
end

function test_pulse_advance_never_sends_before_its_floor()
  -- The midpoint or epoch floor binds: no pulse earlier than it may be used.
  local plan = schedule.pulse_plan{intended = 0.100, send = 0.075, floor = 0.082,
                                   intended_pulse = 20, pulse_time = pulses(0.005)}
  luaunit.assert_equals(plan.pulse, 17)
  luaunit.assert_almost_equals(plan.send, 0.085, 1e-9)
  luaunit.assert_true(plan.send >= 0.082)
end

function test_pulse_advance_falls_back_to_the_value_s_own_pulse_when_no_earlier_one_is_legal()
  -- The floor sits above every earlier pulse, so the value leaves with its step
  -- and honestly reports no lead rather than being sent too early.
  local plan = schedule.pulse_plan{intended = 0.100, send = 0.075, floor = 0.099,
                                   intended_pulse = 20, pulse_time = pulses(0.005)}
  luaunit.assert_equals(plan.pulse, 20)
  luaunit.assert_equals(plan.effective_lead, 0)
end

function test_pulse_advance_never_moves_a_value_past_its_own_intended_pulse()
  local plan = schedule.pulse_plan{intended = 0.100, send = 0.140, intended_pulse = 20,
                                   pulse_time = pulses(0.005)}
  luaunit.assert_equals(plan.pulse, 20)
  luaunit.assert_equals(plan.effective_lead, 0)
end

function test_pulse_advance_gives_every_value_of_one_step_the_same_pulse()
  -- Consistency between events is the property this contract buys: two values
  -- intended together leave together, whatever their requested lead rounds to.
  local a = schedule.pulse_plan{intended = 0.100, send = 0.075, intended_pulse = 20,
                                pulse_time = pulses(0.005)}
  local b = schedule.pulse_plan{intended = 0.100, send = 0.0755, intended_pulse = 20,
                                pulse_time = pulses(0.005)}
  luaunit.assert_equals(a.pulse, b.pulse)
  luaunit.assert_equals(a.send, b.send)
end

function test_pulse_advance_reports_the_quantisation_it_applied()
  local plan = schedule.pulse_plan{intended = 0.100, send = 0.073, intended_pulse = 20,
                                   pulse_time = pulses(0.005)}
  luaunit.assert_equals(plan.contract, "pulse-advance")
  luaunit.assert_almost_equals(plan.quantisation_error, 0.003, 1e-9)
end

function test_pulse_advance_bounds_its_search_instead_of_scanning_the_whole_run()
  -- An out-of-contract desired send must not walk back through every pulse of
  -- the performance; the search stops at its bound and keeps that pulse.
  local visited = 0
  local counted = function(index) visited = visited + 1; return index * 0.005 end
  local plan = schedule.pulse_plan{intended = 5.000, send = 0.0, intended_pulse = 1000,
                                   pulse_time = counted, max_pulses = 8}
  luaunit.assert_equals(plan.pulse, 992)
  luaunit.assert_true(visited <= 16, "search visited " .. visited .. " pulses")
end
