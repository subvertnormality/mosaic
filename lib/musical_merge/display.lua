-- Player-facing text for the Merge Shape screens (docs/musical-merge-extensions-plan.md §5).
--
-- Presentation only: nothing here reads live state or changes a plan. The
-- engines keep their reason codes ("FRAGMENT k · Pnn" with a 0-based k,
-- "MARKER · CHORD Gnn"); the norns font has no '·' glyph, and fragments are
-- numbered from 1 for players, so the screens show "FRAGMENT 1 P03" and
-- "MARKER CHORD G01".
local display = {}

-- One engine reason as the screens show it.
function display.reason(text)
  if text == nil then return nil end
  text = tostring(text)
  local k, source = text:match("^FRAGMENT (%d+) \194\183 P(%d+)$")
  if k then return string.format("FRAGMENT %d P%s", tonumber(k) + 1, source) end
  return (text:gsub(" \194\183 ", " "))
end

-- The ordered rejection reasons of one candidate (§3). One reason is shown
-- whole; several are named in order without their channels, which the Result
-- screen's Interlock row shows, so the list fits one row.
function display.reasons(list)
  if type(list) ~= "table" or #list == 0 then return nil end
  if #list == 1 then return display.reason(list[1]) end
  local names = {}
  for index, reason in ipairs(list) do
    names[index] = (display.reason(reason):gsub(" CH%d+$", ""))
  end
  return table.concat(names, ", ")
end

-- A plan status that is not "ok", as words (anchor_missing -> ANCHOR MISSING).
function display.status(status)
  if status == nil then return nil end
  return (tostring(status):gsub("_", " "))
end

-- A played event's structural pitch decision at a marker: its reason
-- (MARKER CHORD G01, CHORD MISSING) or, when an explicit pitch instruction
-- kept the legacy path, that bypass (BYPASS NOTE MASK, BYPASS RANDOM,
-- BYPASS FIXED, BYPASS QUANTISED FIXED). nil when the event has none.
local STRUCTURAL_BYPASSES = {note_mask = true, random = true, fixed = true, quantised_fixed = true}
function display.structural(status, reason)
  if reason ~= nil then return display.reason(reason) end
  if STRUCTURAL_BYPASSES[status] then return "BYPASS " .. string.upper(display.status(status)) end
  return nil
end

-- An Interlock admission as the Result and Interlock screens show it: ON
-- while it filters, else its visible bypass (RESYNC, PLAN LIMIT, LEADER OFF,
-- LEADER MISSING). Absent: OFF.
function display.admission(result)
  if type(result) ~= "table" then return "OFF" end
  if result.status == "ok" then return "ON" end
  return tostring(result.status)
end

-- Structure marker kinds.
local MARKERS = {off = "off", anchors = "anchors", every_4 = "every 4", every_8 = "every 8"}
local MARKER_KEYS = {}
for key, shown in pairs(MARKERS) do MARKER_KEYS[shown] = key end
display.marker_values = {"off", "anchors", "every 4", "every 8"}
function display.markers(kind) return MARKERS[kind or "off"] or tostring(kind) end
function display.marker_kind(shown) return MARKER_KEYS[shown] end

-- Leader choices: OFF or another channel (never the channel itself).
function display.leader(number) return number and string.format("ch%02d", number) or "off" end
function display.leader_number(shown) return shown ~= "off" and tonumber(tostring(shown):match("(%d+)$")) or nil end
function display.leader_values(channel)
  local values = {"off"}
  for number = 1, 16 do if number ~= channel then values[#values + 1] = display.leader(number) end end
  return values
end

-- Which merge button a Merge Shape mode takes over: Foundation decides the
-- trigs; Fragments decides trigs, notes, velocities and lengths (§2.3), so the
-- saved legacy modes wait for Mode Off. Returns the shape's name or nil.
function display.shape_owner(mode, kind)
  if mode == "foundation" and kind == "trig" then return "Merge Shape" end
  if mode == "fragments" then return "Fragments" end
  return nil
end

-- The prefix C09 shows before a merge mode the shape has taken over.
function display.shape_prefix(mode, kind)
  local owner = display.shape_owner(mode, kind)
  if owner == "Merge Shape" then return "SHAPE" end
  if owner == "Fragments" then return "FRAGMENTS" end
  return nil
end

return display
