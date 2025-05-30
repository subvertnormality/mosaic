local norns_param_state_handler = {}

local original_param_state = {
  {{}, {}, {}, {}, {}, {}, {}, {}, {}, {}},
  {{}, {}, {}, {}, {}, {}, {}, {}, {}, {}}, 
  {{}, {}, {}, {}, {}, {}, {}, {}, {}, {}}, 
  {{}, {}, {}, {}, {}, {}, {}, {}, {}, {}}, 
  {{}, {}, {}, {}, {}, {}, {}, {}, {}, {}}, 
  {{}, {}, {}, {}, {}, {}, {}, {}, {}, {}}, 
  {{}, {}, {}, {}, {}, {}, {}, {}, {}, {}}, 
  {{}, {}, {}, {}, {}, {}, {}, {}, {}, {}}, 
  {{}, {}, {}, {}, {}, {}, {}, {}, {}, {}}, 
  {{}, {}, {}, {}, {}, {}, {}, {}, {}, {}}, 
  {{}, {}, {}, {}, {}, {}, {}, {}, {}, {}}, 
  {{}, {}, {}, {}, {}, {}, {}, {}, {}, {}}, 
  {{}, {}, {}, {}, {}, {}, {}, {}, {}, {}}, 
  {{}, {}, {}, {}, {}, {}, {}, {}, {}, {}}, 
  {{}, {}, {}, {}, {}, {}, {}, {}, {}, {}}, 
  {{}, {}, {}, {}, {}, {}, {}, {}, {}, {}}
} 

function norns_param_state_handler.flush_norns_original_param_trig_lock_store()
  for c = 1, 16 do
    for i = 1, 10 do
      if original_param_state[c] and original_param_state[c][i] and original_param_state[c][i].param_id then
        params:set(original_param_state[c][i].param_id, original_param_state[c][i].value)
        original_param_state[c][i] = {}
      end
    end
  end
end

function norns_param_state_handler.set_original_param_state(c, i, value, param_id)
  if not original_param_state[c] then
    original_param_state[c] = {}
  end
  original_param_state[c][i] = {
    value = value,
    param_id = param_id
  }
end 

function norns_param_state_handler.get_original_param_state(c, i)
  if not original_param_state[c] or not original_param_state[c][i] then
    return nil
  end
  return original_param_state[c][i]
end

function norns_param_state_handler.clear_original_param_state(c, i)
  if original_param_state[c] then
    original_param_state[c][i] = {}
  end
end

return norns_param_state_handler