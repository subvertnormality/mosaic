-- Start-up splash: a mosaic of tiles lays itself down row by row, left to
-- right, then lifts away column by column to leave the word "Mosaic", which
-- fades out into the application screen.
--
-- Purely presentational. Time is a frame count advanced by the caller's clock,
-- so the animation is identical in real and controlled time, and tile shades
-- come from a fixed hash: it never touches math.random, MIDI, the grid or any
-- musical state. Any player input ends it at once and is handled as usual.

local ui_splash = {}

local COLUMNS, ROWS, CELL, TILE = 16, 8, 8, 7
local FPS = 30

-- Timeline in seconds.
local LAY_ROW, LAY_COLUMN, POP = 0.06, 0.018, 0.14
local LIFT_START, LIFT_COLUMN, LIFT_ROW, LIFT = 1.0, 0.028, 0.009, 0.12
local FADE_START, FADE = 1.95, 0.55
ui_splash.DURATION = FADE_START + FADE

local WORD = "Mosaic"
local WORD_FACE, WORD_SIZE = 5, 24

local state = {active = false, frame = 0}

-- Deterministic 0..1 shade per tile; stands in for randomness without using it.
local function shade(column, row)
  local h = (column * 73856093 ~ row * 19349663) % 1000
  return h / 999
end

local function clamp01(x)
  if x < 0 then return 0 elseif x > 1 then return 1 end
  return x
end

-- A little overshoot: the tile grows past its size and settles back.
local function pop(t)
  t = clamp01(t)
  local s = 1.7
  t = t - 1
  return t * t * ((s + 1) * t + s) + 1
end

local function lay_time(column, row) return row * LAY_ROW + column * LAY_COLUMN end
local function lift_time(column, row) return LIFT_START + column * LIFT_COLUMN + row * LIFT_ROW end

-- Tile geometry and level at time t, or nil when the tile is not showing.
function ui_splash.tile(column, row, t)
  local born = lay_time(column, row)
  if t < born then return nil end
  local gone = lift_time(column, row)
  local rest = 3 + math.floor(shade(column, row) * 9 + 0.5)
  local size, level
  if t < gone then
    local grow = (t - born) / POP
    size = TILE * pop(grow)
    -- A flash as it lands, cooling to its resting shade.
    level = math.floor(rest + (15 - rest) * (1 - clamp01(grow)) + 0.5)
    -- A highlight ripples across the finished mosaic just before it lifts.
    local wave = (t - 0.78) * 40 - (column + row)
    if wave > 0 and wave < 2 then level = math.min(15, level + 4) end
  else
    local fall = (t - gone) / LIFT
    if fall >= 1 then return nil end
    size = TILE * (1 - clamp01(fall))
    level = rest
  end
  if size < 0.5 then return nil end
  local x = (column * CELL) + (TILE - size) / 2
  local y = (row * CELL) + (TILE - size) / 2
  return x, y, size, math.max(1, math.min(15, level))
end

-- Level of letter `index` (1-based) at time t: hidden under the tiles, full
-- once revealed, then fading one letter after another, left to right.
local LETTER_STAGGER = 0.06
function ui_splash.letter_level(index, t)
  if t < LIFT_START then return 0 end
  local start = FADE_START + (index - 1) * LETTER_STAGGER
  local span = FADE - (#WORD - 1) * LETTER_STAGGER
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

-- Draws the splash at time t. While the word fades, draw_ui paints the
-- application screen underneath so the word dissolves into it.
function ui_splash.draw(t, draw_ui)
  t = t or ui_splash.time()
  if t >= FADE_START and draw_ui then draw_ui() end
  if t >= LIFT_START then
    screen.font_face(WORD_FACE)
    screen.font_size(WORD_SIZE)
    local total = #WORD - 1
    for index = 1, #WORD do total = total + screen.text_extents(WORD:sub(index, index)) end
    local x = math.floor(64 - total / 2)
    for index = 1, #WORD do
      local letter = WORD:sub(index, index)
      local level = ui_splash.letter_level(index, t)
      if level > 0 then
        -- Each letter lifts a couple of pixels as it fades, a small exhale.
        local lift = math.floor(3 * (1 - level / 15) + 0.5)
        screen.level(level)
        screen.move(x, 40 - lift)
        screen.text(letter)
      end
      x = x + screen.text_extents(letter) + 1
    end
    screen.font_face(1)
    screen.font_size(8)
  end
  for row = 0, ROWS - 1 do
    for column = 0, COLUMNS - 1 do
      local x, y, size, level = ui_splash.tile(column, row, t)
      if x and t < lift_time(column, row) then
        -- Until its tile lifts, a cell hides the word beneath, gaps included.
        screen.level(0)
        screen.rect(column * CELL, row * CELL, CELL, CELL)
        screen.fill()
      end
      if x then
        screen.level(level)
        screen.rect(x, y, size, size)
        screen.fill()
      end
    end
  end
end

return ui_splash
