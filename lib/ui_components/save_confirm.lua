local save_confirm = {}

local fn = include("mosaic/lib/functions")
local save_funcs = {}
local cancel_funcs = {}
local default_confirm_message = "Press K3 to confirm"
local default_ok_message = "OK"
local default_cancel_message = "Action cancelled"
local confirm_message = default_confirm_message
local ok_message = default_ok_message
local cancel_message = default_cancel_message

function save_confirm.set_save(func)
  table.insert(save_funcs, func)
  tooltip:show(confirm_message)
  confirm_message = default_confirm_message
end

function save_confirm.set_cancel(func)
  table.insert(cancel_funcs, func)
end

function save_confirm.confirm()
  if #save_funcs > 0 then
    for _, func in ipairs(save_funcs) do
      func()
    end

    tooltip:show(ok_message)
  end
  save_funcs = {}
  cancel_funcs = {}
  ok_message = default_ok_message
end

function save_confirm.cancel()
  if #cancel_funcs > 0 then
    for _, func in ipairs(cancel_funcs) do
      func()
    end
    tooltip:show(cancel_message)
  end
  save_funcs = {}
  cancel_funcs = {}
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
