-- Own future arp onsets and their terminating release list.
-- Cancelling onsets alone must not suppress releases owed by sounding voices.
local arp_lifetime = {}

function arp_lifetime.new(get_clock, program, get_lattice, get_shuffle_values, chord_timing)
  local arps = {}
  local arp_sprockets = {[0] = {}}
  for i = 1, 16 do arp_sprockets[i] = {} end
  function arps.destroy_all()
    for _, sprocket_table in ipairs(arp_sprockets) do
      for j = #sprocket_table, 1, -1 do
        local sprocket = sprocket_table[j]
        if sprocket then
          sprocket:destroy()
          table.remove(sprocket_table, j)
        end
      end
    end
  end

  -- Cancel only future arp onsets; already sounding voices retain their releases.
  function arps.cancel_onsets(c)
    if arp_sprockets[c] then
      for _, sprocket in ipairs(arp_sprockets[c]) do sprocket:destroy() end
    end
    arp_sprockets[c] = {}
  end

  function arps.start(c, division, chord_spread, chord_acceleration, length, func, release_ids)
    if division == 0 or division == nil then return end
    local first_gap = chord_timing.gap(division, chord_spread, chord_acceleration, 1)
    if not first_gap then return end
    local channel = program.get_channel(program.get().selected_song_pattern, c)

    get_clock().cancel_arp_onsets(c)

    local arp
    local first_onset = true
    local next_interval = 2
    local following_gap = first_gap
    local stop_after_onset = false
    release_ids = release_ids or {}

    local function stop_onsets()
      local finished = arp
      if finished then finished:destroy();arp = nil end
      for i = #arp_sprockets[c], 1, -1 do
        if arp_sprockets[c][i] == finished then table.remove(arp_sprockets[c], i) end
      end
    end

    local function finish_arp()
      stop_onsets()
      local parent = get_clock()["channel_" .. c .. "_clock"]
      for i = #release_ids, 1, -1 do
        local id = release_ids[i]
        release_ids[i] = nil
        local pending = parent.delayed_actions[id]
        if pending then
          parent.delayed_actions[id] = nil
          parent:run_pending_action(pending)
          if parent.cleanup_delayed_action then parent.cleanup_delayed_action(id) end
        end
      end
    end

    local shuffle_values = get_shuffle_values(channel)
    arp = get_lattice():new_sprocket {
      action = function()
        if first_onset then
          -- Startup waited through interval1. Begin interval2 exactly once,
          -- retaining its rounding carry and alternating swing step.
          first_onset = false
          arp.phase = arp.current_ppqn + 1
          arp:finish_cycle()
          arp:begin_cycle()
        end
        local parent = get_clock()["channel_" .. c .. "_clock"]
        local onset_offset = (parent.phase - 2) / parent.current_ppqn
        func(following_gap or 0, onset_offset)
        -- This onset completed a positive gap. A nonpositive FOLLOWING gap
        -- cancels future onsets only; existing voices keep their releases.
        if length == 0 then finish_arp()
        elseif stop_after_onset then stop_onsets() end
      end,
      division = first_gap * get_clock()["channel_" .. c .. "_clock"].division,
      division_for_cycle = function()
        following_gap = chord_timing.gap(division, chord_spread, chord_acceleration, next_interval)
        next_interval = next_interval + 1
        if not following_gap then
          stop_after_onset = true
          return arp.division -- Valid current onset still executes, then stops.
        end
        return following_gap * get_clock()["channel_" .. c .. "_clock"].division
      end,
      enabled = true,
      swing = shuffle_values.swing,
      swing_or_shuffle = shuffle_values.swing_or_shuffle,
      shuffle_basis = shuffle_values.shuffle_basis,
      shuffle_feel = shuffle_values.shuffle_feel,
      shuffle_amount = shuffle_values.shuffle_amount,
      delay = 1,
      delay_offset = -1, -- Created inside order2; first processed next pulse.
      realign = false,
      order = 2,
      step = get_clock()["channel_" .. c .. "_clock"]:get_step()
    }
    arp.shuffle_updated = true -- Constructor already rounded the startup gap.
    get_clock().delay_action(c, length, "must_execute", finish_arp)
    table.insert(arp_sprockets[c], arp)
  end

  function arps.reset_channel(c) arp_sprockets[c] = {} end
  return arps
end

return arp_lifetime
