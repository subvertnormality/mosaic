-- Presentation motion for the live screen: small, playful and never in the way.
--
-- * A screen change reveals the new body tile by tile, left to right (the
--   splash's mosaic, in miniature).
-- * A value change, focus move or apply pops the little tile in the title bar.
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
  return wipe > 0 or pop > 0 or blink > 0
end

local function draw_pop()
  -- A tile that swells past its size and settles, top right of the title bar.
  local t = 1 - pop / POP_FRAMES
  local size = t < 0.5 and (2 + 8 * t) or (6 - 4 * (t - 0.5))
  size = math.floor(size * (pop_strength == 2 and 1.2 or 1) + 0.5)
  local cx, cy = 124, 3
  screen.level(math.max(3, math.floor(15 * (1 - t * 0.6))))
  screen.rect(cx - size / 2, cy - size / 2, size, size)
  screen.fill()
  if pop_strength == 2 and t > 0.3 then
    -- Apply scatters two sparks.
    screen.level(math.floor(10 * (1 - t)))
    screen.rect(cx - 7, cy + 1, 1, 1); screen.fill()
    screen.rect(cx + 4, cy + 3, 1, 1); screen.fill()
  end
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
    wipe, pop, blink = 0, 0, 0
    vm.pose = 0
    return render(vm)
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
  local ok, report = render(vm)
  local moving = ui_motion.busy()
  if wipe > 0 then draw_wipe(); wipe = wipe - 1 end
  if pop > 0 then draw_pop(); pop = pop - 1 end
  if blink > 0 then blink = blink - 1 end
  -- Any frame with motion asks for another, so the last one is always clean.
  if moving then fn.dirty_screen(true) end
  return ok, report
end

return ui_motion
