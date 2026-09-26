-- UI02 adapter for provider `harmony` (Harmony feature editor).
--
-- owners: channel_edit_page_ui.adapter_owners(); uses owners.feature_editors.harmony,
-- the lib/pages/channel_edit_page/channel_feature_editor.lua instance the
-- Channel page already drives. Routes are OLD owner routes (H01..H10,
-- H04_DELETE -> H17, TONE_MAP -> H11, TONE_MAP_RESET -> H19;
-- source_route_map.harmony). Commit boundary: global_pattern_boundary
-- (editor:apply(); while playing the owner reports NEXT PATTERN).
-- Confirmations H17/H19 stay in the owner: `confirm_delete` / `confirm_reset`
-- invoke the owner's closures through key(3); cancel is the owner's K2 path.
-- Visual variants M10, H12..H16 and H18 are described only from snapshot:<id>.

local shared = include("mosaic/lib/ui_adapters/feature_editor")
local config_state = include("mosaic/lib/harmony/config_state")
local harmony_inspection = include("mosaic/lib/harmony/inspection")

local format, field = shared.format, shared.field

local function stage(name, key)
  return function(s) local value = s.trace[name]; return format(value and value[key]) end
end
local function planned_status(status)
  return function(s) return format(s.trace.planned ~= nil and s.trace.planned.status == status) end
end
local function mode_of(record) return record and format(record.mode) or "NONE" end

local variants = {
  M10 = {
    {id = "mode", label = "Mode", read = field("H01", "mode")},
    {id = "tone_map", label = "Tone Map", read = field("H01", "tone_map")},
    {id = "register", label = "Register", read = field("H01", "register")},
    {id = "result", label = "Result", read = field("H01", "result")}
  },
  -- The owner keeps no movement frames; these rows are unavailable.
  H12 = {
    {id = "frame_a", label = "Frame A", read = function() end},
    {id = "frame_b", label = "Frame B", read = function() end},
    {id = "common_tone", label = "Common tone", read = function() end},
    {id = "repeated_b", label = "Repeated B", read = function() end}
  },
  H13 = {
    {id = "identity", label = "Identity", read = field("H03", "mode")},
    {id = "register", label = "Register", read = function() end},
    {id = "direction", label = "Direction", read = field("H03", "direction")},
    {id = "strict", label = "Strict", read = field("H03", "strict_direction")}
  },
  H14 = {
    {id = "active_mode", label = "Active mode", read = function(s) return mode_of(s.channel_status.active) end},
    {id = "queued", label = "Queued", read = function(s) return mode_of(s.channel_status.queued) end},
    {id = "changed", label = "Changed", read = function(s) return format(s.channel_status.queued ~= nil or s.song_status.queued ~= nil) end},
    {id = "sources_unchanged", label = "Sources unchanged", read = function() return "" end}
  },
  H15 = {
    {id = "step", label = "Step", read = function(s) return format(s.selected_step) end},
    {id = "status", label = "Status", read = field("H05", "status")},
    {id = "planned", label = "Planned", read = stage("planned", "output")},
    {id = "scheduled", label = "Scheduled", read = stage("scheduled", "pitch")},
    {id = "emitted", label = "Emitted", read = stage("emitted", "pitch")}
  },
  H16 = {
    {id = "step", label = "Step", read = function(s) return format(s.selected_step) end},
    {id = "local_scale_bypass", label = "LOCAL SCALE BYPASS", read = planned_status("local_scale_bypass")},
    {id = "ordinary_pitch_used", label = "Ordinary pitch used", read = function() end},
    {id = "emitted", label = "Emitted", read = stage("emitted", "pitch")},
    {id = "group_peers_valid", label = "Group peers valid", read = function() end}
  },
  H18 = {
    {id = "step", label = "Step", read = function(s) return format(s.selected_step) end},
    {id = "planned", label = "Planned", read = stage("planned", "output")},
    {id = "scheduled", label = "Scheduled", read = stage("scheduled", "pitch")},
    {id = "emitted", label = "Emitted", read = stage("emitted", "pitch")},
    {id = "status", label = "Status", read = field("H05", "status")},
    {id = "source_chain", label = "Source chain", read = stage("emitted", "source")}
  }
}

return function(ui_adapters, owners)
  local editor = owners and owners.feature_editors and owners.feature_editors.harmony
  return shared.new(ui_adapters, "harmony", editor, {
    commit_boundary = "global_pattern_boundary",
    variants = variants,
    confirmation_routes = {H04_DELETE = true, TONE_MAP_RESET = true},
    capture = function(owner, snap)
      snap.channel_status = config_state.status(owner.song, owner.channel_number)
      snap.song_status = config_state.status(owner.song, "_song")
      snap.trace = harmony_inspection.snapshot(owner.song, owner.channel_number, owner.selected_step)
    end
  })
end
