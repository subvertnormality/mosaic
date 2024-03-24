-- Option class
-- @module params.option

local tab = require 'tabutil'

local Option = {}
Option.__index = Option

local tOPTION = 2

function Option.new(id, name, options, default, allow_pmap)
  local o = setmetatable({}, Option)
  o.t = tOPTION
  o.id = id
  o.name = name
  o.options = {}
  for k,v in pairs(options) do
    o.options[k] = v
  end
  o.count = tab.count(o.options)
  o.default = default or 1
  o.selected = o.default
  o.action = function() end
  if allow_pmap == nil then o.allow_pmap = true else o.allow_pmap = allow_pmap end
  return o
end

function Option:get()
  return self.selected
end

function Option:set(v, silent)
  local silent = silent or false
  local c = util.clamp(math.floor(v),1,self.count)
  if self.selected ~= c then
    self.selected = c
    if silent==false then self:bang() end
  end
  if norns.pmap.data[self.id] ~= nil then
    local midi_prm = norns.pmap.data[self.id]
    midi_prm.value = util.round(util.linlin(midi_prm.out_lo, midi_prm.out_hi, midi_prm.in_lo, midi_prm.in_hi, self.selected))
    if midi_prm.echo then
      local port = norns.pmap.data[self.id].dev
      midi.vports[port]:cc(midi_prm.cc, midi_prm.value, midi_prm.ch)
    end
  end
end

function Option:delta(d)
  if d<0 then d = math.floor(d)
  else d = math.ceil(d) end
  self:set(self:get() + d)
end

function Option:set_default()
  self:set(self.default)
end

function Option:bang()
  self.action(self.selected)
end

function Option:string()
  return self.options[self.selected]
end

function Option:get_range()
  local r = { 1, self.count }
  return r
end


return Option
