-- Trig options provider adapter (UI02): screen P02 (existing_route P02).
--
-- owners = trigger_edit_page_ui.adapter_owners(): owners.pages (page 2 is
-- "Trig editor options") and owners.tresillo_mult, the list selector over the
-- eight options x8..x64. The page module is owners.ui, else the global
-- trigger_edit_page_ui; the algorithm is read from owners.page, else the
-- global trigger_edit_page (get_algorithm, the grid algorithm fader).
--
-- The commit boundary is immediate: E3 on the options page runs, per detent,
-- tresillo_mult:increment()/decrement() and update_tresillo(), which sets the
-- native option tresillo_amount (its action refreshes the selector). Editing
-- the amount never applies the generator or touches a stored pattern: only the
-- Tresillo algorithm's grid gesture reads params:string("tresillo_amount")
-- (trigger_edit_page drum_ops.tresillo). An edit selects the options page (as
-- E1 does) and calls trigger_edit_page_ui.enc(3, delta) unchanged. While the
-- Rhythm Doctor algorithm (5) is selected, enc routes to the Doctor, so the
-- amount is described disabled and never edited from here.

local DOCTOR_ALGORITHM = 5
local TRESILLO_ALGORITHM = 2
local OPTIONS_PAGE = 2

return function(ui_adapters, owners)
  local function ui() return owners.ui or trigger_edit_page_ui end
  local function page() return owners.page or trigger_edit_page end

  local function algorithm()
    local p = page()
    return p and p.get_algorithm and p.get_algorithm() or nil
  end

  local function describe()
    local selector = owners.tresillo_mult
    local enum, values = {}, {}
    for index, item in ipairs(selector.list) do enum[index], values[index] = item.name, item.value end
    local item = selector:get_selected() or {}
    local selected_algorithm = algorithm()
    local doctor = selected_algorithm == DOCTOR_ALGORITHM
    return {
      {id = "tresillo_amount", label = "Tresillo amount", short_label = selector.name, kind = "value",
        value = item.name or "NONE",
        enabled = not doctor,
        selected = selector:is_selected(),
        domain = {min = 1, max = #enum, step = 1, enum = enum, values = values, amount = item.value,
          native_param = "tresillo_amount", committed = params:get("tresillo_amount"),
          reason = doctor and "rhythm_doctor_owns_input" or nil},
        edit = function(delta)
          owners.pages:select_page(OPTIONS_PAGE)
          return ui().enc(3, delta)
        end},
    }
  end

  local adapter = ui_adapters.new("trig_options", {describe = describe})

  function adapter.capture(route)
    return {source_route = route or "P02", screen = route or "P02"}
  end

  return adapter
end
