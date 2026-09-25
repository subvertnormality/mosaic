-- Decorative characters and value dials for the live screen's art region
-- (x75..127, y30..54; docs/ui-reimplementation code/characters.lua).
--
-- They are art, never data: nothing here reads the program, draws a value or
-- uses randomness. `motion` carries a beat position when the screen is
-- animated (lib/ui_motion.lua decides), so characters keep time:
--   the Doctor dances to the analysed tempo in four eighth-note poses,
--   the garden sways and the choir bobs while the sequencer plays,
--   the metronome swings on the clock.
-- With no beat every character stands in its rest pose, which is exactly the
-- accepted atlas drawing.
local pose = 0

local function line(x, y, xx, yy, l)
  screen.level(l or 10); screen.move(x, y); screen.line(xx, yy); screen.stroke()
end
local function box(x, y, w, h, l, outline)
  screen.level(l or 15); screen.rect(x, y, w, h)
  if outline then screen.stroke() else screen.fill() end
end
local function circle(x, y, r, l, outline)
  screen.level(l or 15); screen.circle(x, y, r)
  if outline then screen.stroke() else screen.fill() end
end

-- Four poses an eighth note apart: rest, left hand up, arms wide, right hand up.
local function eighth(motion)
  if not motion or not motion.beat then return 0 end
  return math.floor(motion.beat * 2) % 4
end

local function doctor(p, motion)
  local step = eighth(motion)
  -- Every other eighth he dips a pixel, so the dance has a bounce.
  local o = (step == 1 or step == 3) and 1 or 0
  -- Head mirror, swept hair, shades, broad white lapels and a stethoscope.
  box(92, 32 + o, 19, 9, 10); box(89, 33 + o, 4, 4, 10)
  box(91, 31 + o, 17, 3, 5); box(89, 33 + o, 6, 2, 5)
  line(92, 34 + o, 111, 34 + o, 15); circle(106, 33 + o, 3, 15); circle(106, 33 + o, 1, 0)
  box(94, 36 + o, 6, 3, 0); box(103, 36 + o, 6, 3, 0); line(100, 37 + o, 103, 37 + o, 0)
  line(99, 41 + o, 105, 41 + o, 15); box(101, 42 + o, 3, 2, 10)
  box(92, 44 + o, 19, 7, 15)
  line(96, 44 + o, 101, 49 + o, 0); line(108, 44 + o, 103, 49 + o, 0); line(102, 48 + o, 102, 51, 0)
  line(95, 44 + o, 95, 48 + o, 3); line(95, 48 + o, 98, 49 + o, 3); circle(98, 49 + o, 1, 0)
  -- Arms: a jaunty elbow at rest; on the beat they reach and spread.
  if step == 1 then
    line(92, 45 + o, 87, 42 + o, 15); line(87, 42 + o, 85, 36 + o, 15)
    line(111, 45 + o, 115, 48 + o, 15); line(115, 48 + o, 118, 44 + o, 15)
  elseif step == 2 then
    line(92, 45 + o, 84, 43 + o, 15); line(84, 43 + o, 80, 44 + o, 15)
    line(111, 45 + o, 119, 43 + o, 15); line(119, 43 + o, 123, 44 + o, 15)
  elseif step == 3 then
    line(92, 45 + o, 87, 48 + o, 15); line(87, 48 + o, 84, 44 + o, 15)
    line(111, 45 + o, 116, 42 + o, 15); line(116, 42 + o, 118, 36 + o, 15)
  else
    line(92, 45, 87, 48, 15); line(87, 48, 84, 44 - (p % 2), 15)
    line(111, 45, 115, 48, 15); line(115, 48, 118, 44, 15)
  end
  -- Shoes: one taps with the beat.
  box(93, 52, 7, 1, 15); box(105, 51 + ((p + step) % 2), 8, 1, 15)
  -- Musical sparks are decorative, never an input meter; they flash on the beat.
  local spark = (motion and motion.beat and step % 2 == 0) and 12 or 6
  line(79, 35, 81, 38, spark); line(81, 38, 79, 41, spark)
  line(122, 35, 120, 38, spark); line(120, 38, 122, 41, spark)
end

local function garden(p, active, motion)
  local beat = motion and motion.beat
  -- Two protected flowers and four ranked sprouts. No per-hit randomness.
  line(77, 51, 125, 51, 7)
  for k = 0, 5 do
    local x = 81 + k * 8
    local tall = k == 0 or k == 3
    local h = tall and 15 or (active and (5 + (k % 3) * 2) or 3)
    -- While playing, stems lean with the beat, each a little behind the last.
    local sway = beat and math.floor(math.sin((beat - k * 0.125) * math.pi) * 1.5 + 0.5) or 0
    line(x, 50, x + sway, 50 - h, tall and 15 or 9)
    if tall then
      local nod = beat and ((math.floor(beat * 2) + k) % 2) or 0
      box(x - 2 + sway, 33 + nod, 5, 5, 15); box(x + sway, 35 + nod, 1, 1, 0)
      line(x, 44, x - 3, 41, 9); line(x, 47, x + 3, 44, 9)
    elseif active then
      line(x + sway, 50 - h + 3, x - 3 + sway, 50 - h, 10); line(x + sway, 50 - h + 4, x + 3 + sway, 50 - h + 1, 10)
    else
      box(x - 2, 46, 4, 3, 6, true)
    end
  end
  -- Tiny garden visitor: blinks, and hops on the downbeat while playing.
  local hop = (beat and math.floor(beat) % 2 == 0 and (beat % 1) < 0.25) and 1 or 0
  box(115, 30 - hop, 8, 7, 12); box(117, 32 - hop, 1, p == 1 and 1 or 2, 0); box(121, 32 - hop, 1, 2, 0)
  line(116, 37, 118, 39, 8); line(122, 37, 120, 39, 8)
end

local function choir(p, register, motion)
  local beat = motion and motion.beat
  -- Three note creatures. Common-tone Bass stays on its rung in every pose;
  -- while playing the upper voices bob on their own eighths, a little round.
  for k = 0, 2 do
    local x = 82 + k * 17
    local y = register and (45 - k * 5) or (44 - k * 3)
    local bob = (beat and k > 0 and math.floor(beat * 2) % 3 == k) and 1 or 0
    y = y - bob
    line(x - 5, y + 6 + bob, x + 6, y + 6 + bob, 6)
    circle(x, y, 5, k == 0 and 15 or 10)
    box(x - 2, y - 1, 1, p == 1 and 1 or 2, 0); box(x + 2, y - 1, 1, 2, 0)
    local top = math.max(30, y - 12); line(x + 5, y, x + 5, top, 13); line(x + 5, top, x + 8, top + 2, 13)
    line(x - 2, y + 5, x - 3, y + 7, 10); line(x + 2, y + 5, x + 3, y + 7, 10)
  end
end

-- A small wooden metronome whose pendulum swings on the clock; at rest it
-- hangs straight. Two tick marks light on each beat.
local function metronome(p, motion)
  local beat = motion and motion.beat
  line(92, 54, 112, 54, 9); line(92, 54, 98, 31, 9); line(112, 54, 106, 31, 9); line(98, 31, 106, 31, 9)
  line(96, 48, 108, 48, 5)
  local angle = beat and math.sin(beat * math.pi) * 0.5 or 0
  local px, py = 102, 50
  line(px, py, px + math.sin(angle) * 17, py - math.cos(angle) * 17, 15)
  local wx, wy = px + math.sin(angle) * 11, py - math.cos(angle) * 11
  box(wx - 2, wy - 1, 4, 3, 12)
  circle(px, py, 1, 15)
  if beat and (beat % 1) < 0.15 then
    line(86, 36, 88, 38, 12); line(118, 36, 116, 38, 12)
  end
  -- Two little eyes on the case, which blink with everyone else.
  box(99, 44, 1, p == 1 and 1 or 2, 0); box(105, 44, 1, p == 1 and 1 or 2, 0)
end

local M = {}

-- p: 0 rest, 1 blink/tap. `active` only changes the garden's sprouts.
-- motion: nil at rest, or {beat = beats} to keep time.
function M.draw_art(kind, p, active, motion)
  pose = p or 0
  if kind == 'doctor' or kind == 'window' then doctor(pose, motion)
  elseif kind == 'garden' then garden(pose, active, motion)
  elseif kind == 'choir' then choir(pose, false, motion)
  elseif kind == 'register' then choir(pose, true, motion)
  elseif kind == 'metronome' then metronome(pose, motion)
  end
end

-- A value dial in the art region: a 270 degree arc lit up to `fraction`
-- (0..1), with a needle and end ticks. Decorative: the value itself is always
-- drawn whole as text beside it.
function M.draw_dial(fraction)
  fraction = math.max(0, math.min(1, fraction or 0))
  local cx, cy, r = 101, 43, 11
  local start, sweep = math.pi * 0.75, math.pi * 1.5
  -- Each arc starts a fresh path at its own start point (an arc otherwise
  -- joins the previous point with a straight line).
  local function arc(from, to, level)
    screen.level(level)
    screen.move(cx + math.cos(from) * r, cy + math.sin(from) * r)
    screen.arc(cx, cy, r, from, to)
    screen.stroke()
  end
  arc(start, start + sweep, 5)
  if fraction > 0.01 then arc(start, start + sweep * fraction, 15) end
  for _, t in ipairs({0, 0.5, 1}) do
    local a = start + sweep * t
    line(cx + math.cos(a) * (r + 2), cy + math.sin(a) * (r + 2), cx + math.cos(a) * (r + 4), cy + math.sin(a) * (r + 4), 6)
  end
  local a = start + sweep * fraction
  line(cx, cy, cx + math.cos(a) * (r - 3), cy + math.sin(a) * (r - 3), 15)
  circle(cx, cy, 2, 15)
end

return M
