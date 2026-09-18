-- Pure base-onset arithmetic. The timing view is read-only; no clock methods,
-- live carry, actions or transport state are advanced by a projection.
local projection = {}

local drunk_map = {
  {2/9, 3/9, 2/9, 2/9, 2/9, 3/9, 2/9, 2/9},
  {2/7, 2/7, 2/7, 1/7, 2/7, 2/7, 2/7, 1/7},
  {1/5, 2/5, 1/5, 1/5, 1/5, 2/5, 1/5, 1/5},
  {1/6, 3/6, 1/6, 1/6, 1/6, 3/6, 1/6, 1/6},
  {1/8, 4/8, 2/8, 1/8, 1/8, 4/8, 2/8, 1/8},
  {1/9, 5/9, 2/9, 1/9, 1/9, 5/9, 2/9, 1/9},
}

local smooth_map = {
  {5/18, 5/18, 4/18, 4/18, 5/18, 5/18, 4/18, 4/18},
  {4/14, 4/14, 3/14, 3/14, 4/14, 4/14, 3/14, 3/14},
  {3/10, 3/10, 2/10, 2/10, 3/10, 3/10, 2/10, 2/10},
  {2/6, 2/6, 1/6, 1/6, 2/6, 2/6, 1/6, 1/6},
  {5/16, 5/16, 3/16, 3/16, 5/16, 5/16, 3/16, 3/16},
  {6/18, 7/18, 3/18, 2/18, 6/18, 7/18, 3/18, 2/18},
}

local heavy_map = {
  {4/9, 2/9, 2/9, 1/9, 4/9, 2/9, 2/9, 1/9},
  {3/7, 1/7, 2/7, 1/7, 3/7, 1/7, 2/7, 1/7},
  {2/5, 1/5, 1/5, 1/5, 2/5, 1/5, 1/5, 1/5},
  {3/6, 1/6, 1/6, 1/6, 3/6, 1/6, 1/6, 1/6},
  {4/8, 1/8, 2/8, 1/8, 4/8, 1/8, 2/8, 1/8},
  {5/9, 1/9, 2/9, 1/9, 5/9, 1/9, 2/9, 1/9},
}

local clave_map = {
  {2/9, 3/9, 2/9, 2/9, 3/9, 2/9, 2/9, 2/9},
  {2/7, 2/7, 1/7, 2/7, 2/7, 1/7, 2/7, 2/7},
  {1/5, 2/5, 1/5, 1/5, 2/5, 1/5, 1/5, 1/5},
  {3/12, 4/12, 2/12, 3/12, 4/12, 2/12, 3/12, 3/12},
  {3/16, 6/16, 3/16, 4/16, 5/16, 3/16, 4/16, 4/16},
  {4/18, 7/18, 3/18, 4/18, 7/18, 2/18, 5/18, 4/18},
}

local shuffle_feels = {
  drunk_map,
  smooth_map,
  heavy_map,
  clave_map
}


function projection.calculate(view, pattern_length, step)
  local ppc = view.ppqn * 4
  local step_mod = ((step - 1) % pattern_length) + 1
  if view.swing_or_shuffle == 2 and view.shuffle_feel > 0 and view.shuffle_basis > 0 then
    local multiplier = shuffle_feels[view.shuffle_feel][view.shuffle_basis][(step_mod % 8) + 1]
    return ((view.division * 4) * ppc) * (0.25 + view.shuffle_amount * (multiplier - 0.25))
  elseif pattern_length % 2 == 1 and step_mod % pattern_length == 0 then
    return view.division * ppc
  end
  return (view.division * ppc) * (step_mod % 2 == 1 and view.even_swing or view.odd_swing)
end

function projection.interval(view, pattern_length, step, carry)
  local calculated = math.max(1, projection.calculate(view, pattern_length, step))
  local rounded = math.floor(calculated + carry - 0.01)
  return rounded, calculated + carry - rounded
end

function projection.project_pulses(view, pattern_length, current_ppqn, carry, step, distance)
  local elapsed = current_ppqn
  for interval = 2, distance do
    step = step + 1
    if step > pattern_length then step = 1 end
    current_ppqn, carry = projection.interval(view, pattern_length, step, carry)
    elapsed = elapsed + current_ppqn
  end
  return elapsed
end

function projection.project_occurrence(view, pattern_length, transport, occurrence)
  local remaining = occurrence - (view.onset_count or 0)
  local offset = view.last_processed_transport == transport and 1 or 0
  local current, carry, step, phase = view.current_ppqn, view.ppqn_error, view.step, view.phase
  if not view.shuffle_updated then
    local original = current
    current, carry = projection.interval(view, pattern_length, step, carry)
    if current ~= original then
      phase = math.floor(((phase - 1) / original) * current + 1)
      phase = math.max(1, math.min(current, phase))
    end
  end
  if phase >= 1 and phase < 2 and (offset == 1 or view.last_onset_transport ~= transport) then
    remaining = remaining - 1
    if remaining == 0 then return offset end
  end
  local elapsed = current - (phase - 1)
  for interval = 2, remaining do
    step = step + 1
    if step > pattern_length then step = 1 end
    current, carry = projection.interval(view, pattern_length, step, carry)
    elapsed = elapsed + current
  end
  return elapsed + offset
end

return projection
