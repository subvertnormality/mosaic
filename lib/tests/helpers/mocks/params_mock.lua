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