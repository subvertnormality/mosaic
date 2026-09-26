-- UI02 adapter for provider `merge` (Merge Shape feature editor).
--
-- owners: channel_edit_page_ui.adapter_owners(); uses owners.feature_editors.merge,
-- the lib/pages/channel_edit_page/channel_feature_editor.lua instance the
-- Channel page already drives. Routes are OLD owner routes (M01..M09,
-- source_route_map.merge); describe(M01) yields the fields of new screen M02.
-- Commit boundary: channel_cycle (editor:apply() records the transaction; while
-- playing the owner reports NEXT CYCLE). HARMONY_LINK ("Voice leading", field
-- `harmony`) is a cross_owner_link: invoking it runs the owner's existing
-- reload + channel_edit_page_ui.select_harmony_page() and leaves no return frame.
-- Visual variants M04, M08, M09 and M11 are described only from snapshot:<id>.

local shared = include("mosaic/lib/ui_adapters/feature_editor")
local merge_state = include("mosaic/lib/musical_merge/state")
local merge_config = include("mosaic/lib/musical_merge/config")

local format = shared.format

local function amount(config) return config and format(config.amount) or "NONE" end
-- The owner's two anchor rejections: merge_config.validate ("merge anchor",
-- no anchor chosen) and apply()'s assignment check ("anchor not assigned").
local function invalid_anchor(snap)
  return snap.status == "INVALID merge anchor" or snap.status == "INVALID anchor not assigned"
end
local function guidance(predicate) return function(snap) if predicate(snap) then return "" end end end

local variants = {
  M04 = {
    {id = "active_amount", label = "Active amount", read = function(s) return amount(s.active) end},
    {id = "queued_amount", label = "Queued amount", read = function(s) return amount(s.queued) end},
    {id = "changed", label = "Changed", read = function(s) return format(s.queued ~= nil and not shared.equivalent(s.active, s.queued)) end},
    {id = "result_is_active", label = "Result is ACTIVE", read = function(s) return format(s.queued == nil) end}
  },
  M08 = {
    {id = "p01_is_not_assigned", label = "P01 is not assigned", read = function(s) if invalid_anchor(s) then return format(s.draft.anchor) end end},
    {id = "assign_a_pattern", label = "Assign a pattern", read = guidance(invalid_anchor)},
    {id = "then_choose_anchor", label = "then choose Anchor", read = guidance(invalid_anchor)},
    {id = "active_state_kept", label = "Active state kept", read = function(s) return format(s.active and s.active.mode) end}
  },
  M09 = {
    {id = "draft_edits_discarded", label = "Draft edits discarded", read = function(s) return format(s.status == "DRAFT CANCELLED") end},
    {id = "queued_amount", label = "Queued amount", read = function(s) return amount(s.queued) end},
    {id = "active_amount", label = "Active amount", read = function(s) return amount(s.active) end},
    {id = "next_channel_cycle", label = "Next channel cycle", read = function(s) return format(s.queued ~= nil) end}
  },
  M11 = {
    {id = "mode", label = "Mode", read = function(s) return format(s.draft.mode) end},
    {id = "legacy_trig", label = "Legacy trig", read = function(s) return format(s.gesture) end},
    {id = "shape_settings_kept", label = "Shape settings kept", read = function(s) return format(s.draft.shape) end},
    {id = "sources_unchanged", label = "Sources unchanged", read = function() return "" end}
  }
}

return function(ui_adapters, owners)
  local editor = owners and owners.feature_editors and owners.feature_editors.merge
  return shared.new(ui_adapters, "merge", editor, {
    commit_boundary = "channel_cycle",
    variants = variants,
    capture = function(owner, snap)
      local effective = merge_state.effective(owner.song, owner.channel_number,
        owner.channel.musical_merge or merge_config.new())
      snap.active, snap.queued = shared.copy(effective.config), shared.copy(effective.queued)
    end
  })
end
