-- Diagnostic only. The caller installs this object as _G.mosaic_pulse_probe.
-- Playback does not include/allocate this module unless explicitly requested.
local timing_probe = {}

function timing_probe.new(options)
  local capacity = options.capacity
  assert(type(capacity) == "number" and capacity >= 1 and capacity % 1 == 0,
    "Probe capacity must be a positive integer")
  assert(type(options.now) == "function", "Probe requires a clock")
  local rows = {}
  for i = 1, capacity do rows[i] = {0, 0, 0, 0, 0, 0, 0, 0} end
  local next_row, count, dropped = 1, 0, 0
  local probe = {pulse = 0, enabled = true}

  -- kind: 1 pulse, 2 step parameter resolution, 3 note production,
  -- 4 output write, 5 delay callback, 6 delayed group dispatch.
  -- marker: 1 begin, 2 end. Deadlines use the same seconds epoch as now().
  function probe:record(kind, pulse, occurrence, deadline, marker, bytes, batches)
    if not self.enabled then return end
    local row = rows[next_row]
    row[1], row[2], row[3], row[4] = options.now(), kind, pulse or 0, occurrence or 0
    row[5], row[6], row[7], row[8] = deadline or 0, marker or 0, bytes or 0, batches or 0
    next_row = next_row % capacity + 1
    if count < capacity then count = count + 1 else dropped = dropped + 1 end
  end

  function probe:reset()
    next_row, count, dropped, self.pulse = 1, 0, 0, 0
    self.enabled = true
  end

  function probe:pause() self.enabled = false end

  -- Snapshot allocates only when the measurement has stopped.
  function probe:snapshot(offset, limit)
    offset = offset or 1
    limit = limit or count
    assert(offset >= 1 and offset % 1 == 0 and limit >= 0 and limit % 1 == 0, "Invalid probe slice")
    local records = {}
    local first = count == capacity and next_row or 1
    for i = offset, math.min(count, offset + limit - 1) do
      local row = rows[(first + i - 2) % capacity + 1]
      records[#records + 1] = {row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8]}
    end
    return {schema_version = 1, capacity = capacity, count = count, dropped = dropped, records = records}
  end
  return probe
end

return timing_probe
