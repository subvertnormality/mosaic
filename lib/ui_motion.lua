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

-- Marquee (lib/ui_render.lua fit): cut text scrolls on a 10 Hz tick that runs
-- only while something is cut, and asks for a frame only when a text moves, so
-- a resting screen stays still. The phase restarts with the screen or selection.
local MARQUEE_TICK = 0.1
local marquee = {phase = 0, key = nil, cut = false, next_move = nil, clock = nil, generation = 0}

local function marquee_clock()
  if marquee.clock or not (clock and clock.run and clock.sleep) then return end
  marquee.clock = clock.run(function()
    while marquee.cut and marquee.next_move do
      local generation, ticks = marquee.generation, marquee.next_move
      clock.sleep(ticks * MARQUEE_TICK)
      if not marquee.cut then break end
      if generation == marquee.generation then
        marquee.phase = marquee.phase + ticks
        marquee.next_move = nil
        if fn and fn.dirty_screen then fn.dirty_screen(true) end
      end
      -- The frame just asked for reports when the next move is due.
      while marquee.cut and not marquee.next_move do clock.sleep(MARQUEE_TICK) end
    end
    marquee.clock = nil
  end)
end

function ui_motion.marquee_phase() return marquee.phase end

-- Characters keeping time (the Doctor, garden, choir, metronome) redraw on their
-- own tick, at most ART_FPS a second, rather than every frame: a full-screen
-- redraw is costly on the norns and must not crowd the sequencer while it plays.
local ART_FPS = 12
local art = {active = false, clock = nil}

local function art_clock()
  if art.clock or not (clock and clock.run and clock.sleep) then return end
  art.clock = clock.run(function()
    while art.active do
      clock.sleep(1 / ART_FPS)
      if art.active and fn and fn.dirty_screen then fn.dirty_screen(true) end
    end
    art.clock = nil
  end)
end

function ui_motion.art_fps() return ART_FPS end

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
    marquee.cut, marquee.next_move = false, nil
    art.active = false
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
  -- Marquee: the phase restarts with the screen or selection; the renderer's
  -- report keeps the tick running while text is cut.
  local marquee_key = tostring(vm.screen) .. ":" .. tostring(vm.selected)
  if marquee.key ~= marquee_key then
    marquee.key, marquee.phase, marquee.generation = marquee_key, 0, marquee.generation + 1
  end
  vm.marquee = marquee.phase
  local ok, report = render(vm)
  marquee.cut = type(report) == "table" and report.cut == true
  marquee.next_move = marquee.cut and report.next_move or nil
  if marquee.cut then marquee_clock() end
  -- A character keeping time is redrawn by the art tick while it moves.
  art.active = vm.motion ~= nil
  if art.active then art_clock() end
  local moving = ui_motion.busy()
  if glide.frames > 0 then draw_glide(); glide.frames = glide.frames - 1 end
  draw_mark(pop > 0)
  if pop > 0 then pop = pop - 1 end
  if blink > 0 then blink = blink - 1 end
  -- Any frame with motion asks for another, so the last one is always clean.
  if moving then fn.dirty_screen(true) end
  return ok, report
end

return ui_motion
