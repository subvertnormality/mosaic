-- README.md "Rhythm Doctor": Record shows capture; completed analysis shows the ready window.
-- Integration characterisation: rendering follows the Doctor owner without another input.
-- Native public-ADC acceptance is MA-DOCTOR-AUDIO-001; no private-state acceptance here.
local live = include("mosaic/lib/tests/helpers/ui_live_env")
local function isolated(body)
  local adapter
  live.isolated(function(env)
    env.algorithm = 5
    params.lookup.ui_motion = true
    env.param_values.ui_motion = 1
    local route = "R01"
    adapter.current_route = function() return route end
    adapter.describe = function()
      return {ok=true,descriptors={{id="status",label="Status",value=route,kind="readonly",visible=true}}}
    end
    ui_live.state().screen = "R01"
    body(function(value) route=value end)
  end,{page=pages.pages.trigger_edit_page,before_ui=function()
    local prior=include
    include=function(path)
      local value=prior(path)
      if path=="mosaic/lib/ui_adapters/doctor" then
        return function(...)
          adapter=value(...)
          return adapter
        end
      end
      return value
    end
  end})
end
function test_ui_live_doctor_route_refresh_capture_without_dispatch()
  isolated(function(owner_route)
    luaunit.assert_equals(ui_live.view_model().screen,"R01")
    owner_route("R02") -- Record's pre-press owner path skips ordinary grid.outcome.
    local vm=ui_live.view_model()
    luaunit.assert_equals(vm.screen,"R02")
    luaunit.assert_equals(vm.title,"CAPTURE")
    luaunit.assert_equals(vm.fields[1].value,"R02")
  end)
end
function test_ui_live_doctor_route_refresh_ready_without_dispatch()
  isolated(function(owner_route)
    ui_live.state().screen="R04"
    owner_route("R05") -- Local analysis callback has no key or encoder dispatch.
    local vm=ui_live.view_model()
    luaunit.assert_equals(vm.screen,"R05")
    luaunit.assert_equals(vm.fields[1].value,"R05")
  end)
end
function test_ui_live_doctor_route_refresh_preserves_other_trig_screen()
  isolated(function(owner_route)
    ui_live.state().screen="P06"
    owner_route("R05")
    luaunit.assert_equals(ui_live.view_model().screen,"P06")
  end)
end
