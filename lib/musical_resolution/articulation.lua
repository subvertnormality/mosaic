-- The articulation inputs of one step: chord slots, root mute, strum pattern,
-- arp selection and strum timing, resolved from a stock reader exactly as step
-- playback reads them. Shared by step.lua's note path and the Space gate
-- snapshot (docs/musical-merge-extensions-plan.md §6.1), so both resolve the
-- same channel values, per-step overrides, parameter-slot values and stock
-- precedence, and convert division/spread indices through the same tables.
--
-- `stock(kind)` is the only reader; every read happens in the order and under
-- the conditions playback has always used, so a remembering resolver answers
-- the same values it did before this was shared.
local divisions = include("mosaic/lib/clock/divisions")

local note_divisions = divisions.note_divisions
local note_division_values = divisions.note_division_values

local articulation = {}

-- Returns mute_root, chord_one, chord_two, chord_three, chord_four,
-- has_chord_notes, chord_strum_pattern, arp_division, chord_division,
-- chord_velocity_mod, chord_spread (converted to its division value),
-- chord_acceleration. Multiple returns keep the per-note path allocation free.
function articulation.resolve(channel, current_step, stock)
  local mute_root = stock("mute_root_note") == 1

  local step_chord_masks = channel.step_chord_masks[current_step]
  local chord_one = step_chord_masks and step_chord_masks[1] or channel.chord_one_mask
  local chord_two = step_chord_masks and step_chord_masks[2] or channel.chord_two_mask
  local chord_three = step_chord_masks and step_chord_masks[3] or channel.chord_three_mask
  local chord_four = step_chord_masks and step_chord_masks[4] or channel.chord_four_mask
  -- A chord slot sounds only with a non-zero note (see strum_descriptor).
  local has_chord_notes = (chord_one and chord_one ~= 0) or (chord_two and chord_two ~= 0) or
    (chord_three and chord_three ~= 0) or (chord_four and chord_four ~= 0)

  local chord_strum_pattern = stock("chord_strum_pattern")
  local chord_arp = note_divisions[stock("chord_arp")]
  local arp_division = chord_arp and chord_arp.value
  -- Strum timing and chord velocity only shape arps, sounding chord notes and a
  -- delayed root; a plain single note never reads them.
  local chord_division, chord_velocity_mod, chord_spread, chord_acceleration = nil, nil, 0, 0
  if arp_division or has_chord_notes or
      (not mute_root and (chord_strum_pattern == 2 or chord_strum_pattern == 4)) then
    local chord_strum = note_divisions[stock("chord_strum")]
    chord_division = chord_strum and chord_strum.value
    chord_velocity_mod = stock("chord_velocity_modifier")
    chord_spread = stock("chord_spread") or 0
    chord_acceleration = stock("chord_acceleration") or 0
  end

  if chord_spread ~= 0 then
    chord_spread = note_division_values[chord_spread]
  end

  return mute_root, chord_one, chord_two, chord_three, chord_four, has_chord_notes,
    chord_strum_pattern, arp_division, chord_division, chord_velocity_mod, chord_spread,
    chord_acceleration
end

return articulation
