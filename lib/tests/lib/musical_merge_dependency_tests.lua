-- One-way leader dependencies (MM-09). Contract:
-- docs/musical-merge-extensions-plan.md §1.5. README "Merge Shape" still
-- defers Interlock and Space to MM-11, so every assertion is a
-- characterisation of that approved plan, outside the current manual.

local merge_config = include("mosaic/lib/musical_merge/config")
local merge_state = include("mosaic/lib/musical_merge/state")
local merge_timeline = include("mosaic/lib/musical_merge/timeline")
local dependency = include("mosaic/lib/musical_merge/dependency")
local transaction = include("mosaic/lib/optional_config_transaction")
local validation = include("mosaic/lib/project_validation")
local pattern_module = include("mosaic/lib/pattern")

local function follower(interlock_leader, space_leader)
  local value = merge_config.new()
  value.mode, value.anchor = "foundation", 1
  value.interlock = {leader = interlock_leader, window = 0}
  value.space = {leader = space_leader, release = 0}
  return value
end

local function edges(graph)
  local result = {}
  for number, config in pairs(graph) do dependency.add(result, number, config) end
  return result
end

function test_dependency_check_accepts_one_way_graphs_and_rejects_chains()
  luaunit.assert_true(dependency.check(edges({[1] = follower(2), [3] = follower(2, 2), [4] = follower(nil, 5)})))
  luaunit.assert_equals({dependency.check(edges({[1] = follower(2), [2] = follower(3)}))},
    {nil, "LEADER HAS LEADER", 2})
  -- The proposing channel that is itself a leader.
  luaunit.assert_equals({dependency.check(edges({[1] = follower(2), [2] = follower(3)}), {[2] = true})},
    {nil, "CHANNEL IS A LEADER", 2})
  -- Both features count; configured edges count while their feature is inactive.
  local inactive = follower(nil, 3); inactive.mode = "off"
  luaunit.assert_equals({dependency.check(edges({[1] = follower(2), [2] = inactive}))}, {nil, "LEADER HAS LEADER", 2})
  luaunit.assert_equals({dependency.check(edges({[5] = follower(nil, 6), [6] = follower(5)}))},
    {nil, "LEADER HAS LEADER", 5})
  luaunit.assert_equals({dependency.check({{4, 4}})}, {nil, "LEADER HAS LEADER", 4})
  -- v1 keys never had semantics.
  luaunit.assert_equals(dependency.leaders({schema_version = 1, interlock = {leader = 2}}), {})
end

-- Channel 1 is slow (16 steps /2), channel 2 fast (3 steps), channel 3 medium
-- (5 steps). Global length 64 so no pattern boundary interferes.
local function setup()
  program.init(); globals.reset(); params.reset(); memory.init()
  merge_state.reset(); merge_timeline.stop()
  program.set_selected_song_pattern(1)
  local song = program.get_song_pattern(1)
  for _, step in ipairs({1, 5, 9}) do song.patterns[1].trig_values[step] = 1 end
  for number = 1, 4 do song.channels[number].selected_patterns = {[1] = true} end
  song.channels[1].clock_mods = {name = "/2", value = 2, type = "clock_division"}
  song.channels[1].end_trig = {16, 4}
  song.channels[2].end_trig = {3, 4}
  song.channels[3].end_trig = {5, 4}
  song.channels[1].musical_merge = follower(2)
  pattern_module.update_working_patterns(song)
  return song
end

local function with(song, changes)
  local snapshot = transaction.snapshot(song)
  for number, value in pairs(changes) do snapshot.channels[number].musical_merge = value or nil end
  return snapshot
end

local function pulses(count)
  for _ = 1, count do m_clock.get_clock_lattice():pulse() end
end

local function stop_transport()
  local saved_nb, saved_handler, saved_stop = rawget(_G, "nb"), rawget(_G, "norns_param_state_handler"), m_midi.stop
  rawset(_G, "nb", {stop_all = function() end})
  rawset(_G, "norns_param_state_handler", include("mosaic/lib/devices/norns_param_state_handler"))
  m_midi.stop = function() end
  local ok, err = pcall(function() m_clock:stop() end)
  rawset(_G, "nb", saved_nb); rawset(_G, "norns_param_state_handler", saved_handler); m_midi.stop = saved_stop
  if not ok then error(err, 0) end
end

-- Every intermediate active graph satisfies the one-way invariant.
local function assert_active_graph_one_way(song, label)
  local active = {}
  for number = 1, 16 do
    local record = merge_state.peek(song, number)
    active[number] = record and record.active or song.channels[number].musical_merge
  end
  luaunit.assert_true(dependency.check(edges(active)), label)
end

-- Stopped transactions validate the resulting snapshot atomically: a swap of
-- roles in one transaction is valid.
function test_dependency_stopped_transaction_validates_the_resulting_snapshot()
  local song = setup()
  luaunit.assert_true(transaction.validate(song, with(song, {[1] = merge_config.new(), [2] = follower(1)}), false))
  luaunit.assert_equals({transaction.validate(song, with(song, {[2] = follower(3)}), false)},
    {nil, "CHANNEL IS A LEADER"})
  luaunit.assert_equals({transaction.validate(song, with(song, {[3] = follower(1)}), false)},
    {nil, "LEADER HAS LEADER"})
  luaunit.assert_equals({transaction.validate(song, with(song, {[3] = follower(nil, 1)}), false)},
    {nil, "LEADER HAS LEADER"})
  luaunit.assert_true(transaction.apply(song, with(song, {[1] = merge_config.new(), [2] = follower(1)}), false))
  luaunit.assert_equals(song.channels[2].musical_merge.interlock.leader, 1)
end

-- While playing: the union of active, requested, queued and proposed edges.
-- A queued removal on the slow channel does not free its former leader to
-- become a follower until the removal has activated; the fast channel's
-- addition is rejected, then accepted after that boundary.
function test_dependency_playing_slow_removal_then_fast_addition_uses_the_edge_union()
  local song = setup()
  m_clock.init(); m_clock:start()
  luaunit.assert_true(transaction.apply(song, with(song, {[1] = merge_config.new()}), true, "channel"))
  luaunit.assert_equals(merge_state.peek(song, 1).active.interlock.leader, 2)
  -- The swapped roles are rejected as a whole, deleting nobody's edge.
  local swap = with(song, {[2] = follower(1)})
  luaunit.assert_equals({transaction.apply(song, swap, true, "channel")}, {nil, "CHANNEL IS A LEADER"})
  luaunit.assert_nil(song.channels[2].musical_merge)
  local addition = with(song, {[2] = follower(3)})
  luaunit.assert_equals({transaction.apply(song, addition, true, "channel")}, {nil, "CHANNEL IS A LEADER"})
  -- Stopped validation of the same snapshot would accept it.
  luaunit.assert_true(transaction.validate(song, addition, false))
  local activated = false
  for _ = 1, 24 * 40 do
    pulses(1)
    assert_active_graph_one_way(song, "pulse")
    if merge_state.peek(song, 1).active.interlock.leader == nil then activated = true; break end
    luaunit.assert_equals({transaction.validate(song, addition, true)}, {nil, "CHANNEL IS A LEADER"})
  end
  luaunit.assert_true(activated)
  luaunit.assert_true(transaction.apply(song, with(song, {[2] = follower(3)}), true, "channel"))
  for _ = 1, 24 * 8 do pulses(1); assert_active_graph_one_way(song, "after") end
  luaunit.assert_equals(merge_state.peek(song, 2).active.interlock.leader, 3)
  stop_transport()
end

-- A queued edge counts: channel 3 queued to follow 4 blocks 4 following 5,
-- and a queued replacement that removes the edge keeps blocking until it lands.
function test_dependency_queued_edges_and_queued_replacement_count()
  local song = setup()
  m_clock.init(); m_clock:start()
  luaunit.assert_true(transaction.apply(song, with(song, {[3] = follower(nil, 4)}), true, "channel"))
  luaunit.assert_equals({transaction.apply(song, with(song, {[4] = follower(5)}), true, "channel")},
    {nil, "CHANNEL IS A LEADER"})
  -- Replace the queue before it lands: the requested and queued edges are
  -- gone, but the replacement has not activated; no active edge 3 -> 4 ever
  -- existed, so the union is clear once the queue is replaced.
  luaunit.assert_true(transaction.apply(song, with(song, {[3] = merge_config.new()}), true, "channel"))
  luaunit.assert_true(transaction.validate(song, with(song, {[4] = follower(5)}), true))
  -- A global (pattern-boundary) queue counts as well.
  luaunit.assert_true(transaction.apply(song, with(song, {[6] = follower(7)}), true, "pattern"))
  luaunit.assert_equals({transaction.validate(song, with(song, {[7] = follower(8)}), true)},
    {nil, "CHANNEL IS A LEADER"})
  stop_transport()
  -- Stop settles the requested snapshot; stopped validation uses it alone.
  luaunit.assert_true(transaction.validate(song, with(song, {[6] = merge_config.new(), [7] = follower(8)}), false))
end

-- Undo and redo restore through the same validation, including history
-- restoration while playing.
function test_dependency_undo_and_redo_are_validated_against_the_union()
  local song = setup()
  local slot = program.get().selected_song_pattern
  m_clock.init(); m_clock:start()
  local before = transaction.snapshot(song)
  local removed = with(song, {[1] = merge_config.new()})
  luaunit.assert_true(memory.record_optional_config(slot, {1}, before, removed, "channel"))
  -- Recording while the removal is queued rejects the dependent addition.
  local addition = with(song, {[2] = follower(3)})
  luaunit.assert_equals({memory.record_optional_config(slot, {2}, removed, addition, "channel")},
    {nil, "CHANNEL IS A LEADER"})
  for _ = 1, 24 * 40 do pulses(1) end
  luaunit.assert_nil(merge_state.peek(song, 1).active.interlock.leader)
  luaunit.assert_true(memory.record_optional_config(slot, {2}, removed, addition, "channel"))
  for _ = 1, 24 * 8 do pulses(1) end
  luaunit.assert_equals(merge_state.peek(song, 2).active.interlock.leader, 3)
  -- Undoing the removal would make 1 follow 2 while 2 follows 3: refused.
  luaunit.assert_false(memory.undo(1) == true)
  luaunit.assert_nil(song.channels[1].musical_merge.interlock.leader)
  -- Undo the addition (queued), then the removal is still refused until the
  -- addition's undo has activated.
  luaunit.assert_true(memory.undo(2))
  luaunit.assert_false(memory.undo(1) == true)
  for _ = 1, 24 * 8 do pulses(1); assert_active_graph_one_way(song, "undo") end
  luaunit.assert_nil(merge_state.peek(song, 2).active.interlock.leader)
  luaunit.assert_true(memory.undo(1))
  luaunit.assert_equals(song.channels[1].musical_merge.interlock.leader, 2)
  for _ = 1, 24 * 40 do pulses(1); assert_active_graph_one_way(song, "undo landed") end
  luaunit.assert_equals(merge_state.peek(song, 1).active.interlock.leader, 2)
  -- Redo of the removal queues it; redo of the addition is refused while the
  -- active 1 -> 2 edge remains, then accepted once the removal has landed.
  luaunit.assert_true(memory.redo(1))
  luaunit.assert_false(memory.redo(2) == true)
  for _ = 1, 24 * 40 do pulses(1); assert_active_graph_one_way(song, "redo") end
  luaunit.assert_nil(merge_state.peek(song, 1).active.interlock.leader)
  luaunit.assert_true(memory.redo(2))
  luaunit.assert_equals(song.channels[2].musical_merge.interlock.leader, 3)
  stop_transport()
end

-- Project validation rejects a loaded slot containing a chain.
function test_dependency_project_validation_rejects_chains()
  local channels = {}
  for number = 1, 17 do channels[number] = {start_trig = {1, 4}, end_trig = {16, 4}} end
  local saved = {"fixture", {song_patterns = {[1] = {global_pattern_length = 64, channels = channels}}}}
  channels[1].musical_merge = follower(2)
  channels[3].musical_merge = follower(nil, 2)
  luaunit.assert_true(validation.check(saved))
  channels[2].musical_merge = follower(nil, 4)
  luaunit.assert_equals({validation.check(saved)}, {nil, "Slot 1 ch 2 LEADER HAS LEADER"})
  channels[2].musical_merge = nil
  channels[5].musical_merge = follower(1)
  luaunit.assert_equals({validation.check(saved)}, {nil, "Slot 1 ch 1 LEADER HAS LEADER"})
  -- A v1 configuration with a colliding key has no edge.
  channels[5].musical_merge = {schema_version = 1, mode = "off", amount = 100, accent = 70, gap = 0, seed = 0,
    ranking_version = 1, cycles = 1, shape = "flat", percentages = {100}, variation = "fixed",
    keep_anchor_pitch = false, target = {kind = "legacy"}, interlock = {leader = 1, window = 0}}
  luaunit.assert_true(validation.check(saved))
end

-- Boundary activation verifies the invariant before mutation; an unexpected
-- violation retains the previous active snapshot with the rejection reason.
function test_dependency_boundary_activation_retains_active_on_violation()
  local song = setup()
  merge_state.effective(song, 2, merge_config.new())
  merge_state.request(song, 2, follower(3), true)
  merge_state.on_cycle_boundary(song, 2, song.channels[2].musical_merge or merge_config.new())
  local record = merge_state.peek(song, 2)
  luaunit.assert_equals(record.rejected, "CHANNEL IS A LEADER")
  luaunit.assert_nil(record.active.interlock.leader)
  assert_active_graph_one_way(song, "retained")
  merge_state.request_global(song, 2, follower(3), true)
  merge_state.on_pattern_boundary(song)
  luaunit.assert_equals(merge_state.peek(song, 2).rejected, "CHANNEL IS A LEADER")
  luaunit.assert_nil(merge_state.peek(song, 2).active.interlock.leader)
  -- Once the other edge is gone, the retained queue lands.
  merge_state.request(song, 1, merge_config.new(), false)
  merge_state.on_pattern_boundary(song)
  luaunit.assert_equals(merge_state.peek(song, 2).active.interlock.leader, 3)
  luaunit.assert_nil(merge_state.peek(song, 2).rejected)
end
