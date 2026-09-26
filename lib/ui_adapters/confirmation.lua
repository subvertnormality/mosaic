-- Confirmation provider (docs/ui-reimplementation spec.json#/confirmation_contracts, UI02).
--
-- A thin dispatcher. It holds no token and no question of its own: for each
-- screen in confirmation_contracts it forwards K3 (apply) and K2 (cancel) to
-- the owner closure named there, exactly once, after re-validating the
-- captured identity. The owner decides what confirming means.
--
-- owners: a lookup keyed by the contract's `owner` family. Each entry is an
-- owner interface:
--   pending(screen, contract, target) -> boolean     the owner's question is up
--   confirm(screen, contract, target, owner) -> result   K3, the named confirm closure
--   cancel(screen, contract, target, owner) -> result    K2, the named cancel closure
--   generation(screen, contract, target) -> value   optional; compared on K3/K2
--   describe(screen, contract, target) -> descriptors  optional; screens this
--                                        provider renders (S05, R03, R10, R16)
--
--   owners.harmony  REQUIRED for H17/H19; no default (the harmony adapter owns
--                   the closures). confirm must run the H04_DELETE "Confirm
--                   delete" / TONE_MAP_RESET "Confirm reset" invoke closure of
--                   the live harmony channel_feature_editor exactly as its
--                   key(3) does (field.before then field.invoke); cancel must
--                   run that editor's key(2). pending: editor.screen equals
--                   contract.source_route.
--   owners.scale    default built by scale_owner (below) from
--                   owners.save_confirm (default global save_confirm),
--                   owners.pressed_keys (default m_grid.get_pressed_keys) and
--                   owners.scale_page (default scale_edit_page_ui.adapter_owners()).
--   owners.doctor   default built by doctor_owner (below) from
--                   owners.doctor_page (default global trigger_edit_page: its
--                   handle_rhythm_doctor_key and get_rhythm_doctor_model).
--
-- Owner token envelope (held by the caller, never by this adapter):
--   {screen = <contract key, e.g. "R03">, target = <captured target>,
--    generation = <owner generation at entry>, owner = <opaque owner token or nil>}
-- adapter.capture(screen, target) builds one at entry without mutating anything.
-- K3: adapter:apply(envelope, target) ; K2: adapter:cancel(envelope).

-- Owner result codes meaning the question was not answered (the doctor's
-- Adapter:key guards, and this module's own held-key refusal).
local REFUSED = {held = true, no_owner = true, RELEASE_PENDING = true, STOP_SEQUENCER = true,
  STALE_REQUEST = true, UNCLAIMED = true}

local OWNER_FAMILY = {harmony = "harmony", scale = "scale", ["doctor runtime"] = "doctor"}

-- Stable ids of the Doctor question rows, declared with their copy. The
-- runtime modal token carries only the title (modal_copy); the rows are the
-- screen's own copy.
local DOCTOR_ROWS = {
  R03 = {{id = "discard_this_take", label = "Discard this take?"},
    {id = "no_bank_written_yet", label = "No bank written yet"},
    {id = "k2_keeps_take", label = "K2 keeps the take"},
    {id = "k3_discards_take", label = "K3 discards take"}},
  R10 = {{id = "clear_all_lanes", label = "Clear all lanes?"},
    {id = "painted_patterns", label = "Painted patterns"},
    {id = "will_be_kept", label = "will be kept"},
    {id = "this_removes_capture", label = "This removes capture"}},
  R16 = {{id = "restore_previous_bank", label = "Restore previous bank?"},
    {id = "correction_discarded", label = "Correction discarded"},
    {id = "k2_keeps_correcting", label = "K2 keeps correcting"},
    {id = "k3_restores_bank", label = "K3 restores bank"}}
}

local function contains(list, value)
  for _, item in ipairs(list or {}) do if item == value then return true end end
  return false
end

local function held(pressed_keys)
  local keys = pressed_keys and pressed_keys() or {}
  return #keys > 0
end

-- Scale: the existing save_confirm question armed by scale_edit_page_ui.update_scale.
-- K3 = save_confirm.confirm and K2 = save_confirm.cancel, only with no grid key
-- held (scale_edit_page_ui.handle_key_three/two_pressed; with keys held K3 does
-- nothing and K2 clears step scale locks, which is not a confirmation answer).
-- save_confirm exposes no "armed" getter, so pending is the caller's captured
-- target.armed (set when the router raised S05 on the owner's set_save).
local function scale_owner(sources)
  local save_confirm = sources.save_confirm
  local pressed_keys = sources.pressed_keys
  local page = sources.scale_page
  local owner = {}
  function owner.pending(_, _, target)
    return type(target) == "table" and target.armed == true
  end
  function owner.confirm()
    if held(pressed_keys) then return {ok = false, code = "held"} end
    return save_confirm.confirm()
  end
  function owner.cancel()
    if held(pressed_keys) then return {ok = false, code = "held"} end
    return save_confirm.cancel()
  end
  function owner.describe(_, _, target)
    local p = page and page() or {}
    local scale = p.quantizer_vertical_scroll_selector and p.quantizer_vertical_scroll_selector:get_selected_item()
    local roman = p.romans_vertical_scroll_selector and p.romans_vertical_scroll_selector:get_selected_item()
    local change = scale and scale.name or "NONE"
    if roman ~= nil then change = change .. " / " .. tostring(type(roman) == "table" and roman.name or roman) end
    local slot = target.scale_slot or (program and program.get().selected_scale)
    return {
      {id = "change", label = "Change", kind = "readonly", value = change},
      {id = "target", label = "Target", kind = "readonly", value = slot and string.format("Scale slot%02d", slot) or "NONE",
        domain = {scale_slot = slot}},
      {id = "scope", label = "Scope", kind = "readonly", value = target.scope == "all_song" and "ALL SONG" or "THIS SLOT",
        domain = {scope = target.scope or "slot"}},
      {id = "state", label = "State", kind = "readonly", value = "NOT APPLIED"}
    }
  end
  return owner
end

-- Doctor: the runtime modal token lives in lib/rhythm_doctor/ui_adapter.lua.
-- K3/K2 go through the same trigger_edit_page.handle_rhythm_doctor_key(n, 1)
-- that ui.key reaches, which passes the unchanged opaque token to
-- runtime:confirm_modal (Adapter:key). Staleness is the owner's (sync_modal).
local function doctor_owner(sources)
  local page = sources.doctor_page
  local function model()
    local p = page and page()
    return p and p.get_rhythm_doctor_model and p.get_rhythm_doctor_model() or nil
  end
  local owner = {}
  function owner.pending(_, contract)
    local m = model()
    return m ~= nil and m.modal ~= nil and m.modal.operation == contract.operation and
      (contract.states == nil or contains(contract.states, m.state))
  end
  function owner.generation()
    local m = model()
    return m and m.modal and (tostring(m.state) .. ":" .. tostring(m.modal.operation)) or "none"
  end
  local function key(n)
    local p = page and page()
    if not (p and p.handle_rhythm_doctor_key) then return {ok = false, code = "no_owner"} end
    local value = p.handle_rhythm_doctor_key(n, 1)
    if fn and fn.dirty_screen then fn.dirty_screen(true) end
    if fn and fn.dirty_grid then fn.dirty_grid(true) end
    return value
  end
  function owner.confirm() return key(3) end
  function owner.cancel() return key(2) end
  function owner.describe(screen)
    local m = model()
    local descriptors = {}
    for _, row in ipairs(DOCTOR_ROWS[screen] or {}) do
      descriptors[#descriptors + 1] = {id = row.id, label = row.label, kind = "readonly", value = "",
        domain = {title = m and m.modal and m.modal.title, operation = m and m.modal and m.modal.operation}}
    end
    return descriptors
  end
  return owner
end

local function factory(ui_adapters, owners)
  owners = owners or {}
  local contracts = ui_adapters.spec.confirmation_contracts

  local lookup = {
    harmony = owners.harmony,
    scale = owners.scale or scale_owner({
      save_confirm = owners.save_confirm or _ENV["save_confirm"],
      pressed_keys = owners.pressed_keys or function() return m_grid.get_pressed_keys() end,
      scale_page = owners.scale_page or function()
        local ui = _ENV["scale_edit_page_ui"]
        return ui and ui.adapter_owners and ui.adapter_owners() or {}
      end}),
    doctor = owners.doctor or doctor_owner({
      doctor_page = owners.doctor_page or function() return _ENV["trigger_edit_page"] end})
  }

  -- Contract key for a screen id or an old owner route (H04_DELETE -> H17).
  local function contract_key(value)
    if value == nil or value == "common" then return nil end
    if contracts[value] then return value end
    for key, contract in pairs(contracts) do
      if key ~= "common" and contract.source_route == value then return key end
    end
    return nil
  end

  local function resolve(screen)
    local key = contract_key(screen)
    if not key then return nil, nil, nil, "unknown_confirmation" end
    local contract = contracts[key]
    local owner = lookup[OWNER_FAMILY[contract.owner]]
    if not owner then return key, contract, nil, "no_owner" end
    return key, contract, owner
  end

  local function generation_of(owner, key, contract, target)
    return owner.generation and owner.generation(key, contract, target) or 0
  end

  local impl = {}

  function impl.generation(target)
    local key, contract, owner = resolve(target and (target.screen or target.source_route))
    if not owner then return 0 end
    return generation_of(owner, key, contract, target)
  end

  function impl.pending_confirmation(target)
    local key, contract, owner = resolve(target and (target.screen or target.source_route))
    return owner ~= nil and owner.pending(key, contract, target) == true
  end

  function impl.describe(route, target)
    local key, contract, owner, problem = resolve(route)
    if problem then return nil, problem end
    if not owner.pending(key, contract, target or {}) then return nil, "no_pending_confirmation" end
    if not owner.describe then return nil, "no_owner_descriptors" end
    return owner.describe(key, contract, target or {})
  end

  -- Validates the envelope, then runs the named owner closure exactly once.
  local function answer(which, envelope, target)
    envelope = type(envelope) == "table" and envelope or {}
    target = target or envelope.target or {}
    local key, contract, owner, problem = resolve(envelope.screen or target.screen or target.source_route)
    local identity = {provider = "confirmation", screen = key, target = target, answer = which}
    if problem then return ui_adapters.fail(problem, identity) end
    identity.owner_generation = generation_of(owner, key, contract, target)
    if envelope.generation ~= nil and envelope.generation ~= identity.owner_generation then
      return ui_adapters.fail("stale_generation", identity)
    end
    if not owner.pending(key, contract, target) then return ui_adapters.fail("no_pending_confirmation", identity) end
    local result = owner[which](key, contract, target, envelope.owner)
    -- The owner ran but refused to answer: its question is still up.
    if type(result) == "table" and result.ok == false and REFUSED[result.code] then
      local failed = ui_adapters.fail(result.code, identity)
      failed.result = result
      return failed
    end
    local outcome = ui_adapters.outcome(identity)
    outcome.code = which == "confirm" and "confirmed" or "cancelled"
    outcome.result = result
    outcome.owner_code = type(result) == "table" and result.code or nil
    return outcome
  end

  function impl.apply(envelope, target) return answer("confirm", envelope, target) end
  function impl.cancel(envelope) return answer("cancel", envelope) end

  local adapter = ui_adapters.new("confirmation", impl)

  -- Entry: capture owner identity and target; no mutation.
  function adapter.capture(screen, target, owner_token)
    local key, contract, owner, problem = resolve(screen)
    if problem then return nil, problem end
    target = target or {}
    return {screen = key, target = target, owner = owner_token,
      generation = generation_of(owner, key, contract, target)}
  end

  adapter.owners = lookup
  return adapter
end

return factory
