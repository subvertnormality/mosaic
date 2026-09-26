local harmony_config=include("mosaic/lib/harmony/config")
local harmony_config_state=include("mosaic/lib/harmony/config_state")
local merge_config=include("mosaic/lib/musical_merge/config")
local merge_state=include("mosaic/lib/musical_merge/state")
local transaction={}

local function copy(value,seen)
  if type(value)~="table"then return value end;seen=seen or{};if seen[value]then return seen[value]end
  local result={};seen[value]=result;for key,item in pairs(value)do result[copy(key,seen)]=copy(item,seen)end;return result
end

function transaction.snapshot(song)
  local result={voicing=copy(song.voicing),channels={}}
  for number=1,16 do result.channels[number]={voicing=copy(song.channels[number].voicing),musical_merge=copy(song.channels[number].musical_merge)}end
  return result
end

function transaction.validate(song,snapshot)
  if type(snapshot)~="table"or type(snapshot.channels)~="table"then return nil,"optional configuration snapshot"end
  -- Validation only reads, so the shadow shares everything but the optional
  -- configuration under test: shallow song and channel tables with that
  -- configuration copied in. (A deep copy of the whole song, patterns and locks
  -- included, made every apply stall the sequencer on the norns.)
  local shadow={}
  for key,value in pairs(song)do shadow[key]=value end
  shadow.voicing=copy(snapshot.voicing);shadow.channels={}
  for number,channel in pairs(song.channels or{})do
    local c={};for key,value in pairs(channel)do c[key]=value end;shadow.channels[number]=c
  end
  for number=1,16 do
    if type(snapshot.channels[number])~="table"then return nil,"channel "..number.." optional configuration"end
    shadow.channels[number].voicing=copy(snapshot.channels[number].voicing)
    shadow.channels[number].musical_merge=copy(snapshot.channels[number].musical_merge)
  end
  local ok,reason=harmony_config.validate_song(shadow);if not ok then return nil,reason end
  for number=1,16 do local merge=shadow.channels[number].musical_merge;if merge then
    ok,reason=merge_config.validate(merge);if not ok then return nil,reason end
    if merge.target.kind=="chord"then local group=shadow.voicing and shadow.voicing.groups[merge.target.group_id]
      if not(group and group.enabled)then return nil,"channel "..number.." chord source unavailable"end
    end
  end end
  return true
end

local function encode(value)
  if type(value)~="table"then return tostring(value)end;local keys={};for key in pairs(value)do keys[#keys+1]=key end
  table.sort(keys,function(a,b)return tostring(a)<tostring(b)end);local out={"{"};for _,key in ipairs(keys)do out[#out+1]=tostring(key);out[#out+1]="=";out[#out+1]=encode(value[key]);out[#out+1]=";"end;out[#out+1]="}";return table.concat(out)
end
-- Values compare as their encodings do (keys and scalars by tostring), but
-- walked directly: serialising and sorting whole tables on every apply stalled
-- the sequencer on the norns. Keys that print alike fall back to the encoding.
local function same(left,right)
  local lt,rt=type(left)=="table",type(right)=="table"
  if not lt and not rt then return tostring(left)==tostring(right)end
  if lt~=rt then return encode(left)==encode(right)end
  if left==right then return true end
  local keyed,count={},0
  for key,value in pairs(left)do
    local name=tostring(key);if keyed[name]~=nil then return encode(left)==encode(right)end
    keyed[name]=value;count=count+1
  end
  local seen,seen_count={},0
  for key,value in pairs(right)do
    local name=tostring(key);if seen[name]then return encode(left)==encode(right)end
    seen[name]=true;seen_count=seen_count+1
    local mine=keyed[name];if mine==nil or not same(mine,value)then return false end
  end
  return seen_count==count
end
local function changed(left,right)return not same(left,right)end
transaction.equivalent=function(left,right)return not changed(left,right)end

-- Apply only the paths this transaction originally changed.  A later edit on
-- another channel (or another field in the same group) is therefore not
-- replaced by an older channel-local undo.  Diverged overlapping values are
-- retained; validation below still makes the combined result atomic.
local function transition_value(current,expected,target)
  if not changed(current,expected)then return copy(target)end
  if type(expected)~="table"or type(target)~="table"or type(current)~="table"then return copy(current)end
  local result=copy(current);local keys={}
  for key in pairs(expected)do keys[key]=true end;for key in pairs(target)do keys[key]=true end
  for key in pairs(keys)do if changed(expected[key],target[key])then
    result[key]=transition_value(current[key],expected[key],target[key])
  end end
  return result
end

function transaction.apply(song,snapshot,playing,boundary)
  local ok,reason=transaction.validate(song,snapshot);if not ok then return nil,reason end
  local before=transaction.snapshot(song)
  song.voicing=copy(snapshot.voicing)
  harmony_config_state.request_song(song,snapshot.voicing or{schema_version=1,groups={}},playing)
  for number=1,16 do
    local target=snapshot.channels[number];song.channels[number].voicing=copy(target.voicing)
    harmony_config_state.request_channel(song,number,target.voicing or harmony_config.new_channel(),playing)
    if changed(before.channels[number].musical_merge,target.musical_merge)then
      song.channels[number].musical_merge=copy(target.musical_merge)
      local requested=target.musical_merge or merge_config.new()
      if boundary=="pattern"then merge_state.request_global(song,number,requested,playing)else merge_state.request(song,number,requested,playing)end
      if not playing and pattern and pattern.update_working_pattern then pattern.update_working_pattern(number,song)end
    end
  end
  return true
end


function transaction.apply_transition(song,expected,target,playing,boundary)
  local live=transaction.snapshot(song)
  local patched=transition_value(live,expected,target)
  return transaction.apply(song,patched,playing,boundary)
end

transaction.copy=copy
return transaction
