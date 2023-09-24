local save_confirm = {}

local fn = include("mosaic/lib/functions")
local save_func = nil
local cancel_func = nil

function save_confirm.set_save(func)
  save_func = func
  tooltip:show("Press K3 to confirm")
end

function save_confirm.set_cancel(func)
  cancel_func = func
end

function save_confirm.confirm()
  if save_func ~= nil then
    save_func()
    tooltip:show("OK")
  end
  save_func = nil
  cancel_func = nil
end

function save_confirm.cancel()
  if cancel_func ~= nil then
    cancel_func()
    tooltip:show("Action cancelled")
  end
  save_func = nil
  cancel_func = nil
end

return save_confirm
