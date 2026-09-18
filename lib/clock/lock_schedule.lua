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

return schedule
