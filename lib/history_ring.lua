local history_ring = {}

function history_ring.new(max_size)
  return {
    buffer = {},
    start = 1,
    size = 0,
    max_size = max_size,
    total_size = 0,

    get_size = function(self)
      return self.size
    end,

    push = function(self, event)
      local index
      if self.size < self.max_size then
        index = ((self.start + self.size - 1) % self.max_size) + 1
        self.size = self.size + 1
      else
        index = self.start
        self.start = (self.start % self.max_size) + 1
      end
      self.buffer[index] = event
      self.total_size = self.size
      return self.size
    end,

    get = function(self, position)
      if not position or position < 1 or position > self.size then return nil end
      local actual_pos = ((self.start + position - 2) % self.max_size) + 1
      if actual_pos <= 0 then actual_pos = actual_pos + self.max_size end
      return self.buffer[actual_pos]
    end,

    truncate = function(self, position)
      if position < self.size then
        self.size = position
        self.total_size = position
      end
    end
  }
end

function history_ring.serialize(ring)
  return {
    buffer = ring.buffer,
    start = ring.start,
    size = ring.size,
    max_size = ring.max_size,
    total_size = ring.total_size
  }
end

function history_ring.deserialize(data, default_max_size)
  if not data then return history_ring.new(default_max_size) end
  local ring = history_ring.new(data.max_size)
  ring.buffer = data.buffer or {}
  ring.start = data.start or 1
  ring.size = data.size or 0
  ring.total_size = data.size or 0
  return ring
end

return history_ring
