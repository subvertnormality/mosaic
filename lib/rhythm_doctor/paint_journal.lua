-- Session-only bounded source-paint journal. Pattern mutation remains owned by
-- the caller: prepare yields a snapshot; complete records the resulting source
-- revision. One stream revision governs multi-step undo/redo safely.
local Journal = {}
local function copy(v) if type(v) ~= "table" then return v end local o = {}; for k, x in pairs(v) do o[k] = copy(x) end; return o end
local function valid_target(t) return type(t) == "table" and t.project_id ~= nil and t.song_slot ~= nil and t.pattern_id ~= nil end
local function key(t) return table.concat({ t.project_id, t.song_slot, t.pattern_id }, "\31") end
local function stream_for(j, t) return j.targets[key(t)] end
function Journal.new(limit)
  limit = limit or 32; assert(type(limit) == "number" and limit > 0 and math.floor(limit) == limit, "positive integer limit required")
  return { limit = limit, targets = {}, generation = 0 }
end
local function advance(journal, stream)
  journal.generation = journal.generation + 1
  stream.nonce = journal.generation
end
local function enforce_bound(journal, current_id)
  local total = 0
  for _, stream in pairs(journal.targets) do total = total + #stream.entries end
  while total > journal.limit do
    local oldest_id, oldest
    for id, stream in pairs(journal.targets) do
      if id ~= current_id and (not oldest or stream.nonce < oldest.nonce) then
        oldest_id, oldest = id, stream
      end
    end
    if not oldest then break end -- the current stream already has its own cap
    total = total - #oldest.entries
    journal.targets[oldest_id] = nil
  end
end
function Journal.record(journal, target, before, after, resulting_revision, previous_revision)
  if type(journal) ~= "table" or not valid_target(target) or type(resulting_revision) ~= "number" or type(previous_revision) ~= "number" then return nil, { code = "INVALID_JOURNAL_ENTRY" } end
  local id, stream = key(target), stream_for(journal, target) or { entries = {}, cursor = 0, nonce = 0 }
  -- New paint after an ordinary edit begins a fresh history. Keeping older
  -- entries would let a later second Undo overwrite that intervening edit.
  if stream.expected_revision and stream.expected_revision ~= previous_revision then
    stream.entries, stream.cursor = {}, 0
  end
  journal.targets[id] = stream
  while #stream.entries > stream.cursor do table.remove(stream.entries) end
  stream.entries[#stream.entries + 1] = { before = copy(before), after = copy(after) }
  if #stream.entries > journal.limit then table.remove(stream.entries, 1) else stream.cursor = stream.cursor + 1 end
  stream.cursor, stream.expected_revision = #stream.entries, resulting_revision
  advance(journal, stream)
  enforce_bound(journal, id)
  return true
end
local function prepared(stream, operation, target, index, snapshot)
  return { operation = operation, target = copy(target), index = index, nonce = stream.nonce, snapshot = copy(snapshot) }
end
function Journal.prepare_undo(journal, target, current_revision)
  if type(journal) ~= "table" or not valid_target(target) then return { code = "NO_UNDO" } end
  local stream = stream_for(journal, target)
  if not stream or stream.cursor == 0 then return { code = "NO_UNDO" } end
  if stream.expected_revision ~= current_revision then return { code = "PATTERN_CHANGED" } end
  return prepared(stream, "undo", target, stream.cursor, stream.entries[stream.cursor].before)
end
function Journal.complete_undo(journal, token, resulting_revision)
  local stream = type(token) == "table" and valid_target(token.target) and stream_for(journal, token.target)
  if not stream or token.operation ~= "undo" or stream.cursor ~= token.index or stream.nonce ~= token.nonce then return nil, { code = "STALE_JOURNAL" } end
  stream.cursor, stream.expected_revision = stream.cursor - 1, resulting_revision; advance(journal, stream); return true
end
function Journal.prepare_redo(journal, target, current_revision)
  if type(journal) ~= "table" or not valid_target(target) then return { code = "NO_REDO" } end
  local stream = stream_for(journal, target)
  if not stream or stream.cursor >= #stream.entries then return { code = "NO_REDO" } end
  if stream.expected_revision ~= current_revision then return { code = "PATTERN_CHANGED" } end
  local index = stream.cursor + 1; return prepared(stream, "redo", target, index, stream.entries[index].after)
end
function Journal.complete_redo(journal, token, resulting_revision)
  local stream = type(token) == "table" and valid_target(token.target) and stream_for(journal, token.target)
  if not stream or token.operation ~= "redo" or stream.cursor + 1 ~= token.index or stream.nonce ~= token.nonce then return nil, { code = "STALE_JOURNAL" } end
  stream.cursor, stream.expected_revision = token.index, resulting_revision; advance(journal, stream); return true
end
return Journal
