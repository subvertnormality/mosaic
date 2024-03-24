-- Binary class
-- @module params.toggle

local Binary = {}
Binary.__index = Binary

local tBINARY = 9

function Binary.new(id, name, behavior, default, allow_pmap)
  local o = setmetatable({}, Binary)
  o.t = tBINARY
  o.id = id
  o.name = name
  o.default = default or 0
  o.value = o.default
  o.behavior = behavior or 'trigger'
  o.action = function() end
  if allow_pmap == nil then o.allow_pmap = true else o.allow_pmap = allow_pmap end
  return o
end

function Binary:get()
  return self.value
end

function Binary:set(v, silent)
  local silent = silent or false
  v = (v > 0) and 1 or 0
  if self.value ~= v then
    self.value = v
    if silent==false then self:bang() end
  end
end

function Binary:delta(d)
  if self.behavior == 'momentary' then
    self:set(d)
  elseif self.behavior == 'toggle' then
    if d ~= 0 then self:set((self.value == 0) and 1 or 0) end
  elseif d~=0 then 
    self:bang() 
  end  
end

function Binary:set_default()
  self:set(self.default)
end

function Binary:bang()
  self.action(self.value)
end

function Binary:string()
   return self.value
end

function Binary:get_range()
   return {0,1}
end

return Binary
