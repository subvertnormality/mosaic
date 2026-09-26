-- Start-up splash, drawn from Mosaic's logo (images/logo.svg, generated into
-- lib/ui_splash_logo.lua by tools/splash_logo.py): the logo's round dots and
-- pill bars lay themselves down row by row, left to right, in the logo's own
-- shades; they lift away column by column to leave the logo's MOSAIC
-- wordmark, which fades letter by letter into the application screen.
--
-- Purely presentational. Time is a frame count advanced by the caller's clock,
-- so the animation is identical in real and controlled time. It never touches
-- math.random, MIDI, the grid or any musical state. Any player input ends it
-- at once and is handled as usual.

local logo = include("mosaic/lib/ui_splash_logo")

local ui_splash = {}

local FPS = 30
local DOT = 6 -- a dot's diameter in pixels

-- Timeline in seconds.
local LAY_ROW, LAY_COLUMN, POP = 0.07, 0.02, 0.14
local LIFT_START, LIFT_COLUMN, LIFT_ROW, LIFT = 1.15, 0.028, 0.009, 0.12
local FADE_START, FADE = 2.25, 0.6
ui_splash.DURATION = FADE_START + FADE

local state = {active = false, frame = 0}

local function clamp01(x)
  if x < 0 then return 0 elseif x > 1 then return 1 end
  return x
end

-- A little overshoot: the block grows past its size and settles back.
local function pop(t)
  t = clamp01(t)
  local s = 1.7
  t = t - 1
  return t * t * ((s + 1) * t + s) + 1
end

local function lay_time(column, row) return row * LAY_ROW + column * LAY_COLUMN end
local function lift_time(column, row) return LIFT_START + column * LIFT_COLUMN + row * LIFT_ROW end

ui_splash.logo = logo

-- Block `index` of the logo at time t: its left and right dot centres, its
-- centre line, radius and level, or nil when it is not showing.
function ui_splash.block(index, t)
  local b = logo.blocks[index]
  local born = lay_time(b.first, b.row)
  if t < born then return nil end
  local gone = lift_time(b.first, b.row)
  local scale, level
  if t < gone then
    local grow = (t - born) / POP
    scale = pop(grow)
    -- A flash as it lands, cooling to its logo shade.
    level = math.floor(b.level + (15 - b.level) * (1 - clamp01(grow)) + 0.5)
    -- A highlight ripples across the finished logo just before it lifts.
    local wave = (t - 0.95) * 40 - (b.first + b.row)
    if wave > 0 and wave < 2 then level = math.min(15, level + 4) end
  else
    local fall = (t - gone) / LIFT
    if fall >= 1 then return nil end
    scale = 1 - clamp01(fall)
    level = b.level
  end
  local r = DOT / 2 * scale
  if r < 0.25 then return nil end
  local left = logo.grid_x + b.first * logo.cell_w + DOT / 2
  local right = logo.grid_x + b.last * logo.cell_w + DOT / 2
  local middle, half = (left + right) / 2, (right - left) / 2 * math.min(1, scale)
  local y = logo.grid_y + b.row * logo.cell_h + DOT / 2
  return middle - half, middle + half, y, r, math.max(1, math.min(15, level))
end

-- Level of letter `index` (1-based) at time t: hidden under the blocks, full
-- once revealed, then fading one letter after another, left to right.
local LETTER_STAGGER = 0.07
function ui_splash.letter_level(index, t)
  if t < LIFT_START then return 0 end
  local start = FADE_START + (index - 1) * LETTER_STAGGER
  local span = FADE - (#logo.letters - 1) * LETTER_STAGGER
  if t < start then return 15 end
  return math.floor(15 * (1 - clamp01((t - start) / span)) + 0.5)
end

function ui_splash.start()
  state.active, state.frame = true, 0
end

function ui_splash.active()
  return state.active
end

-- Player input ends the splash immediately; the input itself is not consumed.
function ui_splash.skip()
  state.active = false
end

function ui_splash.time()
  return state.frame / FPS
end

-- Called once per frame by the start-up clock. Returns false when finished.
function ui_splash.advance()
  if not state.active then return false end
  state.frame = state.frame + 1
  if ui_splash.time() >= ui_splash.DURATION then state.active = false end
  return state.active
end

ui_splash.FPS = FPS

local function trace(points, dy)
  screen.move(points[1], points[2] - dy)
  for k = 3, #points, 2 do screen.line(points[k], points[k + 1] - dy) end
  screen.close()
end

-- One wordmark letter: its outlines and (opposite-wound) holes form one path,
-- so the counter of the o stays open onto whatever is underneath.
local function draw_letter(glyph, level, dy)
  screen.level(level)
  for _, points in ipairs(glyph.fill) do trace(points, dy) end
  for _, points in ipairs(glyph.holes) do trace(points, dy) end
  screen.fill()
end

local function draw_block(left, right, y, r, level)
  screen.level(level)
  screen.circle(left, y, r)
  screen.fill()
  if right > left then
    screen.circle(right, y, r)
    screen.fill()
    screen.rect(left, y - r, right - left, 2 * r)
    screen.fill()
  end
end

-- The screen area a grid cell hides the wordmark under until it lifts; cells
-- tile the whole screen, gaps between blocks included.
local function cell_box(column, row)
  local x0 = column == 0 and 0 or logo.grid_x + column * logo.cell_w - 1
  local x1 = column == logo.columns - 1 and 128 or logo.grid_x + (column + 1) * logo.cell_w - 1
  local y0 = row == 0 and 0 or logo.grid_y + row * logo.cell_h
  local y1 = row == logo.rows - 1 and 64 or logo.grid_y + (row + 1) * logo.cell_h
  return x0, y0, x1 - x0, y1 - y0
end

-- Draws the splash at time t. While the word fades, draw_ui paints the
-- application screen underneath so the word dissolves into it.
function ui_splash.draw(t, draw_ui)
  t = t or ui_splash.time()
  if t >= FADE_START and draw_ui then draw_ui() end
  if t >= LIFT_START then
    for index, glyph in ipairs(logo.letters) do
      local level = ui_splash.letter_level(index, t)
      -- Each letter rises a couple of pixels as it fades, a small exhale.
      if level > 0 then draw_letter(glyph, level, math.floor(3 * (1 - level / 15) + 0.5)) end
    end
  end
  screen.level(0)
  for row = 0, logo.rows - 1 do
    for column = 0, logo.columns - 1 do
      if t < lift_time(column, row) then
        screen.rect(cell_box(column, row))
        screen.fill()
      end
    end
  end
  for index = 1, #logo.blocks do
    local left, right, y, r, level = ui_splash.block(index, t)
    if left then draw_block(left, right, y, r, level) end
  end
end

return ui_splash
