local harmony_context = include("mosaic/lib/harmony/context")

local pitch_target = {}

function pitch_target.resolve(pitch, options)
  options = options or {}
  if not options.eligible then return pitch, "ineligible" end
  if options.bypass then return pitch, options.bypass end
  local config = options.config or {kind="legacy"}
  if config.kind == "legacy" then return pitch, "legacy" end

  local pitch_classes
  if config.kind == "scale" then
    pitch_classes = options.scale_pitch_classes or {}
  elseif config.kind == "degrees" then
    pitch_classes = {}
    local inventory = options.scale_pitch_classes or {}
    for _, degree in ipairs(config.degrees or {}) do
      if inventory[degree] == nil then return pitch, "source_missing" end
      pitch_classes[#pitch_classes + 1] = inventory[degree]
    end
  elseif config.kind == "chord" then
    if not options.chord_material then return pitch, "source_missing" end
    pitch_classes = options.chord_material
  else
    return pitch, "source_missing"
  end

  if #pitch_classes == 0 then return pitch, "target_empty" end
  return harmony_context.nearest_pitch(pitch, pitch_classes), "targeted"
end

return pitch_target
