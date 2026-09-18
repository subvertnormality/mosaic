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

-- The record holds the value that was actually put on the wire and the physical
-- address it went to, not merely that something was sent. A step then
-- suppresses its own send only when it would send the identical value to the
-- identical address, so an edit, a pattern change that puts another control in
-- the slot, or anything else that alters what the step resolves is corrected at
-- the step instead of being swallowed by a stale commitment. It is held per
-- channel, because one channel has one step's values in flight, and keying it
-- by step as well would grow without bound whenever a scheduled step was never
-- played.
--
-- The address is also indexed the other way, so a write to it from anywhere
-- else (a live control, a slide, another track) can find the commit it has just
-- made untrue. The receiver holds one value per address, and after that write
-- it is no longer holding the one recorded here.
local function release_slot(self, commits, slot)
  local destination = commits.destinations[slot]
  if destination ~= nil and self.owner_channel[destination] == commits.channel
      and self.owner_slot[destination] == slot then
    self.owner_channel[destination] = nil
    self.owner_slot[destination] = nil
  end
  commits.slots[slot] = nil
  commits.destinations[slot] = nil
end

local function drop_commits(self, channel)
  local commits = self.commits[channel]
  if commits then
    for slot in pairs(commits.destinations) do release_slot(self, commits, slot) end
    self.commits[channel] = nil
  end
end

local function commits_for(self, channel, step)
  local commits = self.commits[channel]
  if commits == nil or commits.step ~= step then
    drop_commits(self, channel)
    commits = {channel = channel, step = step, slots = {}, destinations = {}}
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
    if existing.pulse == pulse then
      existing.bundle = bundle
      return true
    end
    -- A different pulse means a different bucket. Rewriting the field alone
    -- would leave the entry in the bucket it was first filed under, so it would
    -- fire at the old time; retire it here and file the replacement below.
    existing.cancelled = true
    self.cancelled_count = self.cancelled_count + 1
    self.pending = self.pending - 1
    self.pending_by_target[key] = nil
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
  -- The send decides again whether this value is still wanted. A refusal is not
  -- a failure: nothing is recorded, so the slot's own step sends what is then in
  -- force rather than a value the player has since overruled. The send reaches
  -- the wire through the same path every other write takes, and that path
  -- reports back here; while this flag is up the report is of this send itself.
  self.dispatching = true
  local accepted = self.send(bundle) ~= false
  self.dispatching = false
  if accepted then
    local commits = commits_for(self, bundle.channel, bundle.step)
    local slot, destination = bundle.slot, bundle.destination
    release_slot(self, commits, slot)
    commits.slots[slot] = bundle.value
    commits.destinations[slot] = destination
    if destination ~= nil then
      self.owner_channel[destination] = bundle.channel
      self.owner_slot[destination] = slot
    end
  end
end

-- Send everything owed at or before this pulse, in the order it was scheduled.
-- Runs inside the sequencer's pulse; there is no timer.
function Scheduler:serve(pulse)
  -- Buckets are released even with nothing pending: cancelling the only value in
  -- one leaves it behind, and a scan that never revisits it would keep those
  -- bundles for the rest of the performance and make channel invalidation walk
  -- the whole history.
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

-- True only when this exact value already left for this exact step and slot,
-- to this exact address. Anything else -- a different value, a different
-- address, a different step, nothing recorded -- means the step must send, so a
-- correction is never lost.
function Scheduler:was_sent(channel, step, slot, value, destination)
  local commits = self.commits[channel]
  return commits ~= nil and commits.step == step and commits.slots[slot] ~= nil
    and commits.slots[slot] == value and commits.destinations[slot] == destination
end

-- Something other than this scheduler has written an address. Whatever commit
-- claimed that address no longer describes what the receiver holds, so it is
-- forgotten and the slot's own step sends its value again. The resend cache is
-- told as well, because it too believes the receiver still holds the old value.
function Scheduler:observe_write(destination)
  if self.dispatching or destination == nil then return end
  local channel = self.owner_channel[destination]
  if channel == nil then return end
  local slot = self.owner_slot[destination]
  local commits = self.commits[channel]
  if commits then release_slot(self, commits, slot) end
  if self.on_override then self.on_override(channel, slot) end
end

function Scheduler:clear_commit(channel, step)
  local commits = self.commits[channel]
  if commits and commits.step == step then drop_commits(self, channel) end
end

-- An edit to a value that has not left yet simply removes it, because the step
-- will resolve the new value itself. An edit to one that has already left clears
-- the record of it instead, so the step sends the corrected value at its own
-- time: nothing can unsend what the receiver already heard, and the correction
-- costs that value its lead rather than leaving a stale value in force.
function Scheduler:invalidate(channel, step, slot)
  if step == nil or slot == nil then
    -- Clearing a whole step or a whole channel invalidates every value that
    -- came from it, not just one slot.
    for _, bucket in pairs(self.buckets) do
      for index = 1, #bucket do
        local entry = bucket[index]
        local bundle = entry.bundle
        if not entry.cancelled and not entry.sent and bundle.channel == channel
            and (step == nil or bundle.step == step)
            and (slot == nil or bundle.slot == slot) then
          entry.cancelled = true
          self.cancelled_count = self.cancelled_count + 1
          self.pending = self.pending - 1
          if self.pending_by_target[entry.key] == entry then
            self.pending_by_target[entry.key] = nil
          end
        end
      end
    end
    local commits = self.commits[channel]
    if commits and (step == nil or commits.step == step) then drop_commits(self, channel) end
    return
  end
  local key = target_key({channel = channel, step = step, slot = slot})
  local entry = self.pending_by_target[key]
  if entry and not entry.sent and not entry.cancelled then
    entry.cancelled = true
    self.cancelled_count = self.cancelled_count + 1
    self.pending = self.pending - 1
    self.pending_by_target[key] = nil
  end
  local commits = self.commits[channel]
  if commits and commits.step == step then release_slot(self, commits, slot) end
end

-- A transport or pattern boundary discards every value that has not left yet.
-- What has already left is kept: forgetting it would make the step send the same
-- value a second time, and it cannot suppress an incoming pattern's lock because
-- a differing value, or the same value at a different address, no longer
-- matches. A stop clears it separately, since patch recall can replace what the
-- receiver holds while the transport is stopped.
function Scheduler:cancel_all()
  self.buckets = {}
  self.pending_by_target = {}
  self.pending = 0
  self.cancelled_count = 0
  self.earliest = math.huge
end

-- Forget what the receiver was last told, for a restart where something else may
-- have changed it in the meantime.
function Scheduler:forget_commits()
  self.commits = {}
  self.owner_channel = {}
  self.owner_slot = {}
end

local function cancel_unless(self, keep)
  for _, bucket in pairs(self.buckets) do
    for position = 1, #bucket do
      local entry = bucket[position]
      if not entry.cancelled and not entry.sent and not keep(entry.bundle) then
        entry.cancelled = true
        self.cancelled_count = self.cancelled_count + 1
        self.pending = self.pending - 1
        if self.pending_by_target[entry.key] == entry then
          self.pending_by_target[entry.key] = nil
        end
      end
    end
  end
end

function Scheduler:cancel_channel(channel)
  cancel_unless(self, function(bundle) return bundle.channel ~= channel end)
end

-- An address that has just become shared between tracks keeps lead-0 timing
-- from now on, so a value already resolved for it leaves at its own step.
function Scheduler:cancel_destinations(destinations)
  cancel_unless(self, function(bundle)
    return bundle.destination == nil or not destinations[bundle.destination]
  end)
end

function Scheduler:stats()
  return {pending = self.pending, max_pending = self.max_pending,
          late = self.late, horizon_limited = self.horizon_limited,
          cancelled = self.cancelled_count, capacity = self.capacity}
end

function lookahead.new(deps)
  return setmetatable({send = deps.send, on_override = deps.on_override,
                       capacity = deps.capacity or 10240,
                       buckets = {}, pending_by_target = {}, commits = {},
                       owner_channel = {}, owner_slot = {}, dispatching = false,
                       pending = 0, max_pending = 0, late = 0, horizon_limited = 0,
                       cancelled_count = 0, earliest = math.huge}, Scheduler)
end

return lookahead
