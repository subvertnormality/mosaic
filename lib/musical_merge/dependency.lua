-- One-way leader dependencies (docs/musical-merge-extensions-plan.md §1.5).
--
-- A channel names at most one Interlock leader and one Space leader (possibly
-- the same channel), never itself. A channel that has a leader cannot itself
-- be a leader, which forbids chains and therefore every cycle. Configured
-- edges count whether or not their feature is active. Pure: nothing here reads
-- live state.
local dependency = {}

dependency.LEADER_HAS_LEADER = "LEADER HAS LEADER"
dependency.CHANNEL_IS_A_LEADER = "CHANNEL IS A LEADER"

-- The leaders a configuration names. v1 configurations name none (their keys
-- never had semantics, plan §0).
function dependency.leaders(config)
  if type(config) ~= "table" or config.schema_version ~= 2 then return {} end
  local result = {}
  local first = type(config.interlock) == "table" and config.interlock.leader or nil
  local second = type(config.space) == "table" and config.space.leader or nil
  if first ~= nil then result[#result + 1] = first end
  if second ~= nil and second ~= first then result[#result + 1] = second end
  return result
end

-- Add every edge follower -> leader of `config` for channel `number` to `edges`.
function dependency.add(edges, number, config)
  for _, leader in ipairs(dependency.leaders(config)) do
    edges[#edges + 1] = {number, leader}
  end
  return edges
end

-- Validate a union of edges. `proposed`, when given, is the set of channels
-- whose edges the transaction proposes, and selects the reason: a proposing
-- channel that is itself a leader gets CHANNEL IS A LEADER; a leader that has
-- a leader gets LEADER HAS LEADER. Returns true, or nil, reason, channel.
function dependency.check(edges, proposed)
  local has_leader, is_leader = {}, {}
  for _, edge in ipairs(edges) do
    local follower, leader = edge[1], edge[2]
    if follower == leader then return nil, dependency.LEADER_HAS_LEADER, follower end
    has_leader[follower] = true
    is_leader[leader] = true
  end
  proposed = proposed or {}
  for number = 1, 16 do
    if proposed[number] and has_leader[number] and is_leader[number] then
      return nil, dependency.CHANNEL_IS_A_LEADER, number
    end
  end
  for number = 1, 16 do
    if has_leader[number] and is_leader[number] then
      return nil, dependency.LEADER_HAS_LEADER, number
    end
  end
  return true
end

return dependency
