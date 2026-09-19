-- Native controls remain numeric, while off is a distinct selectable value.
local domain = {}
-- A separate Off position is one selectable interval, including sparse ranges.
function domain.unit_quantum(minimum, maximum, off)
  off = off == nil and -1 or off
  local intervals = maximum - minimum
  if off < minimum or off > maximum then intervals = intervals + 1 end
  return 1 / math.max(1, intervals)
end
function domain.new(minimum, maximum, off, units)
  off = off == nil and -1 or off
  units = units or 1
  assert(type(minimum)=="number" and type(maximum)=="number" and minimum<=maximum,
    "Invalid MIDI parameter range")
  assert(minimum%1==0 and maximum%1==0 and type(off)=="number" and off%1==0,
    "MIDI parameter bounds and off value must be integers")
  if off>=minimum and off<=maximum then
    return controlspec.new(minimum,maximum,"lin",1,off,"",units/math.max(1,maximum-minimum))
  end
  local intervals = maximum-minimum+1 -- active values plus one off position
  local first_off = off<minimum
  local spec = controlspec.new(math.min(minimum,off),math.max(maximum,off),"lin",1,off,"",units/intervals)
  spec.warp = {
    map=function(_,raw)
      local index=util.round(raw*intervals,1)
      if first_off then return index==0 and off or minimum+index-1 end
      return index==intervals and off or minimum+index
    end,
    unmap=function(_,value)
      if value==off then return first_off and 0 or 1 end
      local index=util.clamp(value,minimum,maximum)-minimum+(first_off and 1 or 0)
      return index/intervals
    end
  }
  local function preserve_domain(s)
    s.constrain=function(self,value)return self:map(self:unmap(value)) end
    s.copy=function(self)return preserve_domain(controlspec.copy(self)) end
    return s
  end
  return preserve_domain(spec)
end
return domain
