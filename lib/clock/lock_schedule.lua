-- The lock lookahead scheduling rule, as pure arithmetic.
--
-- A value intended at T on a receiver channel is sent at
--
--   S = max(T - L, (A + T) / 2)   clamped to the epoch start and availability
--
-- where L is the requested lead and A is the latest protected anchor strictly
-- before T on that same physical receiver channel. A protected anchor is a
-- planned eligible trig onset, whether or not its note decision eventually
-- passes, which is what lets the rule avoid predicting the outcome of a
-- probability or condition.
--
-- The midpoint exists so a value cannot cross the note before it. Halfway
-- between the previous note and this one is the earliest a value may move
-- without landing on the wrong side of a note the player has already heard, so
-- when notes are closer together than twice the lead the lead shortens rather
-- than the ordering breaking.
--
-- The effective lead is T - S and is never negative. A value whose send time has
-- already passed is marked late and leaves promptly; it is never given back the
-- lead it did not achieve, and never discarded for being late.
local schedule = {}

-- The clamps in the order they are applied. The reported reason is the clamp
-- that actually moved the send, so a constraint that did not bind is not blamed.
local function clamp(send, limit, reason, current_reason)
  if limit and limit > send then return limit, reason end
  return send, current_reason
end

function schedule.plan(request)
  local intended, lead = request.intended, request.lead or 0
  local send, reason = intended - lead, nil

  -- Only a strictly earlier anchor constrains the send. A note at or after the
  -- value's own time is not a previous note.
  local anchor = request.anchor
  if anchor and anchor < intended then
    local midpoint = (anchor + intended) / 2
    if midpoint > send then send, reason = midpoint, "spacing" end
  end

  send, reason = clamp(send, request.epoch_start, "pattern-boundary", reason)
  send, reason = clamp(send, request.available, "startup", reason)

  local effective = intended - send
  if effective < 0 then effective = 0 end

  local now = request.now
  local late = false
  if now and now > send then
    late = true
    send = now
    effective = intended - send
    if effective < 0 then effective = 0 end
  elseif request.available and request.available > intended then
    -- Known only after its own time: owed immediately, with no lead achieved.
    late = true
  end

  return {send = send, effective_lead = effective, reason = reason, late = late}
end

-- The separate pulse-advance contract.
--
-- schedule.plan decides when a value should ideally leave. This maps that time
-- onto the pulse train, so the value leaves inside a pulse the sequencer was
-- already running rather than from a timer firing part way through a step. The
-- lead is then quantised to the pulse grid: less accurate against a requested
-- figure in milliseconds, but consistent between events, which is the property
-- a player hears.
--
-- The value takes the latest pulse at or before its desired send, so the lead
-- rounds up rather than down; rounding the other way would deliver less lead
-- than asked for. If no pulse lies between the floor and the desired send, it
-- takes the first pulse at or after the floor, up to its own pulse, and reports
-- the lead it actually achieved. It never moves past its own pulse.
--
-- This is a different contract from exact milliseconds, not a rounding of it. It
-- carries its own name in every report so a result cannot be read as if it had
-- qualified exact-millisecond timing.
function schedule.pulse_plan(request)
  local intended, desired = request.intended, request.send
  local intended_pulse, pulse_time = request.intended_pulse, request.pulse_time
  local floor_time = request.floor

  -- The searches run inside a pulse, so they are bounded rather than trusting
  -- the caller. A lead of at most 50 ms spans far fewer pulses than this; a walk
  -- that reaches the limit means the request was out of contract, and the value
  -- keeps the earliest pulse the search reached rather than scanning the run.
  local limit = request.max_pulses or 64
  local floor_pulse = intended_pulse - limit
  if floor_pulse < 0 then floor_pulse = 0 end

  local pulse = intended_pulse
  while pulse > floor_pulse and pulse_time(pulse) > desired do pulse = pulse - 1 end

  if floor_time and pulse_time(pulse) < floor_time then
    -- No pulse sits in the permitted window, so take the first one at or after
    -- the floor instead, without passing the value's own pulse.
    pulse = intended_pulse
    local candidate = pulse
    while candidate > floor_pulse and pulse_time(candidate) >= floor_time do
      pulse = candidate
      candidate = candidate - 1
    end
  end

  if pulse > intended_pulse then pulse = intended_pulse end
  if pulse < 0 then pulse = 0 end

  local send = pulse_time(pulse)
  if send > intended then send = intended end
  local effective = intended - send
  if effective < 0 then effective = 0 end

  return {contract = "pulse-advance", pulse = pulse, send = send,
          effective_lead = effective, quantisation_error = desired - send,
          reason = request.reason}
end

return schedule
