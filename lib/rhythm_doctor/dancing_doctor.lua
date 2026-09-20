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
-- '.' leaves the pixel alone; every other mark is a screen level: dark
-- detail, trousers, skin, shading, and the white of the coat.
local LEVELS = { a = 3, e = 7, b = 11, c = 13, d = 15 }
local IDLE_BPM = 96

-- Four poses an eighth note apart: reach up, arms out, hands on hips, point.
-- Poses two and four stand a row lower with their feet apart, so he bobs and
-- steps on the off-beat rather than flapping his arms on the spot.
local POSES = {
  {
    '............dddd..............',
    '...........ddaadd.............',
    '...........ddaaddb............',
    '...........bddddbbb...........',
    '..........aabbbbbbaa..........',
    '.bbb.....abbbbbbbbbba.....bbb.',
    '.bbb.....bbbbbbbbbbbb.....bbb.',
    '..dd....bbbbbbbbbbbbbb....dd..',
    '..dd....bbbaaabbaaabbb....dd..',
    '...dd...abbaddaaddabba...dd...',
    '...dd...ccaaaabbaaaaa....dd...',
    '....dd.cccabbbbbbbbaa...dd....',
    '....dd..ccaaaabbbbbaa...dd....',
    '.....dd...aaaabbbbaa...dd.....',
    '.....dd....bbbbbbbb....dd.....',
    '.....dd......bbbb......dd.....',
    '......dd..ddaaaaaadd..dd......',
    '......dd.dddabbbbaddd.dd......',
    '......ddddddaaaaaadddddd......',
    '......dddddddaaaaddddddd......',
    '.......dddadddaaddadddd.......',
    '.......dddadddcdddadddd.......',
    '........dddaddcddadddd........',
    '........ddddaaaaaddddd........',
    '........ddddddcddddddd........',
    '........ddddddcdaddddd........',
    '.......daaaaddcdddddddd.......',
    '.......daddaddcdddddddd.......',
    '......ddaaaaddcddddddddd......',
    '......ddddddddcdaddddddd......',
    '......ddddddddcddddddddd......',
    '.....ddddddddcccddddddddd.....',
    '.....ddddddddcccddddddddd.....',
    '......cccccccccccccccccc......',
    '...........eee..eee...........',
    '...........eee..eee...........',
    '...........eee..eee...........',
    '...........eee..eee...........',
    '...........eee..eee...........',
    '...........eee..eee...........',
    '..........cccc..cccc..........',
    '.........ccccc..ccccc.........',
    '..............................',
    '..............................',
  },
  {
    '..............................',
    '............dddd..............',
    '...........ddaadd.............',
    '...........ddaaddb............',
    '...........bddddbbb...........',
    '..........aabbbbbbaa..........',
    '.........abbbbbbbbbba.........',
    '.........bbbbbbbbbbbb.........',
    '........bbbbbbbbbbbbbb........',
    '........bbbaaabbaaabbb........',
    '........abbaddaaddabba........',
    '........ccaaaabbaaaaa.........',
    '.......cccabbbbbbbbaa.........',
    '........ccaaaabbbbbaa.........',
    '..........aaaabbbbaa..........',
    '...........bbbbbbbb...........',
    '.............bbbb.............',
    '..........ddaaaaaadd..........',
    '.........dddabbbbaddd.........',
    '........ddddaaaaaadddd........',
    '.......ddddddaaaadddddd.......',
    'bbbdddddddadddaaddaddddddddbbb',
    'bbbdddddddadddcdddaddddddddbbb',
    '...dddd.dddaddcddadddd.dddd...',
    '........ddddaaaaaddddd........',
    '........ddddddcddddddd........',
    '........ddddddcdaddddd........',
    '.......daaaaddcdddddddd.......',
    '.......daddaddcdddddddd.......',
    '......ddaaaaddcddddddddd......',
    '......ddddddddcdaddddddd......',
    '......ddddddddcddddddddd......',
    '.....ddddddddcccddddddddd.....',
    '.....ddddddddcccddddddddd.....',
    '......cccccccccccccccccc......',
    '..........eee....eee..........',
    '..........eee....eee..........',
    '..........eee....eee..........',
    '..........eee....eee..........',
    '..........eee....eee..........',
    '..........eee....eee..........',
    '.........cccc....cccc.........',
    '........ccccc....ccccc........',
    '..............................',
  },
  {
    '............dddd..............',
    '...........ddaadd.............',
    '...........ddaaddb............',
    '...........bddddbbb...........',
    '..........aabbbbbbaa..........',
    '.........abbbbbbbbbba.........',
    '.........bbbbbbbbbbbb.........',
    '........bbbbbbbbbbbbbb........',
    '........bbbaaabbaaabbb........',
    '........abbaddaaddabba........',
    '........ccaaaabbaaaaa.........',
    '.......cccabbbbbbbbaa.........',
    '........ccaaaabbbbbaa.........',
    '..........aaaabbbbaa..........',
    '...........bbbbbbbb...........',
    '.............bbbb.............',
    '..........ddaaaaaadd..........',
    '.........dddabbbbaddd.........',
    '........ddddaaaaaadddd........',
    '.....ddddddddaaaadddddddd.....',
    '.....dddddadddaaddadddddd.....',
    '....dd.dddadddcdddadddd.dd....',
    '....dd..dddaddcddadddd..dd....',
    '....dd..ddddaaaaaddddd..dd....',
    '.....bbbddddddcddddddd.bbb....',
    '.....bbbddddddcdaddddd.bbb....',
    '.......daaaaddcdddddddd.......',
    '.......daddaddcdddddddd.......',
    '......ddaaaaddcddddddddd......',
    '......ddddddddcdaddddddd......',
    '......ddddddddcddddddddd......',
    '.....ddddddddcccddddddddd.....',
    '.....ddddddddcccddddddddd.....',
    '......cccccccccccccccccc......',
    '............eee..eee..........',
    '............eee..eee..........',
    '............eee..eee..........',
    '............eee..eee..........',
    '............eee..eee..........',
    '............eee..eee..........',
    '...........cccc..cccc.........',
    '..........ccccc..ccccc........',
    '..............................',
    '..............................',
  },
  {
    '..............................',
    '............dddd...........bbb',
    '...........ddaadd..........bbb',
    '...........ddaaddb........dd..',
    '...........bddddbbb.......dd..',
    '..........aabbbbbbaa......dd..',
    '.........abbbbbbbbbba....dd...',
    '.........bbbbbbbbbbbb....dd...',
    '........bbbbbbbbbbbbbb...dd...',
    '........bbbaaabbaaabbb..dd....',
    '........abbaddaaddabba..dd....',
    '........ccaaaabbaaaaa...dd....',
    '.......cccabbbbbbbbaa...dd....',
    '........ccaaaabbbbbaa..dd.....',
    '..........aaaabbbbaa...dd.....',
    '...........bbbbbbbb....dd.....',
    '.............bbbb......dd.....',
    '..........ddaaaaaadd..dd......',
    '.........dddabbbbaddd.dd......',
    '........ddddaaaaaadddddd......',
    '.....ddddddddaaaaddddddd......',
    '.....dddddadddaaddadddd.......',
    '....dd.dddadddcdddadddd.......',
    '....dd..dddaddcddadddd........',
    '....dd..ddddaaaaaddddd........',
    '.....bbbddddddcddddddd........',
    '.....bbbddddddcdaddddd........',
    '.......daaaaddcdddddddd.......',
    '.......daddaddcdddddddd.......',
    '......ddaaaaddcddddddddd......',
    '......ddddddddcdaddddddd......',
    '......ddddddddcddddddddd......',
    '.....ddddddddcccddddddddd.....',
    '.....ddddddddcccddddddddd.....',
    '......cccccccccccccccccc......',
    '..........eee....eee..........',
    '..........eee....eee..........',
    '..........eee....eee..........',
    '..........eee....eee..........',
    '..........eee....eee..........',
    '..........eee....eee..........',
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
