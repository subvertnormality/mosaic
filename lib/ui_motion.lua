-- Presentation motion for the live screen: small, playful and never in the way.
--
-- * A screen change is instant: no transition over the new screen.
-- * On overview grids the selection's shadow glides from the cell it left to
--   the new one along the straight line between them (diagonally when it moves
--   between rows).
-- * A value change, focus move or apply runs a light around Mosaic's little
--   four-tile mark in the title bar.
-- * Characters blink now and then.
--
-- Motion is decorative only (spec layout_contract.motion). It never delays or
-- consumes input, never hides a value, uses no
-- math.random and drives no MIDI or grid LED. Animation advances one step per
-- drawn frame, so it is identical in real and controlled time. The native
-- MOSAIC > UI motion parameter turns it off; captures then use the settled frame.

local ui_motion = {}

local POP_FRAMES, BLINK_FRAMES = 6, 3
local BLINK_EVERY = 4.5 -- seconds between blinks while a character is shown

local pop, pop_strength = 0, 1
local GLIDE_FRAMES = 7
local glide = {frames = 0, from = nil, to = nil, screen = nil, selected = nil}
local dial = {key = nil, shown = nil, target = nil}
-- A changed focused value rolls up into place over a few frames.
local ROLL_FRAMES = 3
local roll = {key = nil, value = nil, frames = 0}
local last_blink, blink = nil, 0

local function now()
  if util and util.time then return util.time() end
  return os.clock()
end

function ui_motion.enabled()
  if params and params.lookup and params.lookup["ui_motion"] then
    return params:get("ui_motion") ~= 1
  end
  return true
end

-- Screens change without a transition (owner decision 2026-09-25).
function ui_motion.screen_changed() end

-- kind: "value", "focus", "apply" or "status".
function ui_motion.nudge(kind)
  if not ui_motion.enabled() then return end
  pop = POP_FRAMES
  pop_strength = (kind == "apply") and 2 or 1
end

function ui_motion.pose()
  return blink > 0 and 1 or 0
end

function ui_motion.busy()
  return pop > 0 or blink > 0 or glide.frames > 0
    or (dial.target ~= nil and dial.shown ~= dial.target) or roll.frames > 0
end

-- Mosaic's mark: four small tiles at the right of the title row. They rest
-- dim; a change lights them one after another, clockwise, and an apply adds a
-- second, brighter lap.
local MARK = {{121, 1}, {124, 1}, {124, 4}, {121, 4}}
local MARK_REST = {3, 6, 3, 6}

local function draw_mark(active)
  local t = active and (1 - pop / POP_FRAMES) or nil
  for index, tile in ipairs(MARK) do
    local level = MARK_REST[index]
    if t then
      local lit = math.floor(t * #MARK * pop_strength) % #MARK + 1
      if lit == index then level = 15 elseif (lit % #MARK) + 1 == index then level = 9 end
    end
    screen.level(level)
    screen.rect(tile[1], tile[2], 2, 2)
    screen.fill()
  end
end

-- Overview grids: the selection outline glides from the cell it left to the
-- new one. The renderer always draws the real outline; this is a faint ghost.
local function cell_rect(layout, selected)
  local columns, width = 4, 32
  if layout == "overview_params" then columns, width = 5, 25 end
  local x = ((selected - 1) % columns) * width
  local y = 9 + math.floor((selected - 1) / columns) * 18
  return x, y, width - 2, 17
end

local function track_glide(vm)
  local overview = vm.layout == "overview_masks" or vm.layout == "overview_params"
  if not overview then glide.screen, glide.selected, glide.frames = nil, nil, 0; return end
  if glide.screen == vm.screen and glide.selected ~= vm.selected and glide.selected then
    glide.from = {cell_rect(vm.layout, glide.selected)}
    glide.to = {cell_rect(vm.layout, vm.selected)}
    glide.frames = GLIDE_FRAMES
  end
  glide.screen, glide.selected = vm.screen, vm.selected
end

-- The shadow is already on its way in the first frame and eases in and out,
-- moving x and y together so a move between rows travels diagonally.
local function glide_position(frames_left)
  local t = 1 - (frames_left - 1) / GLIDE_FRAMES
  local e = t * t * (3 - 2 * t)
  local a, b = glide.from, glide.to
  return a[1] + (b[1] - a[1]) * e, a[2] + (b[2] - a[2]) * e
end

local function draw_glide()
  local a = glide.from
  local x, y = glide_position(glide.frames)
  screen.level(5)
  screen.rect(x, y, a[3], a[4])
  screen.stroke()
end

-- Draws one frame: the renderer, then any overlay, and keeps frames coming
-- while something moves.
function ui_motion.draw(vm, render)
  if not ui_motion.enabled() then
    pop, blink, glide.frames = 0, 0, 0
    dial.shown, dial.target, roll.frames = nil, nil, 0
    vm.pose, vm.motion = 0, nil
    local ok, report = render(vm)
    draw_mark(false)
    return ok, report
  end
  -- The once-a-second screen refresh is enough to notice a blink is due.
  if vm.art then
    local t = now()
    last_blink = last_blink or t
    if blink == 0 and t - last_blink >= BLINK_EVERY then last_blink, blink = t, BLINK_FRAMES end
  else
    blink, last_blink = 0, nil
  end
  vm.pose = ui_motion.pose()
  track_glide(vm)
  if vm.layout == "focused" and vm.fields and vm.fields[vm.selected] then
    local field = vm.fields[vm.selected]
    local key = vm.screen .. ":" .. tostring(field.id)
    if roll.key == key and roll.value ~= field.value then roll.frames = ROLL_FRAMES end
    roll.key, roll.value = key, field.value
    if roll.frames > 0 then vm.value_dy = roll.frames; roll.frames = roll.frames - 1 end
  else
    -- Left mid-roll: nothing is rolling on this screen, so stop asking for frames.
    roll.key, roll.value, roll.frames = nil, nil, 0
  end
  -- The dial needle sweeps to a new value instead of jumping.
  if vm.dial then
    if dial.key ~= vm.dial_key or dial.shown == nil then dial.key, dial.shown = vm.dial_key, vm.dial end
    dial.target = vm.dial
    dial.shown = dial.shown + (dial.target - dial.shown) * 0.45
    if math.abs(dial.target - dial.shown) < 0.004 then dial.shown = dial.target end
    vm.dial = dial.shown
  else
    -- Left mid-sweep: a dial no longer shown must not keep the screen redrawing.
    dial.key, dial.shown, dial.target = nil, nil, nil
  end
  local ok, report = render(vm)
  -- A character keeping time asks for frames for as long as it moves.
  local moving = ui_motion.busy() or vm.motion ~= nil
  if glide.frames > 0 then draw_glide(); glide.frames = glide.frames - 1 end
  draw_mark(pop > 0)
  if pop > 0 then pop = pop - 1 end
  if blink > 0 then blink = blink - 1 end
  -- Any frame with motion asks for another, so the last one is always clean.
  if moving then fn.dirty_screen(true) end
  return ok, report
end

return ui_motion
