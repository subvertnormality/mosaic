local stock_parameter = {}

function stock_parameter.resolve(assignments, type, read_step_lock, read_assigned, read_fallback)
  for i = 1, 10 do
    local param = assignments[i]
    if param and param.id == type then
      local step_lock = read_step_lock(i)
      if step_lock == param.off_value then
        return nil
      end
      if step_lock then
        return step_lock
      end
      return read_assigned(param.param_id) or nil
    end
  end

  local value, read_default = read_fallback()
  if value and value ~= read_default() then
    return value
  end

  return nil
end

return stock_parameter
