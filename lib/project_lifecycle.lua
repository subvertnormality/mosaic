-- Project operations and autosave share one inhibition state and timer owner.
local project_lifecycle = {}

function project_lifecycle.new(as_metro, autosave_timer, param_manager, project_validation, set_splash, capture_guard)
  local autosave_inhibited = false
  local autosave_reset
  local new_project_sequence = 0

local function reject_project(reason)
  autosave_inhibited = true
  autosave_timer:stop()
  as_metro:stop()
  print("Load rejected: " .. reason)
  tooltip:show(reason)
  fn.dirty_screen(true)
  return false
end

local function resume_autosave()
  autosave_inhibited = false
  autosave_reset()
end

local function after_capture_release(continuation)
  if not capture_guard then return continuation() end
  local decision = capture_guard:prepare_project_change(continuation)
  if decision.code == "DEFERRED" then
    tooltip:show("RELEASING CAPTURE")
    fn.dirty_screen(true)
    return false, "DEFERRED"
  end
  return decision.value, decision.code
end

local function load_project(pth, allow_missing)
  if type(pth) ~= "string" or not pth:match("%.ptn$") then return false end
  local file, _, code = io.open(pth, "r")
  if not file then
    if allow_missing and code == 2 then return false end
    return reject_project("Cannot read project")
  end
  file:close()
  local decoded, saved = pcall(tab.load, pth)
  if not decoded then return reject_project("Invalid project data") end
  local valid, reason = project_validation.check(saved)
  if not valid then return reject_project(reason) end

  -- Validate first: rejection must not cancel a live capture or transport.
  return after_capture_release(function()
    m_clock:stop()
    print("Loading project " .. pth)
    program.init()
    program.set(saved[2])
    clock.tempo_change_handler = function(x)
      song_edit_page_ui.refresh_tempo()
    end
    param_manager.init()
    for i = 1, 16 do
      param_manager.add_device_params(
        i,
        device_map.get_device(program.get().devices[i].device_map),
        program.get().devices[i].midi_channel,
        program.get().devices[i].midi_device,
        false
      )
    end
    if saved[1] then params:read(norns.state.data .. saved[1] .. ".pset", true) end
    m_clock:reset()
    ui.refresh()
    if capture_guard and capture_guard.project_loaded then capture_guard:project_loaded(pth) end
    if capture_guard and capture_guard.restore_project then
      local restored = capture_guard:restore_project(program.get(), pth)
      if not restored or restored.ok ~= true then return reject_project("Invalid Rhythm Doctor bank") end
    end
    fn.dirty_grid(true)
    resume_autosave()
    return true
  end)
end

-- The norns serializers ignore some write/close return values. Observe those
-- synchronous calls without replacing their formats, and restore IO on errors.
local function checked_table_save(saved, path)
  local original_open = io.open
  local opened, closed
  io.open = function(filename, mode)
    local file, err, code = original_open(filename, mode)
    if not file or filename ~= path then return file, err, code end
    opened = file
    local proxy = {}
    function proxy:write(...)
      local result, problem = file:write(...)
      if not result then error(problem or "project write failed") end
      return self
    end
    function proxy:close()
      closed = true
      local result, problem = file:close()
      if not result then error(problem or "project close failed") end
      return result
    end
    return proxy
  end
  local ok, problem = pcall(tab.save, saved, path)
  io.open = original_open
  if opened and not closed then pcall(opened.close, opened) end
  if not ok or problem then return false, problem end
  return true
end

local function save_project(txt, automatic)
  if not txt then return false end
  -- The guard owns coalescing and resource-release timing. Ask before stop/reset
  -- or serialization: ordinary project saves also silence n.b. voices.
  if capture_guard then
    local decision = automatic and capture_guard:autosave() or capture_guard:manual_save()
    if decision.code ~= "SAVE_NOW" then
      if not automatic then
        tooltip:show("CAPTURE ACTIVE / FINISH OR CANCEL")
        fn.dirty_screen(true)
      end
      return false
    end
  end
  m_clock:stop()
  m_clock:reset()
  print("Saving project as " .. txt)
  local project_data = program.prepare_for_save()
  local project_path = norns.state.data .. txt .. ".ptn"
  if capture_guard and capture_guard.serialize_project then
    local serialized = capture_guard:serialize_project(project_data, project_path)
    if not serialized or serialized.ok ~= true then
      tooltip:show("Rhythm Doctor save failed")
      fn.dirty_screen(true)
      return false
    end
  end
  local ok, err = checked_table_save({txt, project_data}, project_path)
  -- ParamSet:write returns nil even when opening the file fails. Its write
  -- callback is reached after attempting the write. Check IO return values as
  -- well, so silent write/close failures cannot release autosave inhibition.
  local previous_write = params.action_write
  local pset_written = false
  if ok then
    params.action_write = function(...)
      pset_written = true
      if previous_write then previous_write(...) end
    end
    local original_write, original_close = io.write, io.close
    local function checked(call)
      return function(...)
        local values = table.pack(call(...))
        if not values[1] then error(values[2] or "parameter file IO failed") end
        return table.unpack(values, 1, values.n)
      end
    end
    io.write, io.close = checked(original_write), checked(original_close)
    ok, err = pcall(function() params:write(norns.state.data .. txt .. ".pset") end)
    io.write, io.close = original_write, original_close
    params.action_write = previous_write
  end
  if not ok or not pset_written then
    print("Save failed: " .. tostring(err or "parameter file not written"))
    tooltip:show("Save failed")
    fn.dirty_screen(true)
    return false
  end
  if not automatic then resume_autosave() end
  return true
end

local function load_new_project()
  return after_capture_release(function()
    program.init()
    memory.init() -- bind memory to the new project; the old history must not carry over
    for i = 1, 16 do
      param_manager.add_device_params(
        i,
        device_map.get_device(program.get().devices[i].device_map),
        program.get().devices[i].midi_channel,
        program.get().devices[i].midi_device,
        true
      )
    end
    m_grid.refresh()
    ui.refresh()
    new_project_sequence = new_project_sequence + 1
    if capture_guard and capture_guard.project_loaded then capture_guard:project_loaded("new:" .. tostring(new_project_sequence)) end
    resume_autosave()
    return true
  end)
end

local function do_autosave()
  if autosave_inhibited then return end
  -- Saving stops and resets the transport. The save is primed only while
  -- stopped, but runs half a second later; playback started in between must
  -- keep playing, so leave the project unsaved and prime again later.
  if m_clock.is_playing() then
    as_metro:stop()
    autosave_reset()
    return
  end
  set_splash(true)
  local saved = program ~= nil and save_project("autosave", true)
  set_splash(false)
  if saved then tooltip:show("Autosaved") end
  fn.dirty_screen(true)
  as_metro:stop()
  autosave_timer:stop()
end

local function prime_autosave()
  if autosave_inhibited then return end
  if as_metro.id then
    metro.free(as_metro.id)
  end
  if not m_clock.is_playing() then
    as_metro = metro.init(do_autosave, 0.5, 1)
    as_metro:start()
  else
    autosave_reset()
  end
end

autosave_reset = function()
  if autosave_inhibited then return end
  if autosave_timer.id then
    metro.free(autosave_timer.id)
  end
  autosave_timer = metro.init(prime_autosave, 60, 1)
  autosave_timer:start()
end

  return {
    load = load_project,
    save = save_project,
    new = load_new_project,
    reset_autosave = autosave_reset,
    prime_autosave = prime_autosave,
    autosave = do_autosave,
    set_capture_guard = function(guard)
      capture_guard = guard
    end
  }
end

return project_lifecycle
