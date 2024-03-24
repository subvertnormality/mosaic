-- Taper class
-- non-linear parameter using @catfact's taper function
-- @module params.taper

local util = require 'util'

local Taper = {}
Taper.__index = Taper

local tTAPER = 5

local function map(x, from_min, from_max, to_min, to_max)
  return (x - from_min) * (to_max - to_min) / (from_max - from_min) + to_min
end

function Taper.new(id, name, min, max, default, k, units, allow_pmap)
  local p = setmetatable({}, Taper)
  p.t = tTAPER
  p.id = id
  p.name = name
  p.min = min or 0
  p.max = max or 1
  p.k = k or 0
  p.action = function() end
  if allow_pmap == nil then p.allow_pmap = true else p.allow_pmap = allow_pmap end
  p.default = default or min
  p.units = units or ""
  p:set(p.default)
  return p
end

function Taper:map_value(v)
  local result

  if self.k == 0 then
    result = v
  else
    result = (math.exp(v * self.k) - 1) / (math.pow(math.exp(1), self.k) - 1)
  end

  return map(result, 0, 1, self.min, self.max)
end

function Taper:get()
  return self:map_value(self.value)
end

function Taper:get_raw()
  return self.value
end

function Taper:unmap_value(v)
  local raw
  raw = map(v, self.min, self.max, 0, 1)

  if self.k ~= 0 then
    raw = math.log(raw * (math.pow(math.exp(1), self.k) - 1) + 1) / self.k
  end

  return raw
end

function Taper:set(v, silent)
  self:set_raw(self:unmap_value(v), silent)
end

function Taper:set_raw(v, silent)
  local silent = silent or false
  if self.value ~= v then
    self.value = util.clamp(v, 0, 1)
    if silent==false then self:bang() end
  end
end

function Taper:get_delta()
  local range = math.abs(self.max - self.min)
  return 1 / math.min(math.max(range, 200), 800)
end

function Taper:delta(d)
  self:set_raw(self.value + d * self:get_delta())
end

function Taper:set_default()
  self:set(self.default)
end

function Taper:bang()
  if self.value ~= nil then
    self.action(self:get())
  end
end

function Taper:string()
  local format

  local v = self:get()
  local absv = math.abs(v)

  if absv >= 100 then
    format = "%.0f "..string.gsub(self.units, "%%", "%%%%")
  elseif absv >= 10 then
    format = "%.1f "..string.gsub(self.units, "%%", "%%%%")
  elseif absv >= 1 then
    format = "%.2f "..string.gsub(self.units, "%%", "%%%%")
  elseif absv >= 0.001 then
    format = "%.3f "..string.gsub(self.units, "%%", "%%%%")
  else
    format = "%.0f "..string.gsub(self.units, "%%", "%%%%")
  end

  return string.format(format, v)
end

function Taper:get_range()
  local r = { self.min, self.max }
  return r
end

return Taper
