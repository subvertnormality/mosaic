-- Project lifecycle bridge check, characterisation outside README.

-- Harmony and Musical Merge resolve their transient state at load, and this
-- case is about the capture bridge rather than either of them, so they are
-- supplied as modules that reset to nothing.
local harmony_modules = {
  ['mosaic/lib/musical_merge/state'] = true,
  ['mosaic/lib/harmony/config_state'] = true,
  ['mosaic/lib/harmony/state'] = true,
  ['mosaic/lib/harmony/inspection'] = true,
}
local resets = {}
include = function(path)
  assert(harmony_modules[path], 'unexpected include: ' .. tostring(path))
  return { reset = function() resets[path] = (resets[path] or 0) + 1 end }
end
local lifecycle = dofile('lib/project_lifecycle.lua')
include = nil

local failures, count = {}, 0
local function test(name, body)
  count = count + 1
  local ok, err = pcall(body)
  if not ok then failures[#failures + 1] = name .. ': ' .. tostring(err) end
end
local function equal(actual, expected, message)
  assert(actual == expected, (message or 'values differ') .. ': expected ' .. tostring(expected) .. ', got ' .. tostring(actual))
end

local function timer() return { id = nil, stop = function() end, start = function() end } end

test('new project notifies capture runtime after program replacement', function()
  local trace, loaded = {}, {}
  metro = { free = function() end, init = function() return timer() end }
  tooltip = { show = function() end }
  fn = { dirty_screen = function() end, dirty_grid = function() end }
  m_clock = { is_playing = function() return false end, stop = function() end, reset = function() end }
  memory = { init = function() trace[#trace + 1] = 'memory' end }
  local devices = {}
  for i = 1, 16 do devices[i] = { device_map = 'none', midi_channel = 1, midi_device = 1 } end
  program = { init = function() trace[#trace + 1] = 'program' end, get = function() return { devices = devices } end }
  device_map = { get_device = function() return {} end }
  param_manager = { add_device_params = function() end }
  m_grid, ui = { refresh = function() end }, { refresh = function() end }
  local guard = {
    prepare_project_change = function(self, continuation) trace[#trace + 1] = 'prepare'; return { code = 'OK', value = continuation() } end,
    project_loaded = function(self, identity) trace[#trace + 1] = 'loaded'; loaded[#loaded + 1] = identity end,
  }
  local project = lifecycle.new(timer(), timer(), param_manager, { check = function() return true end }, function() end, guard)
  equal(project.new(), true)
  equal(table.concat(trace, ','), 'prepare,program,memory,loaded')
  equal(loaded[1], 'new:1')
end)

if #failures > 0 then io.stderr:write(table.concat(failures, '\n') .. '\n'); os.exit(1) end
print('rhythm_doctor project lifecycle runtime: ' .. count .. ' tests passed')
