-- Interlock device-timing workload (docs/musical-merge-extensions-plan.md section 1.4
-- "Device acceptance"). One chunk, sent once over Maiden by
-- merge_workloads.py and also executed by the host Lua suite
-- (lib/tests/lib/merge_device_workload_tests.lua), so the configuration the
-- device plays and the admission semantics the host proves are the same code.
--
-- Defines the global _MOSAIC_MERGE_WORKLOAD with:
--   configure(variant, mode)  variant STEADY | WORST | DENSE (EDIT and
--       DENSE-EDIT play WORST and DENSE); mode "enabled" or "off" (Merge Shape
--       Off: the same patterns, ranges and clock mods with no merge
--       configuration). Applied while stopped through the production modules:
--       pattern data, channel ranges, m_clock.set_channel_division and the
--       optional-configuration transaction. Returns a one-line readback.
--   install(leader_pattern)  admission and
--       input recorder: every Foundation build of channels 1..16 (the record
--       working_pattern.foundation.interlock publishes, reduced to counts),
--       and every grid key edge with its native util.time() stamp and the
--       leader's anchor trig as it stands once Mosaic has handled the edge.
--       Mosaic applies a tap on its release (m_grid short press), so a trig
--       edit shows on the key-up row, not the key-down row.
--   reset(), dump(first, last), count(), remove()
--
-- Pattern slots: 1 is the PERF-002 dense pattern (a trig on steps 1..16),
-- left untouched. The workload writes slots 3, 5, 6, 7 and 8.
-- ASCII only: the chunk travels as a Lua string literal.

local W = {}

local LEADER = 1
W.LEADER_PATTERN = 3

local function song()
  return program.get_song_pattern(program.get().selected_song_pattern)
end

local function set_pattern(target, number, steps)
  local value = target.patterns[number]
  for s = 1, 64 do value.trig_values[s] = 0; value.lengths[s] = 1 end
  for _, s in ipairs(steps) do value.trig_values[s] = 1; value.note_values[s] = 0; value.velocity_values[s] = 100 end
end

local function range(from, to)
  local result = {}
  for s = from, to do result[#result + 1] = s end
  return result
end

local function odd(from, to)
  local result = {}
  for s = from, to, 2 do result[#result + 1] = s end
  return result
end

local MODS = {
  ["/1"] = {name = "/1", value = 1, type = "clock_division"},
  ["/4"] = {name = "/4", value = 4, type = "clock_division"},
  ["x16"] = {name = "x16", value = 16, type = "clock_multiplication"},
}

local function set_channel(target, number, patterns, first, last, mod)
  local channel = target.channels[number]
  channel.selected_patterns = {}
  for _, p in ipairs(patterns) do channel.selected_patterns[p] = true end
  channel.start_trig = {(first - 1) % 16 + 1, 4 + (first - 1) // 16}
  channel.end_trig = {(last - 1) % 16 + 1, 4 + (last - 1) // 16}
  local mods = {}
  for key, value in pairs(MODS[mod]) do mods[key] = value end
  channel.clock_mods = mods
  m_clock.set_channel_division(number, m_clock.calculate_divisor(mods))
end

local function foundation(anchor, leader, window)
  local value = include("mosaic/lib/musical_merge/config").new()
  value.mode, value.anchor, value.amount, value.accent, value.gap = "foundation", anchor, 100, 70, 0
  if leader then value.interlock = {leader = leader, window = window} end
  return value
end

-- {patterns = {slot = steps}, channels = {number = {patterns, first, last, mod, merge}}}
local function plan(variant)
  if variant == "STEADY" then
    -- The leader's anchor pattern is W.LEADER_PATTERN in every variant: the
    -- recorder's leader_trig reads that pattern's step 1.
    return {patterns = {[W.LEADER_PATTERN] = {1, 5, 9, 13}, [6] = {1, 9}},
      channels = {[1] = {{W.LEADER_PATTERN, 1}, 1, 16, "/1", foundation(W.LEADER_PATTERN)},
        [2] = {{6, 1}, 1, 16, "/1", foundation(6, LEADER, 1)}}}
  end
  local result = {channels = {}}
  if variant == "WORST" then
    result.patterns = {[W.LEADER_PATTERN] = {1}, [7] = {1}, [8] = odd(1, 63)}
    result.channels[1] = {{W.LEADER_PATTERN}, 1, 1, "/1", foundation(W.LEADER_PATTERN)}
    for number = 2, 16 do result.channels[number] = {{7, 8}, 1, 64, "/1", foundation(7, LEADER, 0)} end
  elseif variant == "DENSE" then
    result.patterns = {[W.LEADER_PATTERN] = range(1, 64), [7] = {}, [8] = range(1, 64)}
    result.channels[1] = {{W.LEADER_PATTERN}, 1, 64, "x16", foundation(W.LEADER_PATTERN)}
    for number = 2, 16 do result.channels[number] = {{7, 8}, 1, 64, "/4", foundation(7, LEADER, 0)} end
  else
    error("unknown merge workload variant " .. tostring(variant))
  end
  return result
end

function W.configure(variant, mode)
  assert(mode == "enabled" or mode == "off", "mode")
  assert(not m_clock.is_playing(), "configure while stopped")
  local target = song()
  local value = plan(variant)
  target.global_pattern_length = 64
  for number, steps in pairs(value.patterns) do set_pattern(target, number, steps) end
  for number, channel in pairs(value.channels) do
    set_channel(target, number, channel[1], channel[2], channel[3], channel[4])
  end
  local transaction = include("mosaic/lib/optional_config_transaction")
  local snapshot = transaction.snapshot(target)
  for number = 1, 16 do
    local channel = value.channels[number]
    snapshot.channels[number].musical_merge = mode == "enabled" and channel and channel[5] or nil
  end
  assert(transaction.apply(target, snapshot, false, "channel"))
  pattern.update_working_patterns(target)
  local parts = {}
  for number = 1, 16 do
    local merge = target.channels[number].musical_merge
    parts[#parts + 1] = number .. ":" .. (merge and (merge.mode .. "/" .. tostring(merge.anchor) .. "/" ..
      tostring(merge.interlock.leader) .. "/" .. merge.interlock.window) or "none") .. "/" ..
      target.channels[number].clock_mods.name
  end
  return "__MERGE_CONFIG__" .. variant .. "|" .. mode .. "|" .. table.concat(parts, ";")
end

------------------------------------------------------------------------------
-- Recorder. Rows are flat arrays of numbers so recording allocates one small
-- table per build; the dump prints them after the window.

-- util.time() on the norns (the MIDI trace's clock); os.clock() on a host
-- harness without the norns runtime.
local function now()
  if util and util.time then
    local ok, value = pcall(util.time)
    if ok then return value end
  end
  return os.clock()
end

local function registry_k(number)
  local registry = rawget(_G, "__mosaic_merge_timeline")
  local record = registry and registry.channels and registry.channels[number]
  return record and record.k or -99
end

local function transport_pulse()
  local lattice = m_clock.get_clock_lattice and m_clock.get_clock_lattice()
  return type(lattice) == "table" and lattice.transport or -1
end

local STATUS = {ok = 1, RESYNC = 2, ["PLAN LIMIT"] = 3, ["LEADER OFF"] = 4, ["LEADER MISSING"] = 5}

-- Row kinds: 1 build, 2 grid key-down, 3 grid key-up.
-- build: {1, time, pulse, channel, k, status, cycles, anchors, plan_builds,
--         eligible, admitted, candidates, interlock_removed, other_reasons,
--         leader_trig}  (status 0: no Interlock record)
-- key:   {2 or 3, time, pulse, x, y, leader_trig, k2 .. k16}; time, pulse
--        and the row's position are the edge's arrival (before the builds it
--        causes); leader_trig and k are read after Mosaic handled it.
function W.install(leader_pattern)
  if rawget(_G, "_MOSAIC_MERGE_REC") then error("merge recorder already installed") end
  local R = {rows = {}, n = 0, limit = 20000, originals = {}, leader_pattern = leader_pattern or W.LEADER_PATTERN}
  local function leader_trig()
    local value = song().patterns[R.leader_pattern].trig_values[1]
    return value == 1 and 1 or 0
  end
  local merge = pattern.get_and_merge_patterns
  R.originals[#R.originals + 1] = {pattern, "get_and_merge_patterns", merge}
  pattern.get_and_merge_patterns = function(c, ...)
    local result = merge(c, ...)
    local f = result and result.foundation
    if f and R.n < R.limit then
      local i = f.interlock
      local candidates, removed, other = 0, 0, 0
      local reason = i and i.reason
      for s = 1, 64 do
        local sources = f.sources and f.sources[s]
        if sources and f.roles[s] ~= "anchor" then
          candidates = candidates + 1
          local list = f.reason_lists and f.reason_lists[s]
          local hit = false
          if list then for _, r in ipairs(list) do if r == reason then hit = true end end end
          if hit then removed = removed + 1 elseif f.reasons[s] then other = other + 1 end
        end
      end
      R.n = R.n + 1
      R.rows[R.n] = {1, now(), transport_pulse(), c, registry_k(c), i and (STATUS[i.status] or 9) or 0,
        i and i.cycles or -1, i and i.anchors or -1, i and i.plan_builds or -1,
        f.eligible_count or -1, f.admitted_count or -1, candidates, removed, other, leader_trig()}
    end
    return result
  end
  local grid_table = rawget(_G, "_norns") and _norns.grid
  if grid_table and type(grid_table.key) == "function" then
    local key = grid_table.key
    R.originals[#R.originals + 1] = {grid_table, "key", key}
    grid_table.key = function(id, x, y, z, ...)
      local stamp = now()
      -- The edge takes its place in the row order on arrival, before the
      -- builds it causes (a tap rebuilds the leader's followers inside the
      -- key handler); its leader trig and counters are then read after it.
      local row
      if (z == 1 or z == 0) and R.n < R.limit then
        row = {z == 1 and 2 or 3, stamp, transport_pulse(), x, y, leader_trig()}
        for c = 2, 16 do row[#row + 1] = registry_k(c) end
        R.n = R.n + 1
        R.rows[R.n] = row
      end
      local results = table.pack(key(id, x, y, z, ...))
      if row then
        row[6] = leader_trig()
        for c = 2, 16 do row[5 + c] = registry_k(c) end
      end
      return table.unpack(results, 1, results.n)
    end
  end
  rawset(_G, "_MOSAIC_MERGE_REC", R)
  return "__MERGE_REC_INSTALLED__" .. #R.originals
end

function W.reset()
  local R = rawget(_G, "_MOSAIC_MERGE_REC")
  R.rows, R.n = {}, 0
  return "__MERGE_REC_RESET__"
end

function W.count()
  return "__MERGE_REC_COUNT__" .. rawget(_G, "_MOSAIC_MERGE_REC").n
end

function W.dump(first, last)
  local R = rawget(_G, "_MOSAIC_MERGE_REC")
  local lines = {}
  for index = first, math.min(last, R.n) do
    local row = R.rows[index]
    local parts = {}
    for j, value in ipairs(row) do
      parts[j] = (j == 2) and string.format("%.9f", value) or tostring(value)
    end
    lines[#lines + 1] = "__MERGE_ROW__" .. index .. "|" .. table.concat(parts, ",")
  end
  return table.concat(lines, "\n")
end

function W.rows()
  return rawget(_G, "_MOSAIC_MERGE_REC").rows
end

function W.remove()
  local R = rawget(_G, "_MOSAIC_MERGE_REC")
  if R then
    for index = #R.originals, 1, -1 do
      local entry = R.originals[index]
      entry[1][entry[2]] = entry[3]
    end
    rawset(_G, "_MOSAIC_MERGE_REC", nil)
  end
  return "__MERGE_REC_REMOVED__"
end

_MOSAIC_MERGE_WORKLOAD = W
return W
