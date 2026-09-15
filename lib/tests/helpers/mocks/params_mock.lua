params = {}
param_store = {}

function params.reset()
  param_store = {}
end

function params:add(id, param)
  param_store[id] = param
end

function params:set(p, val) 
  local param = param_store[p]
  if param == nil then
    param = {}
  end
  param.val = val
  param_store[p] = param
end

function params:get(p) 
  local param = param_store[p]
  if param == nil then
    param = {}
  end
  
  return param.val
end

function params:lookup_param(id)
  return param_store[id]
end
-- Mirror ParamSet's id index over the store so indexed reads see the same values.
params.lookup = setmetatable({}, {__index = function(_, id)
  if param_store[id] ~= nil then return id end
end})
params.params = setmetatable({}, {__index = function(_, id)
  local param = param_store[id]
  if param == nil then return nil end
  return {get = function() return param.val end, default = param.default}
end})
