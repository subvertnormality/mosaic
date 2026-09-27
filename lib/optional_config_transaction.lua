local harmony_config=include("mosaic/lib/harmony/config")
local harmony_config_state=include("mosaic/lib/harmony/config_state")
local merge_config=include("mosaic/lib/musical_merge/config")
local merge_state=include("mosaic/lib/musical_merge/state")
local merge_structure=include("mosaic/lib/musical_merge/structure")
local merge_dependency=include("mosaic/lib/musical_merge/dependency")
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

-- The same shape as a snapshot, but referring to the song's live tables. Only
-- for reading and comparing: it must not be kept or changed. (Copying for a
-- read-only comparison cost milliseconds per apply on the norns.)
function transaction.view(song)
  local result={voicing=song.voicing,channels={}}
  for number=1,16 do result.channels[number]={voicing=song.channels[number].voicing,musical_merge=song.channels[number].musical_merge}end
  return result
end

-- playing: while the transport runs, the one-way dependency check (plan §1.5)
-- uses the union of configured edges in the active, requested, per-channel
-- queued and global queued snapshots and the proposed replacement; stopped,
-- the resulting snapshot alone.
function transaction.validate(song,snapshot,playing)
  if type(snapshot)~="table"or type(snapshot.channels)~="table"then return nil,"optional configuration snapshot"end
  -- Validation only reads, so the shadow shares everything but the optional
  -- configuration under test: shallow song and channel tables with that
  -- configuration copied in. (A deep copy of the whole song, patterns and locks
  -- included, made every apply stall the sequencer on the norns.)
  local shadow={}
  for key,value in pairs(song)do shadow[key]=value end
  shadow.voicing=snapshot.voicing;shadow.channels={}
  for number,channel in pairs(song.channels or{})do
    local c={};for key,value in pairs(channel)do c[key]=value end;shadow.channels[number]=c
  end
  for number=1,16 do
    if type(snapshot.channels[number])~="table"then return nil,"channel "..number.." optional configuration"end
    -- Read in place: validation never changes what it is given.
    shadow.channels[number].voicing=snapshot.channels[number].voicing
    shadow.channels[number].musical_merge=snapshot.channels[number].musical_merge
  end
  local ok,reason=harmony_config.validate_song(shadow);if not ok then return nil,reason end
  local edges,proposed={},{}
  for number=1,16 do local merge=shadow.channels[number].musical_merge;if merge then
    -- Version 1 (for example from a live project built before migration) is
    -- validated through its canonical v2 form; apply stores that form.
    merge,reason=merge_config.canonicalize(merge,number);if not merge then return nil,reason end
    if merge.target.kind=="chord"then local group=shadow.voicing and shadow.voicing.groups[merge.target.group_id]
      if not(group and group.enabled)then return nil,"channel "..number.." chord source unavailable"end
    end
    -- Plan §4: markers on need an existing enabled group (whatever the mode:
    -- the stored reference is what is saved).
    if merge.structure.markers~="off"and not merge_structure.group_available(shadow.voicing,merge.structure.group_id)then
      return nil,"channel "..number.." structure group unavailable"
    end
    merge_dependency.add(edges,number,merge)
  end end
  -- The channels whose edges this transaction proposes to change.
  for number=1,16 do
    local live=song.channels and song.channels[number]and song.channels[number].musical_merge
    local proposed_leaders=merge_dependency.leaders(snapshot.channels[number].musical_merge)
    local live_leaders=merge_dependency.leaders(live)
    if table.concat(proposed_leaders,",")~=table.concat(live_leaders,",")then proposed[number]=true end
    if playing then
      merge_dependency.add(edges,number,live)
      local record=merge_state.peek(song,number)
      if record then
        merge_dependency.add(edges,number,record.active);merge_dependency.add(edges,number,record.queued)
        merge_dependency.add(edges,number,record.global_queued)
      end
    end
  end
  local graph_ok,graph_reason=merge_dependency.check(edges,proposed)
  if not graph_ok then return nil,graph_reason end
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
-- The result is only read by apply, which copies everything it stores, so an
-- unchanged branch is returned as is rather than copied twice.
local function transition_value(current,expected,target)
  if not changed(current,expected)then return target end
  if type(expected)~="table"or type(target)~="table"or type(current)~="table"then return current end
  local result=copy(current);local keys={}
  for key in pairs(expected)do keys[key]=true end;for key in pairs(target)do keys[key]=true end
  for key in pairs(keys)do if changed(expected[key],target[key])then
    result[key]=transition_value(current[key],expected[key],target[key])
  end end
  return result
end

-- validated: the caller has already validated a configuration identical to
-- `snapshot` against this song, so it is not validated a second time.
function transaction.apply(song,snapshot,playing,boundary,validated)
  if not validated then
    local ok,reason=transaction.validate(song,snapshot,playing);if not ok then return nil,reason end
  end
  -- The previous merge settings are only compared, so they are read in place
  -- (each is compared before its channel is replaced below).
  local before=transaction.view(song)
  local changed_channels
  song.voicing=copy(snapshot.voicing)
  harmony_config_state.request_song(song,snapshot.voicing or{schema_version=1,groups={}},playing)
  for number=1,16 do
    local target=snapshot.channels[number];song.channels[number].voicing=copy(target.voicing)
    harmony_config_state.request_channel(song,number,target.voicing or harmony_config.new_channel(),playing)
    local merge=target.musical_merge and assert(merge_config.canonicalize(target.musical_merge,number))
    if changed(before.channels[number].musical_merge,merge)then
      song.channels[number].musical_merge=merge
      local requested=merge or merge_config.new()
      if boundary=="pattern"then merge_state.request_global(song,number,requested,playing)else merge_state.request(song,number,requested,playing)end
      if not playing and pattern and pattern.update_working_pattern then pattern.update_working_pattern(number,song)end
      changed_channels=changed_channels or{};changed_channels[number]=true
    end
  end
  -- Plan §1.3: a queued apply on a leader rebuilds its followers, so their
  -- predictions follow the new queue; a queued global activation rebuilds the
  -- affected follower itself, which bypasses from queue time (§1.2.3).
  -- (Stopped, update_working_pattern above already propagates.)
  if playing and changed_channels and pattern and pattern.rebuild_followers then
    pattern.rebuild_followers(song,changed_channels)
    if boundary=="pattern"then
      local followers=pattern.followers_of(song)
      for number in pairs(changed_channels)do if followers[number]then pattern.update_working_pattern(number,song)end end
    end
  end
  return true
end


-- The same snapshot with each merge configuration in canonical form (a
-- configuration that cannot be canonicalized is kept so validation rejects it),
-- so a v1 history entry and its stored v2 form compare as equal.
local function canonical_view(snapshot)
  if type(snapshot)~="table"or type(snapshot.channels)~="table"then return snapshot end
  local result={};for key,value in pairs(snapshot)do result[key]=value end;result.channels={}
  for number,channel in pairs(snapshot.channels)do
    if type(channel)=="table"and channel.musical_merge~=nil then
      local c={};for key,value in pairs(channel)do c[key]=value end
      c.musical_merge=merge_config.canonicalize(channel.musical_merge,number)or channel.musical_merge
      result.channels[number]=c
    else result.channels[number]=channel end
  end
  return result
end

function transaction.apply_transition(song,expected,target,playing,boundary,target_validated)
  expected,target=canonical_view(expected),canonical_view(target)
  -- transition_value only reads the live configuration and copies what it returns.
  local live=canonical_view(transaction.view(song))
  local patched=transition_value(live,expected,target)
  return transaction.apply(song,patched,playing,boundary,target_validated and same(patched,target))
end

transaction.copy=copy
return transaction
