-- Presentation motion for the live screen: small, playful and never in the way.
--
-- * A screen change reveals the new body tile by tile, left to right (the
--   splash's mosaic, in miniature).
-- * A value change, focus move or apply runs a light around Mosaic's little
--   four-tile mark in the title bar.
-- * Characters blink now and then.
--
-- Motion is decorative only (spec layout_contract.motion). It never delays or
-- consumes input, hides a value for at most WIPE_FRAMES frames, uses no
-- math.random and drives no MIDI or grid LED. Animation advances one step per
-- drawn frame, so it is identical in real and controlled time. The native
-- MOSAIC > UI motion parameter turns it off; captures then use the settled frame.

local ui_motion = {}

local WIPE_FRAMES, POP_FRAMES, BLINK_FRAMES = 6, 6, 3
local BLINK_EVERY = 4.5 -- seconds between blinks while a character is shown

local wipe, pop, pop_strength = 0, 0, 1
local GLIDE_FRAMES = 4
local glide = {frames = 0, from = nil, to = nil, screen = nil, selected = nil}
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

function ui_motion.screen_changed()
  if ui_motion.enabled() then wipe = WIPE_FRAMES end
end

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
  return wipe > 0 or pop > 0 or blink > 0 or glide.frames > 0
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

local function draw_glide()
  local t = 1 - glide.frames / GLIDE_FRAMES
  local e = 1 - (1 - t) * (1 - t)
  local a, b = glide.from, glide.to
  screen.level(5)
  screen.rect(a[1] + (b[1] - a[1]) * e, a[2] + (b[2] - a[2]) * e, a[3], a[4])
  screen.stroke()
end

local function draw_wipe()
  -- Body tiles (8x8) still covering the new screen: columns uncover left to right.
  local uncovered = math.floor(16 * (1 - wipe / WIPE_FRAMES) + 0.5)
  for column = uncovered, 15 do
    for row = 1, 6 do
      local shade = ((column * 7 + row * 3) % 4) + 1
      screen.level(column == uncovered and shade + 3 or 0)
      screen.rect(column * 8, row * 8 + 1, column == uncovered and 7 or 8, column == uncovered and 7 or 8)
      screen.fill()
    end
  end
end

-- Draws one frame: the renderer, then any overlay, and keeps frames coming
-- while something moves.
function ui_motion.draw(vm, render)
  if not ui_motion.enabled() then
    wipe, pop, blink, glide.frames = 0, 0, 0, 0
    vm.pose = 0
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
  local ok, report = render(vm)
  local moving = ui_motion.busy()
  if glide.frames > 0 then draw_glide(); glide.frames = glide.frames - 1 end
  if wipe > 0 then draw_wipe(); wipe = wipe - 1 end
  draw_mark(pop > 0)
  if pop > 0 then pop = pop - 1 end
  if blink > 0 then blink = blink - 1 end
  -- Any frame with motion asks for another, so the last one is always clean.
  if moving then fn.dirty_screen(true) end
  return ok, report
end

return ui_motion
