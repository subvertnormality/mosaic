-- Execute the actual entrypoint closures with explicit IO/transport boundaries.
-- Native behaviour tests separately exercise the complete application/runtime.
local function find_upvalue(fn, wanted)
  for i=1,100 do
    local name,value=debug.getupvalue(fn,i)
    if not name then break end
    if name==wanted then return value end
  end
  error("Missing entrypoint closure: "..wanted)
end

local function load_fixture()
  local channels,devices={},{}
  for i=1,17 do channels[i]={start_trig={1,4},end_trig={4,4}} end
  for i=1,16 do devices[i]={device_map=1,midi_channel=1,midi_device=1} end
  return {"good",{song_patterns={[1]={global_pattern_length=4,channels=channels}},devices=devices}}
end

local function load_context()
  local count={stop=0,reset=0,init=0,set=0,read=0,restore=0,writes=0,hooks=0}
  local original={identity="live",pending_notes={60,64},memory={position=3}}
  local state={store=original,playing=true,files={},messages={},timers={}}
  local env=setmetatable({}, {__index=_G})
  env.print=function() end
  env.clock={transport={}}
  env.grid={connect=function() return {} end}
  env.norns={state={data="fixture/"}}
  env.tooltip={show=function(_,message) state.messages[#state.messages+1]=message end}
  env.io={open=function(path,mode)
    if mode=="wb" then
      return {write=function() if state.table_write_error then return nil,"table write failed" end;return true end,
        close=function() if state.table_close_error then return nil,"table close failed" end;return true end}
    end
    if not state.files[path] then return nil,"missing",2 end
    return {close=function() return true end}
  end,
  write=function() if state.write_error then return nil,"write failed" end;if state.write_throw then error("write threw") end;return true end,
  close=function() if state.close_error then return nil,"close failed" end;return true end}
  env.tab={load=function(path) if state.decode_error then error("bad data") end;return state.files[path] end,
    save=function(_,path)
      if state.save_error then return "write failed" end
      local file=env.io.open(path,"wb");file:write("project");file:close();count.writes=count.writes+1
    end}
  env.params={action_write=function() count.hooks=count.hooks+1 end,
    read=function() count.read=count.read+1 end,
    write=function(self,path)
      if state.pset_error then return end
      env.io.write("parameters");env.io.close()
      if self.action_write then self.action_write(path) end
    end}
  env.metro={init=function(callback)
    local timer={id=#state.timers+1,event=callback,running=false}
    function timer:start() self.running=true end
    function timer:stop() self.running=false end
    state.timers[#state.timers+1]=timer;return timer
  end,free=function(id) state.timers[id].running=false end}
  local model={init=function() count.init=count.init+1 end,
    set=function(value) count.set=count.set+1;state.store=value end,
    get=function() return state.store end,prepare_for_save=function() return state.store end}
  -- New creates a usable fresh model; retain original by reference for rejection.
  model.init=function() count.init=count.init+1;state.store=load_fixture()[2] end
  local clock={stop=function() count.stop=count.stop+1;state.playing=false end,
    reset=function() count.reset=count.reset+1 end,is_playing=function() return state.playing end}
  local modules={
    ["mosaic/lib/models/program"]=model,["mosaic/lib/clock/m_clock"]=clock,
    ["mosaic/lib/project_validation"]=dofile("../../lib/project_validation.lua"),
    ["mosaic/lib/helpers/functions"]={dirty_screen=function() end,dirty_grid=function() end},
    ["mosaic/lib/ui"]={refresh=function() end},["mosaic/lib/m_grid"]={refresh=function() end},
    ["mosaic/lib/devices/param_manager"]={init=function() count.restore=count.restore+1 end,add_device_params=function() end},
    ["mosaic/lib/devices/device_map"]={get_device=function() return {} end}}
  env.include=function(name) return modules[name] or {} end
  env.require=function(name)
    assert(name=="fileselect" or name=="textentry" or name=="mosaic/lib/nb/lib/nb")
    return {}
  end
  assert(loadfile("../../mosaic.lua","t",env))()
  local load=find_upvalue(env.init,"load_project")
  local new=find_upvalue(env.init,"load_new_project")
  local prime=find_upvalue(env.autosave_reset,"prime_autosave")
  local autosave=find_upvalue(prime,"do_autosave")
  local save=find_upvalue(autosave,"save_project")
  local function blocked()
    local before=count.writes;local timers=#state.timers
    env.autosave_reset();prime();autosave()
    luaunit.assert_equals(count.writes,before)
    luaunit.assert_equals(#state.timers,timers)
    luaunit.assert_not_equals(state.messages[#state.messages],"Autosaved")
  end
  return {env=env,state=state,count=count,original=original,load=load,new=new,prime=prime,autosave=autosave,save=save,blocked=blocked}
end

function test_rejected_load_preserves_live_state_and_queued_autosave_callbacks()
  local c=load_context();local bad=load_fixture();bad[2].song_patterns[1].channels[1].start_trig={5,4}
  c.state.files["fixture/bad.ptn"]=bad;c.env.autosave_reset()
  luaunit.assert_false(c.load("fixture/bad.ptn"))
  luaunit.assert_is(c.state.store,c.original);luaunit.assert_true(c.state.playing)
  for _,name in ipairs({"stop","reset","init","set","read","restore","writes"}) do luaunit.assert_equals(c.count[name],0) end
  luaunit.assert_equals(c.state.messages[#c.state.messages],"Slot 1 ch 1 reversed")
  for _,timer in ipairs(c.state.timers) do luaunit.assert_false(timer.running) end
  c.blocked();c.blocked()
  luaunit.assert_false(c.load("cancel"));luaunit.assert_false(c.save(nil));c.blocked()
  luaunit.assert_true(c.state.playing);luaunit.assert_is(c.state.store,c.original)
end

function test_rejected_load_autosave_recovery_actions_and_failed_saves()
  for _,recovery in ipairs({"save","new","load"}) do
    local c=load_context();c.state.files["fixture/bad.ptn"]={false}
    c.load("fixture/bad.ptn");c.blocked()
    c.state.save_error=true;luaunit.assert_false(c.save("failed"));c.state.save_error=false;c.blocked()
    local hook=c.env.params.action_write
    c.state.pset_error=true;luaunit.assert_false(c.save("failed-pset"));c.state.pset_error=false
    luaunit.assert_is(c.env.params.action_write,hook);c.blocked()
    if recovery=="save" then luaunit.assert_true(c.save("recovered"));luaunit.assert_equals(c.count.hooks,1)
    elseif recovery=="new" then c.new()
    else c.state.files["fixture/good.ptn"]=load_fixture();luaunit.assert_true(c.load("fixture/good.ptn")) end
    luaunit.assert_true(c.state.timers[#c.state.timers].running)
    c.state.playing=false;c.prime();local writes=c.count.writes;c.autosave()
    luaunit.assert_equals(c.count.writes,writes+1);luaunit.assert_equals(c.state.messages[#c.state.messages],"Autosaved")
  end
end

function test_missing_startup_is_normal_but_unreadable_manual_load_is_rejected()
  local c=load_context();luaunit.assert_false(c.load("fixture/autosave.ptn",true))
  luaunit.assert_equals(#c.state.messages,0);luaunit.assert_equals(c.count.stop,0)
  c.env.autosave_reset();luaunit.assert_true(c.state.timers[#c.state.timers].running)
  luaunit.assert_false(c.load("fixture/missing.ptn"));c.blocked()
  luaunit.assert_equals(c.count.stop,0);luaunit.assert_is(c.state.store,c.original)
end


function test_save_io_failures_and_throwing_hooks_preserve_inhibition_and_restore_io()
  for _,failure in ipairs({"table_write_error","table_close_error","write_error","close_error","write_throw","hook_throw"}) do
    local c=load_context();c.state.files["fixture/bad.ptn"]={false};c.load("fixture/bad.ptn")
    local open,write,close=c.env.io.open,c.env.io.write,c.env.io.close
    if failure=="hook_throw" then c.env.params.action_write=function() error("hook threw") end
    else c.state[failure]=true end
    local hook=c.env.params.action_write
    luaunit.assert_false(c.save("recovery"))
    luaunit.assert_is(c.env.io.open,open);luaunit.assert_is(c.env.io.write,write);luaunit.assert_is(c.env.io.close,close)
    luaunit.assert_is(c.env.params.action_write,hook)
    c.blocked()
  end
end
