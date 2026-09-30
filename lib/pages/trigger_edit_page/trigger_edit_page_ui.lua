local trigger_edit_page_ui = {}


local pages = include("mosaic/lib/ui_components/pages")
local page = include("mosaic/lib/ui_components/page")
local grid_viewer = include("mosaic/lib/ui_components/grid_viewer")
local list_selector = include("mosaic/lib/ui_components/list_selector")
local dancing_doctor = include("mosaic/lib/rhythm_doctor/dancing_doctor")

local pages = pages:new()
local grid_viewer = grid_viewer:new(0, 3)
local tresillo_mult =
  list_selector:new(
  0,
  29,
  "Tresillo mult",
  {
    {id = 1, value = 8, name = "x8"},
    {id = 2, value = 16, name = "x16"},
    {id = 3, value = 24, name = "x24"},
    {id = 4, value = 32, name = "x32"},
    {id = 5, value = 40, name = "x40"},
    {id = 6, value = 48, name = "x48"},
    {id = 7, value = 56, name = "x56"},
    {id = 8, value = 64, name = "x64"}
  }
)


-- The right-hand third of the Rhythm Doctor page is empty whenever no editor
-- or modal is open, so the doctor dances there -- in time with the analysed
-- tempo when there is one.  He yields the space the moment anything needs it,
-- because the overlays write text right across the screen.
local DOCTOR_X, DOCTOR_Y = 97, 15

local function seconds_now()
  if util and type(util.time) == "function" then return util.time() end
  return os.clock()
end

local function doctor_is_clear(model)
  if not model then return true end
  if model.modal then return false end
  if model.alignment and model.alignment.active then return false end
  if model.setup and model.setup.active then return false end
  return true
end

trigger_edit_page_ui.doctor_is_clear = doctor_is_clear

local grid_viewer_page =
  page:new(
  "",
  function()
    grid_viewer:draw()
  end
)

local trig_edit_options_page =
  page:new(
  "Trig editor options",
  function()
    tresillo_mult:draw()
  end
)

function trigger_edit_page_ui.register_ui_draws()
  draw:register_ui(
    "trigger_edit_page",
    function()
      if trigger_edit_page and trigger_edit_page.get_algorithm and trigger_edit_page.get_algorithm() == 5 then
        local model = trigger_edit_page.get_rhythm_doctor_model and trigger_edit_page.get_rhythm_doctor_model() or nil
        local lane = model and model.lane or (trigger_edit_page.get_rhythm_doctor_lane and trigger_edit_page.get_rhythm_doctor_lane())
        screen.level(10)
        screen.move(0, 9)
        screen.text("RHYTHM DOCTOR")
        screen.move(120, 9)
        screen.text("m")
        if doctor_is_clear(model) then
          dancing_doctor.draw(DOCTOR_X, DOCTOR_Y,
            dancing_doctor.pose_at(seconds_now(), model and model.tempo))
        end
        screen.level(10)
        screen.move(0, 22)
        if model and model.alignment and model.alignment.active then
          -- A refused correction keeps its draft, so without this the screen
          -- reads exactly as it did before the player pressed K3 and the
          -- refusal is invisible.
          screen.text(model.alignment.error and tostring(model.alignment.error)
            or ("ALIGNMENT / " .. tostring(model.alignment.field)))
        elseif model and model.setup and model.setup.active then
          screen.text("SETUP / " .. tostring(model.setup.field))
        else
          screen.text(lane .. " / " .. (model and model.status or "NOT READY"))
        end
        if model then
          if model.alignment and model.alignment.active then
            screen.move(0, 34)
            screen.text((model.alignment.field == "HALF TEMPO" and ">" or " ") .. "HALF " .. tostring(model.alignment.bpm or "") .. " BPM")
            screen.move(0, 46)
            screen.text((model.alignment.field == "DOUBLE TEMPO" and ">" or " ") .. "DOUBLE / START " .. tostring(model.alignment.start_beat or ""))
            screen.move(0, 58)
            screen.text((model.alignment.field == "FINE START" and ">" or " ") .. "FINE " .. tostring(model.alignment.fine_start_ms or 0) .. "ms")
          elseif model.setup and model.setup.active then
            screen.move(0, 34)
            screen.text((model.setup.field == "TEMPO" and ">" or " ") .. "TEMPO " .. string.upper(tostring(model.capture_mode or "auto")))
            screen.move(0, 46)
            screen.text((model.setup.field == "MANUAL BPM" and ">" or " ") .. "MANUAL BPM " .. tostring(model.manual_bpm or ""))
            screen.move(0, 58)
            screen.text((model.setup.field == "INPUT" and ">" or " ") .. "INPUT " .. tostring(model.input_source or "STEREO"))
          else
            screen.move(0, 34)
            screen.text("HITS " .. tostring(model.hit_count or 0) .. " / " .. tostring(model.state or "EMPTY"))
            screen.move(0, 46)
            if model.tempo then screen.text(string.format("%.1f BPM / %s", model.tempo, tostring(model.tempo_source or "")))
            elseif model.acquired_beats then screen.text(tostring(model.acquired_beats) .. " BEATS") end
            if model.ready and model.ready.active then
              -- The window position is shown by the grid itself, so spelling it
              -- out here said nothing the player could not already see and
              -- collided with the row the modal and the doctor share.
              local detail = model.ready.field == "SENSITIVITY" and ("SENS " .. tostring(model.sensitivity or ""))
                or model.ready.field == "PAINT POLICY" and ("PAINT " .. string.upper(tostring(model.paint_policy or "toggle")))
                or nil
              if detail then screen.move(0, 58); screen.text(detail) end
            end
          end
          if model.modal then
            screen.move(0, 58)
            screen.text(model.modal.detail or "K2 NO / K3 YES")
          end
        end
        return
      end
      pages:draw()
    end
  )
end

function trigger_edit_page_ui.init()
  pages:add_page(grid_viewer_page)
  pages:add_page(trig_edit_options_page)
  pages:select_page(1)
  tresillo_mult:select()
  trigger_edit_page_ui.refresh_tresillo()
end

function trigger_edit_page_ui.enc(n, d)
  if trigger_edit_page and trigger_edit_page.get_algorithm and trigger_edit_page.get_algorithm() == 5 then
    local value = trigger_edit_page.handle_rhythm_doctor_encoder and trigger_edit_page.handle_rhythm_doctor_encoder(n, d)
    fn.dirty_screen(true); fn.dirty_grid(true)
    return value and value.code ~= "UNCLAIMED"
  end
  if n == 2 then
    for i = 1, math.abs(d) do
      if d > 0 then
        grid_viewer:next_channel()
      else
        grid_viewer:prev_channel()
      end
    end
  end

  if n == 1 then
    for i = 1, math.abs(d) do
      if d > 0 then
        pages:next_page()
        fn.dirty_screen(true)
      else
        pages:previous_page()
        fn.dirty_screen(true)
      end
    end
  end

  if n == 3 then
    for i = 1, math.abs(d) do
      if d > 0 then
        if pages:get_selected_page() == 2 then
          tresillo_mult:increment()
          trigger_edit_page_ui.update_tresillo()
        end
      else
        if pages:get_selected_page() == 2 then
          tresillo_mult:decrement()
          trigger_edit_page_ui.update_tresillo()
        end
      end
    end
  end
end

function trigger_edit_page_ui.key(n, z)
  if not trigger_edit_page or not trigger_edit_page.get_algorithm or trigger_edit_page.get_algorithm() ~= 5 then return false end
  local value = trigger_edit_page.handle_rhythm_doctor_key and trigger_edit_page.handle_rhythm_doctor_key(n, z)
  fn.dirty_screen(true); fn.dirty_grid(true)
  return value and value.code ~= "UNCLAIMED"
end

function trigger_edit_page_ui.update_tresillo()
  params:set("tresillo_amount", tresillo_mult:get_selected().id)
end

function trigger_edit_page_ui.refresh_tresillo()
  tresillo_mult:set_selected_value(params:get("tresillo_amount"))
end

function trigger_edit_page_ui:refresh()
  trigger_edit_page_ui.refresh_tresillo()
end

-- The existing owner instances, for lib/ui_adapters (UI02). Adapters wrap
-- these objects; they do not copy their state.
function trigger_edit_page_ui.adapter_owners()
  return {
    pages = pages,
    grid_viewer = grid_viewer,
    tresillo_mult = tresillo_mult
  }
end

return trigger_edit_page_ui
