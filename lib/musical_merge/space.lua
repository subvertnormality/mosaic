-- MM-12 nominal Space (docs/musical-merge-extensions-plan.md §6, on §1 and §3).
--
-- Nominal planned occupancy, not audible silence (residual MM-12-AUDIBLE,
-- §6.3, stays open). A follower's candidate addition at nominal onset o is
-- removed with SPACE CHnn when some planned leader gate with onset a and
-- reserved extent g (final post-mask length plus strum tail, in leader steps,
-- plus release · d_f) has a <= o < a + g. Gates come from the leader's cycle
-- plans (the same get_and_merge_patterns build, §1.2.3) over the support
-- [j·P_f − G, last follower onset] with G = (L_max + S_max)·d_l + release·d_f
-- computed before enumeration (§1.4), within the shared leader-query budget.
--
-- The result is a record: status "ok" with the blocked playable steps, or a
-- visible bypass that removes nothing: RESYNC / PLAN LIMIT (unsupported: the
-- caller bypasses both filters) or GATE INPUT UNAVAILABLE (Space only). No
-- bypass is evidence of silence.
local common_time = include("mosaic/lib/musical_merge/common_time")
local query = include("mosaic/lib/musical_merge/leader_query")
local space_gate = include("mosaic/lib/musical_merge/space_gate")

local space = {}

space.RESYNC = query.RESYNC
space.PLAN_LIMIT = query.PLAN_LIMIT
space.GATE_INPUT_UNAVAILABLE = space_gate.UNAVAILABLE

local checked_mul, checked_add = query.checked_mul, query.checked_add
local add = common_time.add

-- Whether fraction a exceeds fraction b (denominators positive); nil when the
-- cross products cannot be represented.
local function exceeds(a, b)
  local left, right = checked_mul(a[1], b[2]), checked_mul(b[1], a[2])
  if not left or not right then return nil end
  return left > right
end

function space.reason(leader)
  return string.format("SPACE CH%02d", leader)
end

-- The configured leader and release of an active Foundation configuration, or nil.
function space.settings(config)
  -- v1 keys never had semantics, whatever their names (plan §0).
  if type(config) ~= "table" or config.schema_version ~= 2 or config.mode ~= "foundation" then return nil end
  local value = config.space
  if type(value) ~= "table" or value.leader == nil then return nil end
  return value.leader, value.release or 0
end

local function bypass(leader, release, status)
  return {leader = leader, release = release, status = status, blocked = {}, reason = space.reason(leader)}
end
space.bypass = bypass

-- Every leader cycle's gates count, whatever its configuration: a leader in
-- legacy merge still sounds (§1.5).
local function every_config() return true end

-- ctx: as interlock.admission (song, channel, config, first, last,
-- leader_plan, plan_memo).
function space.admission(ctx)
  local leader, release = space.settings(ctx.config)
  if not leader then return nil end

  local frame, status = query.frame(ctx, leader)
  if not frame then return bypass(leader, release, status) end
  local leader_channel = ctx.song.channels[leader]

  -- §6.1 articulation snapshot of the leader's playable positions: immutable
  -- for this admission, unavailable as a whole when any input is.
  local record = space_gate.snapshot(leader_channel, frame.l_first, frame.l_last)
  if record.status ~= "ok" then return bypass(leader, release, space.GATE_INPUT_UNAVAILABLE) end
  local bound = space_gate.length_bound(ctx.song, leader_channel)
  if not bound then return bypass(leader, release, space.GATE_INPUT_UNAVAILABLE) end

  -- §1.4 G = (L_max + S_max)·d_l + release·d_f, in scale units rounded up.
  local df, dl, pl, start = frame.df, frame.dl, frame.pl, frame.start
  local reach = add(bound, record.s_max)
  local margin = checked_mul(release, df)
  local reach_units = reach and checked_mul(reach[1], dl)
  local g = reach_units and margin and checked_add(-(-reach_units // reach[2]), margin)
  local last_onset = checked_add(start, checked_mul(frame.f_count - 1, df) or math.maxinteger)
  if not g or not last_onset then return bypass(leader, release, space.PLAN_LIMIT) end

  -- Gates with onset a only block o >= a, so the support ends at the last
  -- follower onset; it begins G before the cycle, clipped at the origin.
  local low, high = query.clip(frame, start - g, last_onset)
  local result = {leader = leader, release = release, status = "ok", blocked = {},
    reason = space.reason(leader), gates = 0, cycles = 0, reach = g}
  if high < low then return result end

  local segments, failure = query.segments(frame, low, high, every_config)
  if not segments then return bypass(leader, release, failure) end

  -- Gates per plan key: {position index, extent in leader steps}.
  local l_first, l_count = frame.l_first, frame.l_count
  local derived, gates = {}, {}
  for _, entry in ipairs(segments) do
    local plan = derived[entry.key]
    if plan == nil then
      plan = {}
      local merged = query.plan(ctx, frame, entry)
      if merged then
        for index = 1, l_count do
          local position = l_first + index - 1
          local tail = record.tails[position]
          if merged.trig_values[position] == 1 and tail then
            local length = space_gate.rational_of(merged.lengths[position])
            if not length then return bypass(leader, release, space.GATE_INPUT_UNAVAILABLE) end
            -- Zero or negative lengths contribute no gate.
            if length[1] > 0 then
              -- A length outside the proven L_max table would make the support
              -- an underestimate.
              local above = exceeds(length, bound)
              if above == nil or above then return bypass(leader, release, space.PLAN_LIMIT) end
              local extent = tail[1] == 0 and length or add(length, tail)
              if not extent then return bypass(leader, release, space.PLAN_LIMIT) end
              plan[#plan + 1] = {index = index, extent = extent}
            end
          end
        end
      end
      derived[entry.key] = plan
    end
    local base = checked_mul(entry.i, pl)
    if not base then return bypass(leader, release, space.PLAN_LIMIT) end
    for _, item in ipairs(plan) do
      local onset = base + (item.index - 1) * dl
      if onset >= low and onset <= high then
        local p, q = item.extent[1], item.extent[2]
        local span = checked_mul(p, dl)
        if not span then return bypass(leader, release, space.PLAN_LIMIT) end
        gates[#gates + 1] = {onset = onset, span = span, q = q}
      end
    end
  end
  result.cycles = #segments
  result.gates = #gates

  -- a <= o < a + extent·d_l + release·d_f, i.e. (o − a − margin)·q < p·d_l.
  -- Every extent is at most G, so only gates with a in [o − G, o] can hold o.
  table.sort(gates, function(left, right) return left.onset < right.onset end)
  for index = 1, frame.f_count do
    local onset = start + (index - 1) * df
    local lo, hi = 1, #gates + 1
    while lo < hi do
      local mid = (lo + hi) // 2
      if gates[mid].onset < onset - g then lo = mid + 1 else hi = mid end
    end
    for position = lo, #gates do
      local item = gates[position]
      if item.onset > onset then break end
      local offset = checked_mul(onset - item.onset - margin, item.q)
      if offset == nil then return bypass(leader, release, space.PLAN_LIMIT) end
      if offset < item.span then
        result.blocked[ctx.first + index - 1] = true
        break
      end
    end
  end
  return result
end

return space
