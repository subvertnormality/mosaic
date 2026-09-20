package.path = './lib/?.lua;' .. package.path
local Doctor = require('rhythm_doctor.dancing_doctor')

local passed = 0
local function check(condition, message)
  if not condition then error(message, 2) end
  passed = passed + 1
end

-- Loading the module already asserts every pose is the declared size and uses
-- only known marks, so a mistyped row cannot reach the screen.
check(#Doctor.FRAMES == 4, 'four poses make the loop')
check(Doctor.WIDTH == 30 and Doctor.HEIGHT == 44, 'the declared size is what the page reserves')

-- He must fit the right-hand third the page leaves for him, at 128x64.
check(97 + Doctor.WIDTH <= 128, 'the sprite fits beside the screen edge')
check(15 + Doctor.HEIGHT <= 64, 'the sprite fits above the screen bottom')

-- Every pose has to carry the silhouette; an empty or near-empty one would
-- read as a dropped frame.
for index, frame in ipairs(Doctor.FRAMES) do
  local lit, levels = 0, {}
  for _, band in ipairs(frame) do
    levels[band.level] = true
    for _, run in ipairs(band.runs) do
      lit = lit + run[3]
      check(run[1] >= 0 and run[1] + run[3] <= Doctor.WIDTH, 'pose ' .. index .. ' runs off the canvas')
      check(run[2] >= 0 and run[2] < Doctor.HEIGHT, 'pose ' .. index .. ' runs past the last row')
    end
  end
  check(lit > 250, 'pose ' .. index .. ' is too sparse to read: ' .. lit .. ' pixels')
  check(levels[15], 'pose ' .. index .. ' has no white: the coat carries the shape')
  check(levels[4], 'pose ' .. index .. ' has no dark detail')
end

-- The poses differ, or he is standing still rather than dancing.
local signature = {}
for index, frame in ipairs(Doctor.FRAMES) do
  local parts = {}
  for _, band in ipairs(frame) do
    for _, run in ipairs(band.runs) do parts[#parts + 1] = table.concat(run, ',') .. ':' .. band.level end
  end
  local key = table.concat(parts, ' ')
  check(signature[key] == nil, 'pose ' .. index .. ' repeats pose ' .. tostring(signature[key]))
  signature[key] = index
end

-- Two poses to the beat, at the tempo the capture was analysed at.
check(Doctor.pose_at(0, 120) == 1, 'the loop starts at the first pose')
check(Doctor.pose_at(0.25, 120) == 2, 'an eighth note at 120 advances one pose')
check(Doctor.pose_at(0.5, 120) == 3, 'and the next eighth advances again')
check(Doctor.pose_at(1.0, 120) == 1, 'a whole beat returns to the first pose')
check(Doctor.pose_at(0.125, 240) == 2, 'a faster tempo dances faster')

-- Without a usable tempo he keeps dancing rather than freezing on one pose.
local idle = {}
for step = 0, 7 do idle[Doctor.pose_at(step * 0.3125, nil)] = true end
local distinct = 0
for _ in pairs(idle) do distinct = distinct + 1 end
check(distinct == 4, 'the idle shuffle still uses every pose')
check(Doctor.pose_at(1, 0) == Doctor.pose_at(1, nil), 'a nonsense tempo falls back to the shuffle')
check(Doctor.pose_at(nil, 120) == 1, 'a missing clock does not error')

-- Drawing asks the screen for one fill per level, not one per pixel.
local levels, rects, fills = {}, 0, 0
local previous = screen
screen = { level = function(value) levels[#levels + 1] = value end,
           rect = function() rects = rects + 1 end, fill = function() fills = fills + 1 end }
Doctor.draw(97, 15, 1)
screen = previous
check(fills == #levels, 'each level is filled exactly once')
check(fills <= 4, 'a pose costs at most four fills: ' .. fills)
check(rects > 40, 'the pose actually drew: ' .. rects .. ' runs')
for i = 2, #levels do check(levels[i] > levels[i - 1], 'levels are set in one ascending pass') end

Doctor.draw(97, 15, 99)  -- a pose that does not exist must be a no-op, not an error

print('test_dancing_doctor: ' .. passed .. ' tests passed')
