local save_confirm = {}

local fn = include("mosaic/lib/functions")
local save_func = nil
local cancel_func = nil
local default_confirm_message = "Press K3 to confirm"
local default_ok_message = "OK"
local default_cancel_message = "Action cancelled"
local confirm_message = default_confirm_message
local ok_message = default_ok_message
local cancel_message = default_cancel_message

function save_confirm.set_save(func)
  save_func = func
  tooltip:show(confirm_message)
  confirm_message = default_confirm_message
end

function save_confirm.set_cancel(func)
  cancel_func = func
end

function save_confirm.confirm()
  if save_func ~= nil then
    save_func()
    tooltip:show(ok_message)
  end
  save_func = nil
  cancel_func = nil
  ok_message = default_ok_message
end

function save_confirm.cancel()
  if cancel_func ~= nil then
    cancel_func()
    tooltip:show(cancel_message)
  end
  save_func = nil
  cancel_func = nil
  cancel_message = default_cancel_message
end

function save_confirm.set_confirm_message(message)
  confirm_message = message
end

function save_confirm.set_ok_message(message)
  ok_message = message
end

function save_confirm.set_cancel_message(message)
  cancel_message = message
end


return save_confirm
