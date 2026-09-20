-- A doctor, dancing, in the empty right-hand third of the Rhythm Doctor page.
--
-- Drawn in the house style of a LucasArts point-and-click sprite: a big bald
-- dome with a tuft over each ear, round spectacles, a nose with somewhere to
-- go, a head mirror worn up on its band, and a long white coat that carries
-- the silhouette.
--
-- The norns screen is black, so he is built out of light.  A dark level is
-- only ever a feature inside a lit area -- hair against the face, the
-- stethoscope against the coat, the hole through the head mirror -- and never
-- an outline, which would simply vanish.
--
-- He dances to the analysed tempo when there is one, so the page keeps time
-- with the capture it is describing, and shuffles when there is not.
local Doctor = {}

local WIDTH, HEIGHT = 30, 44
-- '.' leaves the pixel alone; every other mark is a screen level.
local LEVELS = { a = 4, b = 8, c = 12, d = 15 }
local IDLE_BPM = 96

-- Four poses an eighth note apart: reach up, arms out, hands on hips, point.
-- Poses two and four stand a row lower with their feet apart, so he bobs and
-- steps on the off-beat rather than flapping his arms on the spot.
local POSES = {
  {
    '............dddd..............',
    '...........ddaadd.............',
    '...........ddaaddbb...........',
    '..........bbddddbbbb..........',
    '.........aabbbbbbbbaa.........',
    '.bbb.....abbbbbbbbbba.....bbb.',
    '.bbb....abbbbbbbbbbbba....bbb.',
    '..dd....aaaaabbaaabbaa....dd..',
    '..dd....aaaddaaddabbaa....dd..',
    '...dd..ccaaaabbaaabbaa...dd...',
    '...dd.cccabbbbbbbbbbaa...dd...',
    '....dd.ccaaaabbbbbbbaa..dd....',
    '....dd..aabaabbbbbbbaa..dd....',
    '.....dd..abbbbbbbbbba..dd.....',
    '.....dd...bbbbbbbbbb...dd.....',
    '.....dd......bbbb......dd.....',
    '......ddddd.aaaaaa.ddddd......',
    '......ddddddabbbbadddddd......',
    '......ddddddaaaaaadddddd......',
    '......ddddaddaaaadaddddd......',
    '.......dddadddaaddadddd.......',
    '.......ddddaddcddaddddd.......',
    '.......dddddaaaaadddddd.......',
    '.......dddddddcdddddddd.......',
    '.......dddddddcdadddddd.......',
    '.......daaaaddcdddddddd.......',
    '.......daddaddcdddddddd.......',
    '.......daaaaddcdddddddd.......',
    '.......dddddddcdadddddd.......',
    '.......dddddddcdddddddd.......',
    '.......dddddddcdddddddd.......',
    '.......ddddddcccddddddd.......',
    '.......ddddddcccddddddd.......',
    '.......cccccccccccccccc.......',
    '...........bbb..bbb...........',
    '...........bbb..bbb...........',
    '...........bbb..bbb...........',
    '...........bbb..bbb...........',
    '...........bbb..bbb...........',
    '...........bbb..bbb...........',
    '..........cccc..cccc..........',
    '.........ccccc..ccccc.........',
    '..............................',
    '..............................',
  },
  {
    '..............................',
    '............dddd..............',
    '...........ddaadd.............',
    '...........ddaaddbb...........',
    '..........bbddddbbbb..........',
    '.........aabbbbbbbbaa.........',
    '.........abbbbbbbbbba.........',
    '........abbbbbbbbbbbba........',
    '........aaaaabbaaabbaa........',
    '........aaaddaaddabbaa........',
    '.......ccaaaabbaaabbaa........',
    '......cccabbbbbbbbbbaa........',
    '.......ccaaaabbbbbbbaa........',
    '........aabaabbbbbbbaa........',
    '.........abbbbbbbbbba.........',
    '..........bbbbbbbbbb..........',
    '.............bbbb.............',
    '.......dddd.aaaaaa.dddd.......',
    '.......dddddabbbbaddddd.......',
    '.......dddddaaaaaaddddd.......',
    '.......dddaddaaaadadddd.......',
    'bbbdddddddadddaaddaddddddddbbb',
    'bbbddddddddaddcddadddddddddbbb',
    '...dddddddddaaaaadddddddddd...',
    '.......dddddddcdddddddd.......',
    '.......dddddddcdadddddd.......',
    '.......daaaaddcdddddddd.......',
    '.......daddaddcdddddddd.......',
    '.......daaaaddcdddddddd.......',
    '.......dddddddcdadddddd.......',
    '.......dddddddcdddddddd.......',
    '.......dddddddcdddddddd.......',
    '.......ddddddcccddddddd.......',
    '.......ddddddcccddddddd.......',
    '.......cccccccccccccccc.......',
    '..........bbb....bbb..........',
    '..........bbb....bbb..........',
    '..........bbb....bbb..........',
    '..........bbb....bbb..........',
    '..........bbb....bbb..........',
    '..........bbb....bbb..........',
    '.........cccc....cccc.........',
    '........ccccc....ccccc........',
    '..............................',
  },
  {
    '............dddd..............',
    '...........ddaadd.............',
    '...........ddaaddbb...........',
    '..........bbddddbbbb..........',
    '.........aabbbbbbbbaa.........',
    '.........abbbbbbbbbba.........',
    '........abbbbbbbbbbbba........',
    '........aaaaabbaaabbaa........',
    '........aaaddaaddabbaa........',
    '.......ccaaaabbaaabbaa........',
    '......cccabbbbbbbbbbaa........',
    '.......ccaaaabbbbbbbaa........',
    '........aabaabbbbbbbaa........',
    '.........abbbbbbbbbba.........',
    '..........bbbbbbbbbb..........',
    '.............bbbb.............',
    '.......dddd.aaaaaa.dddd.......',
    '.......dddddabbbbaddddd.......',
    '.......dddddaaaaaaddddd.......',
    '.....dddddaddaaaadadddddd.....',
    '.....dddddadddaaddadddddd.....',
    '....dd.ddddaddcddaddddd.dd....',
    '....dd.dddddaaaaadddddd.dd....',
    '....dd.dddddddcdddddddd.dd....',
    '.....bbbddddddcdaddddddbbb....',
    '.....bbbaaaaddcddddddddbbb....',
    '.......daddaddcdddddddd.......',
    '.......daaaaddcdddddddd.......',
    '.......dddddddcdadddddd.......',
    '.......dddddddcdddddddd.......',
    '.......dddddddcdddddddd.......',
    '.......ddddddcccddddddd.......',
    '.......ddddddcccddddddd.......',
    '.......cccccccccccccccc.......',
    '............bbb..bbb..........',
    '............bbb..bbb..........',
    '............bbb..bbb..........',
    '............bbb..bbb..........',
    '............bbb..bbb..........',
    '............bbb..bbb..........',
    '...........cccc..cccc.........',
    '..........ccccc..ccccc........',
    '..............................',
    '..............................',
  },
  {
    '..............................',
    '............dddd...........bbb',
    '...........ddaadd..........bbb',
    '...........ddaaddbb.......dd..',
    '..........bbddddbbbb......dd..',
    '.........aabbbbbbbbaa.....dd..',
    '.........abbbbbbbbbba....dd...',
    '........abbbbbbbbbbbba...dd...',
    '........aaaaabbaaabbaa...dd...',
    '........aaaddaaddabbaa..dd....',
    '.......ccaaaabbaaabbaa..dd....',
    '......cccabbbbbbbbbbaa..dd....',
    '.......ccaaaabbbbbbbaa..dd....',
    '........aabaabbbbbbbaa.dd.....',
    '.........abbbbbbbbbba..dd.....',
    '..........bbbbbbbbbb...dd.....',
    '.............bbbb......dd.....',
    '.......dddd.aaaaaa.ddddd......',
    '.......dddddabbbbadddddd......',
    '.......dddddaaaaaadddddd......',
    '.....dddddaddaaaadaddddd......',
    '.....dddddadddaaddadddd.......',
    '....dd.ddddaddcddaddddd.......',
    '....dd.dddddaaaaadddddd.......',
    '....dd.dddddddcdddddddd.......',
    '.....bbbddddddcdadddddd.......',
    '.....bbbaaaaddcdddddddd.......',
    '.......daddaddcdddddddd.......',
    '.......daaaaddcdddddddd.......',
    '.......dddddddcdadddddd.......',
    '.......dddddddcdddddddd.......',
    '.......dddddddcdddddddd.......',
    '.......ddddddcccddddddd.......',
    '.......ddddddcccddddddd.......',
    '.......cccccccccccccccc.......',
    '..........bbb....bbb..........',
    '..........bbb....bbb..........',
    '..........bbb....bbb..........',
    '..........bbb....bbb..........',
    '..........bbb....bbb..........',
    '..........bbb....bbb..........',
    '.........cccc....cccc.........',
    '........ccccc....ccccc........',
    '..............................',
  },
}

-- Horizontal runs, grouped by level, so a pose costs one fill per level rather
-- than one per pixel.  Compiled at load; nothing parses a string per frame.
local function compile(rows)
  assert(#rows == HEIGHT, 'a pose is ' .. HEIGHT .. ' rows, not ' .. #rows)
  local grouped, order = {}, {}
  for y = 1, HEIGHT do
    local row = rows[y]
    assert(#row == WIDTH, 'row ' .. y .. ' is ' .. #row .. ' columns, not ' .. WIDTH)
    local x = 1
    while x <= WIDTH do
      local mark = row:sub(x, x)
      local level = LEVELS[mark]
      if level then
        local last = x
        while last < WIDTH and row:sub(last + 1, last + 1) == mark do last = last + 1 end
        if not grouped[level] then grouped[level] = {}; order[#order + 1] = level end
        local runs = grouped[level]
        runs[#runs + 1] = { x - 1, y - 1, last - x + 1 }
        x = last + 1
      else
        assert(mark == '.', 'row ' .. y .. ' has an unknown mark ' .. mark)
        x = x + 1
      end
    end
  end
  table.sort(order)
  local frame = {}
  for i = 1, #order do frame[i] = { level = order[i], runs = grouped[order[i]] } end
  return frame
end

local FRAMES = {}
for i = 1, #POSES do FRAMES[i] = compile(POSES[i]) end

Doctor.WIDTH, Doctor.HEIGHT, Doctor.FRAMES = WIDTH, HEIGHT, FRAMES

-- Two poses to the beat.  Without a tempo he shuffles rather than freezing.
function Doctor.pose_at(seconds, bpm)
  if type(seconds) ~= 'number' or seconds ~= seconds then return 1 end
  local tempo = (type(bpm) == 'number' and bpm >= 20 and bpm <= 400) and bpm or IDLE_BPM
  return math.floor(seconds * tempo / 30) % #FRAMES + 1
end

function Doctor.draw(x, y, pose)
  local frame = FRAMES[pose]
  if not frame then return end
  for i = 1, #frame do
    local band = frame[i]
    screen.level(band.level)
    for j = 1, #band.runs do
      local run = band.runs[j]
      screen.rect(x + run[1], y + run[2], run[3], 1)
    end
    screen.fill()
  end
end

return Doctor
