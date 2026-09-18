-- Lookahead scheduler for the pulse-advance contract.
--
-- Values for a future step are resolved early and held against the pulse that
-- will send them. Serving happens inside the sequencer's own pulse, so no timer
-- exists here and no value is dispatched part way through a step's work. A pulse
-- that was never serviced still owes its values: they leave at the next service
-- marked late, rather than being dropped or silently credited with a lead they
-- did not achieve.
--
-- A value sent early is recorded so the step it belongs to does not send it a
-- second time. That record clears when the step is played, because it exists to
-- prevent one duplicate, not to suppress the value next time round.
local lookahead = {}

local Scheduler = {}
Scheduler.__index = Scheduler

local function target_key(bundle)
  return (bundle.channel or 0) .. ":" .. (bundle.step or 0) .. ":" .. (bundle.slot or 0)
end

-- One channel can only have one step's values in flight, so the record of what
-- was sent early is held per channel rather than per channel and step. Keying it
-- by step as well would grow without bound whenever a step was scheduled and
-- then never played, which a pattern change can do at any time.
local function commits_for(self, channel, step)
  local commits = self.commits[channel]
  if commits == nil or commits.step ~= step then
    commits = {step = step, slots = {}}
    self.commits[channel] = commits
  end
  return commits
end

-- Replace an unsent value for the same target rather than queueing a second
-- one, so a receiver never hears a value that an edit already superseded.
function Scheduler:schedule(pulse, bundle)
  local key = target_key(bundle)
  local existing = self.pending_by_target[key]
  if existing and not existing.sent then
    existing.bundle = bundle
    existing.pulse = pulse
    return true
  end
  if self.pending >= self.capacity then
    self.horizon_limited = self.horizon_limited + 1
    return false, "horizon-limit"
  end
  local bucket = self.buckets[pulse]
  if bucket == nil then
    bucket = {}
    self.buckets[pulse] = bucket
    if pulse < self.earliest then self.earliest = pulse end
  end
  local entry = {bundle = bundle, pulse = pulse, key = key}
  bucket[#bucket + 1] = entry
  self.pending_by_target[key] = entry
  self.pending = self.pending + 1
  if self.pending > self.max_pending then self.max_pending = self.pending end
  return true
end

local function dispatch(self, entry, pulse)
  local bundle = entry.bundle
  if entry.pulse < pulse then
    bundle.late = true
    self.late = self.late + 1
  end
  entry.sent = true
  self.pending = self.pending - 1
  if self.pending_by_target[entry.key] == entry then
    self.pending_by_target[entry.key] = nil
  end
  commits_for(self, bundle.channel, bundle.step).slots[bundle.slot] = true
  self.send(bundle)
end

-- Send everything owed at or before this pulse, in the order it was scheduled.
-- Runs inside the sequencer's pulse; there is no timer.
function Scheduler:serve(pulse)
  if self.pending == 0 then
    self.earliest = pulse
    return
  end
  for index = self.earliest, pulse do
    local bucket = self.buckets[index]
    if bucket then
      for position = 1, #bucket do
        local entry = bucket[position]
        if not entry.cancelled and not entry.sent then dispatch(self, entry, pulse) end
      end
      self.buckets[index] = nil
    end
  end
  self.earliest = pulse
end

function Scheduler:was_sent(channel, step, slot)
  local commits = self.commits[channel]
  return commits ~= nil and commits.step == step and commits.slots[slot] == true
end

function Scheduler:clear_commit(channel, step)
  local commits = self.commits[channel]
  if commits and commits.step == step then self.commits[channel] = nil end
end

-- A global pattern reset discards every speculative value at once.
function Scheduler:cancel_all()
  self.buckets = {}
  self.pending_by_target = {}
  self.pending = 0
end

function Scheduler:cancel_channel(channel)
  for _, bucket in pairs(self.buckets) do
    for position = 1, #bucket do
      local entry = bucket[position]
      if not entry.cancelled and not entry.sent and entry.bundle.channel == channel then
        entry.cancelled = true
        self.pending = self.pending - 1
        if self.pending_by_target[entry.key] == entry then
          self.pending_by_target[entry.key] = nil
        end
      end
    end
  end
end

function Scheduler:stats()
  return {pending = self.pending, max_pending = self.max_pending,
          late = self.late, horizon_limited = self.horizon_limited,
          capacity = self.capacity}
end

function lookahead.new(deps)
  return setmetatable({send = deps.send, capacity = deps.capacity or 10240,
                       buckets = {}, pending_by_target = {}, commits = {},
                       pending = 0, max_pending = 0, late = 0, horizon_limited = 0,
                       earliest = math.huge}, Scheduler)
end

return lookahead
