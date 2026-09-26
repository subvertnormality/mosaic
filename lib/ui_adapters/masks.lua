-- Masks provider adapter (UI02): screens C01, C12, F06 (descriptor_filter views).
--
-- owners = channel_edit_page_ui.adapter_owners(); uses owners.mask_selectors
-- (the eight value selectors the Masks page draws) and owners.mask_handlers
-- (channel_edit_masks handlers E3 reaches). Field ids are declared beside the
-- owner in channel_edit_masks.fields.
--
-- Values are read from the current mask selectors, which refresh_masks fills
-- with the channel defaults or, while steps are held, the held steps' locks
-- (field_contracts.masks.read). The formatted value is the selector's own view
-- text ("X" for an unset mask); domain.inherit is the unset sentinel and
-- domain.state says "inherit" or "set", so INHERIT is never shown as 0. The
-- owner has no MIXED state: with several held steps it shows the last held
-- step's value, and so does this adapter.
--
-- Edits call the owner handler for the field on the selected channel once per
-- detent with the full delta, as channel_edit_navigation.enc(3, d) does; the
-- handler itself reads the held set, so a target whose held set differs from
-- the owner's is refused as stale before the handler runs.

local channel_edit_masks = include("mosaic/lib/pages/channel_edit_page/channel_edit_masks")
local channel_target = include("mosaic/lib/ui_adapters/channel_target")

return function(ui_adapters, owners)
  local selectors = owners.mask_selectors
  local handlers = owners.mask_handlers

  local function selector_for(field)
    if field.chord then return selectors.chords[field.chord] end
    return selectors[field.selector]
  end

  local function describe()
    local held = channel_target.held_steps()
    local descriptors = {
      {id = "steps", label = "Steps", kind = "readonly", value = channel_target.format_steps(held),
        visible = #held > 0, domain = {steps = held}}
    }
    for _, field in ipairs(channel_edit_masks.fields) do
      local selector = selector_for(field)
      local raw = selector:get_value()
      descriptors[#descriptors + 1] = {
        id = field.id,
        label = field.label,
        -- The whole name in the cell (it scrolls when the cell is too narrow):
        -- "Velocity", "Chord 1", not "Vel" / "Chd1" (owner request 26 September 2026).
        short_label = field.label,
        kind = "value",
        value = selector.view_transform_func(raw),
        selected = selector:is_selected(),
        domain = {
          min = selector.min, max = selector.max, step = 1, inherit = field.inherit, raw = raw,
          state = raw == field.inherit and "inherit" or "set",
          contract_id = field.contract_id or field.id
        },
        edit = function(delta)
          return channel_target.per_detent(delta, function(d)
            return handlers[field.handler](program.get_selected_channel(), d)
          end)
        end
      }
    end
    descriptors[#descriptors + 1] = {id = "scope", label = "Scope", kind = "readonly",
      value = channel_target.scope(held), domain = {held = #held}}
    return descriptors
  end

  return ui_adapters.new("masks", {
    describe = describe,
    generation = channel_target.generation(channel_target.identity),
    target_valid = function(target) return channel_target.valid(target) end
  })
end
