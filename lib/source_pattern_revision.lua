-- Session-only revisions for shared source patterns. No fields are serialized.
-- Every explicit edit gets a fresh token even if it restores identical values.
local Revision = {}
Revision.__index = Revision

function Revision.new()
  return setmetatable({songs=setmetatable({}, {__mode='k'}), serial=0}, Revision)
end

local function source_at(song, number)
  assert(type(song)=='table' and type(song.patterns)=='table', 'invalid song')
  assert(type(number)=='number' and number%1==0 and number>=1 and number<=16, 'invalid source number')
  local source = song.patterns[number]
  assert(type(source)=='table', 'missing source pattern')
  return source
end

function Revision:get(song, number)
  local source = source_at(song, number)
  local entries = self.songs[song]
  if not entries then entries={}; self.songs[song]=entries end
  local entry = entries[number]
  if not entry or entry.source ~= source then
    self.serial = self.serial + 1
    entry = {source=source, revision=self.serial}
    entries[number] = entry
  end
  return entry.revision
end

function Revision:edited(song, number)
  self:get(song, number)
  self.serial = self.serial + 1
  self.songs[song][number].revision = self.serial
  return self.serial
end

return Revision
