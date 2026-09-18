-- Bounded cancellable queue of pending parameter values for lock lookahead.
--
-- Every pending value shares one earliest-deadline wakeup: there is no timer per
-- bundle, track or lead. Entries are ordered by deadline and then by insertion,
-- so values intended for the same time keep the slot order playback would have
-- used. Cancellation marks the entries present at the time, and cancelled
-- entries are compacted in bounded work rather than accumulating.
--
-- The cap is a refusal, not a silent drop: a value that cannot be admitted is
-- rejected so the caller can shorten its effective lead and report a
-- horizon-limit, while every value already accepted is still owed and still
-- served, even if its deadline has passed.
local lookahead = {}

-- Sixteen channels, a sixty-four occurrence horizon, ten parameter slots.
lookahead.MAX_BUNDLES = 16 * 64 * 10

local Queue = {}
Queue.__index = Queue

local function less(a, b)
  if a.deadline ~= b.deadline then return a.deadline < b.deadline end
  return a.ordinal < b.ordinal
end

local function sift_up(heap, index)
  while index > 1 do
    local parent = index // 2
    if less(heap[index], heap[parent]) then
      heap[index], heap[parent] = heap[parent], heap[index]
      index = parent
    else
      return
    end
  end
end

local function sift_down(heap, index, size)
  while true do
    local left, smallest = index * 2, index
    if left <= size and less(heap[left], heap[smallest]) then smallest = left end
    if left + 1 <= size and less(heap[left + 1], heap[smallest]) then smallest = left + 1 end
    if smallest == index then return end
    heap[index], heap[smallest] = heap[smallest], heap[index]
    index = smallest
  end
end

local function pop_root(self)
  local heap, size = self.heap, self.size
  local root = heap[1]
  heap[1] = heap[size]
  heap[size] = nil
  self.size = size - 1
  if self.size > 0 then sift_down(heap, 1, self.size) end
  return root
end

-- Rebuild without the cancelled entries. Run only when they outnumber the live
-- ones, so the amortised cost per admitted value stays constant.
local function compact(self)
  local live, count = {}, 0
  for index = 1, self.size do
    local entry = self.heap[index]
    if not entry.cancelled then
      count = count + 1
      live[count] = entry
    end
    self.heap[index] = nil
  end
  for index = 1, count do self.heap[index] = live[index] end
  for index = count // 2, 1, -1 do sift_down(self.heap, index, count) end
  self.size = count
  self.cancelled_count = 0
end

-- Drop cancelled roots so the reported wakeup always belongs to a value that
-- will actually be sent.
local function settle(self)
  while self.size > 0 and self.heap[1].cancelled do
    pop_root(self)
    self.cancelled_count = self.cancelled_count - 1
    if self.cancelled_count < 0 then self.cancelled_count = 0 end
  end
end

function Queue:live()
  return self.size - self.cancelled_count
end

function Queue:push(deadline, payload, generation)
  settle(self)
  if self:live() >= self.capacity then
    self.rejected = self.rejected + 1
    return false, "horizon-limit"
  end
  if self.cancelled_count > self:live() then compact(self) end
  self.ordinal = self.ordinal + 1
  self.size = self.size + 1
  self.heap[self.size] = {deadline = deadline, payload = payload,
                          generation = generation, ordinal = self.ordinal}
  sift_up(self.heap, self.size)
  local live = self:live()
  if live > self.max_live then self.max_live = live end
  return true
end

-- The earliest deadline that will actually be served, or nil when nothing is
-- pending. One wakeup is scheduled from this.
function Queue:earliest()
  settle(self)
  if self.size == 0 then return nil end
  return self.heap[1].deadline
end

-- Return the next payload owed at this time, or nil. An overdue entry is still
-- owed and leaves here; lateness is the caller's to record, never a reason to
-- discard the value or to restate the lead that was actually achieved.
function Queue:pop_due(now)
  settle(self)
  if self.size == 0 or self.heap[1].deadline > now then return nil end
  return pop_root(self).payload
end

-- Cancellation marks the entries present now. It does not remember the
-- generation number, so a caller that reuses one is not silently ignored later.
function Queue:cancel_generation(generation)
  for index = 1, self.size do
    local entry = self.heap[index]
    if not entry.cancelled and entry.generation == generation then
      entry.cancelled = true
      self.cancelled_count = self.cancelled_count + 1
    end
  end
  if self.cancelled_count > self:live() then compact(self) end
end

function Queue:cancel(predicate)
  for index = 1, self.size do
    local entry = self.heap[index]
    if not entry.cancelled and predicate(entry.payload) then
      entry.cancelled = true
      self.cancelled_count = self.cancelled_count + 1
    end
  end
  if self.cancelled_count > self:live() then compact(self) end
end

-- A global pattern reset discards every speculative value at once.
function Queue:cancel_all()
  for index = 1, self.size do self.heap[index] = nil end
  self.size, self.cancelled_count = 0, 0
end

function Queue:stats()
  return {live = self:live(), stored = self.size, cancelled = self.cancelled_count,
          capacity = self.capacity, max_live = self.max_live, rejected = self.rejected}
end

function lookahead.new(capacity)
  return setmetatable({heap = {}, size = 0, ordinal = 0, cancelled_count = 0,
                       capacity = capacity or lookahead.MAX_BUNDLES,
                       max_live = 0, rejected = 0}, Queue)
end

return lookahead
