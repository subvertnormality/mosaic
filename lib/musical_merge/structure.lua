-- Structural chord tones (docs/musical-merge-extensions-plan.md §4).
--
-- Pure helpers only: marker sets, the per-position pitch policy shared by
-- step.handle and the Harmony Pattern material loop, reasons, the persisted
-- Pattern identity suffix and the reference repair used when a Harmony group
-- is deleted or disabled. Nothing here reads live state or draws from the RNG.
local pitch_target = include("mosaic/lib/musical_merge/pitch_target")

local structure = {}

local marker_spacing = {every_4 = 4, every_8 = 8}

-- The structure settings with semantics: enabled markers on a Foundation
-- configuration. Every other combination (merge Off or Fragments, markers Off,
-- a v1 configuration) is inactive and returns nil.
function structure.active(merge)
  if type(merge) ~= "table" or merge.mode ~= "foundation" then return nil end
  local value = merge.structure
  if type(value) ~= "table" or value.markers == nil or value.markers == "off" or
    value.group_id == nil then return nil end
  return value
end

-- The playable positions first..last (never wrapping: validation forbids first > last).
function structure.positions(first, last)
  local result = {}
  for step = first, last do result[#result + 1] = step end
  return result
end

-- Marker positions as a set. `positions` are the channel's playable positions
-- in order; every_4/every_8 count p1, p5 … / p1, p9 … from the loop's own first
-- position whether or not an onset lands there; anchors are the Foundation
-- anchor positions among them.
function structure.markers(kind, positions, roles)
  local result = {}
  local spacing = marker_spacing[kind]
  for index, step in ipairs(positions or {}) do
    if spacing then
      if (index - 1) % spacing == 0 then result[step] = true end
    elseif kind == "anchors" and roles and roles[step] == "anchor" then
      result[step] = true
    end
  end
  return result
end

-- The per-position policy, selected before scale conversion.
--   marker            the position is an active structural marker
--   role              Foundation role at the position (anchor/addition/nil)
--   bypass            an explicit pitch instruction (note_mask, random,
--                     quantised_fixed, fixed) or nil
--   target, target_available   the Addition Target and whether it has material
--   marker_material   the marker chord's pitch classes (nil or empty: missing)
-- Result kinds: bypass (marker with an explicit instruction: complete legacy
-- path), marker (snap), chord_missing (complete legacy path), addition (the
-- existing Addition Target rule) and legacy.
function structure.policy(args)
  if args.marker then
    if args.bypass then
      return {kind = "bypass", bypass = args.bypass, suppress_merged_pentatonic = false}
    end
    local material = args.marker_material
    if type(material) == "table" and #material > 0 then
      return {kind = "marker", material = material, suppress_merged_pentatonic = true}
    end
    return {kind = "chord_missing", suppress_merged_pentatonic = false}
  end
  if args.role == "addition" then
    local target = args.target
    return {kind = "addition", bypass = args.bypass,
      suppress_merged_pentatonic = not args.bypass and target ~= nil and target.kind ~= "legacy" and
        args.target_available == true}
  end
  return {kind = "legacy", suppress_merged_pentatonic = false}
end

-- Apply a policy to the converted pitch. `context` carries the Addition
-- Target inputs (target, scale_pitch_classes, chord_material).
function structure.resolve(policy, pitch, context)
  context = context or {}
  if policy.kind == "marker" then return pitch_target.snap_to_chord(pitch, policy.material), "marker" end
  if policy.kind == "chord_missing" then return pitch, "chord_missing" end
  if policy.kind == "bypass" then return pitch, policy.bypass end
  if policy.kind == "addition" then
    return pitch_target.resolve(pitch, {eligible = true, bypass = policy.bypass, config = context.target,
      scale_pitch_classes = context.scale_pitch_classes, chord_material = context.chord_material})
  end
  return pitch, nil
end

local reasons = {chord_missing = "CHORD MISSING", marker_priority = "MARKER PRIORITY"}

-- Display reasons for the Result/Reason screens.
function structure.reason(status, group_id)
  if status == "marker" then return string.format("MARKER · CHORD G%02d", group_id or 0) end
  return reasons[status]
end

-- The versioned Harmony Pattern binding suffix for active markers, or nil.
function structure.identity(merge)
  local value = structure.active(merge)
  if not value then return nil end
  return "structure-v1," .. value.markers .. "," .. tostring(value.group_id)
end

function structure.group_available(voicing, group_id)
  local group = type(voicing) == "table" and type(voicing.groups) == "table" and voicing.groups[group_id]
  return type(group) == "table" and group.enabled == true
end

-- Turn markers Off (group nil) when the configuration's marker group is not an
-- existing enabled group of `groups`. Changes `merge` in place; true if it did.
function structure.repair(merge, groups)
  if type(merge) ~= "table" or type(merge.structure) ~= "table" then return false end
  local value = merge.structure
  if value.markers == nil or value.markers == "off" then return false end
  if structure.group_available({groups = groups}, value.group_id) then return false end
  merge.structure = {markers = "off", group_id = nil}
  return true
end

return structure
