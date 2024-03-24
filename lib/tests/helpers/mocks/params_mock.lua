params = {}
param_store = {}

function params.reset()
    param_store = {}
end

function params:set(param, val) 
    param_store[param] = val
end

function params:get(param) 
    return param_store[param]
end

params.lookup_param = function () end