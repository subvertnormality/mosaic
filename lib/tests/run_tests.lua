-- require('luacov')

-- Function to check if the norns directory exists with extracted files
function directory_and_files_exist(path, sample_file_name)
  local check_command = string.format('find "%s" -type f -name "%s"', path, sample_file_name)
  local handle = io.popen(check_command)
  local result = handle:read("*a")
  handle:close()
  return result ~= ""
end

local expected_file_name = "norns.lua"  

local my_path = "./test_artefacts/norns_test_artefact/lua/lib/?.lua;" 

if directory_and_files_exist("/home/we/norns/lua/core", expected_file_name) then
  print("Running these tests directly on norns can cause issues. Skipping.")
  return
end

if directory_and_files_exist("./test_artefacts/norns_test_artefact/lua/core", expected_file_name) then
  print("The './test_artefacts/norns_test_artefact/lua/core/norns.lua' file already exists. Skipping download.")
else
  print("Fetching latest release of norns...")

  -- Ensure the test_artefacts directory exists
  os.execute("mkdir -p ./test_artefacts")

  -- This calls the GitHub API unauthenticated, so it shares a 60-per-hour
  -- budget with every other runner on the same address, and returns something
  -- that is not a release when the service is degraded. A single attempt makes
  -- the whole suite fail before it runs a test, so retry before giving up.
  local download_url, last_response = nil, ""
  for attempt = 1, 5 do
    os.execute("curl -sS --fail --connect-timeout 10 --max-time 120 " ..
      "https://api.github.com/repos/monome/norns/releases/latest " ..
      "> ./test_artefacts/latest_release.json 2>/dev/null")
    local file = io.open("./test_artefacts/latest_release.json", "r")
    local content = ""
    if file then content = file:read("*all") or ""; file:close() end
    download_url = content:match('"zipball_url":%s*"([^"]+)"')
    if download_url then break end
    last_response = content:gsub("%s+", " "):sub(1, 300)
    if attempt < 5 then
      print(string.format("norns release lookup attempt %d failed; retrying", attempt))
      os.execute("sleep " .. tostring(attempt * 3))
    end
  end

  if download_url then
      -- Download the latest release zip file into test_artefacts
      os.execute(string.format("curl -L '%s' -o ./test_artefacts/norns_latest.zip", download_url))

      -- Extract the zip file into a temporary directory within test_artefacts
      os.execute("unzip ./test_artefacts/norns_latest.zip -d ./test_artefacts/temp_norns")

      -- Determine the name of the top-level directory
      local top_level_dir_command = "ls ./test_artefacts/temp_norns | head -n 1"
      local handle = io.popen(top_level_dir_command)
      local top_level_dir = handle:read("*a"):gsub("\n", "")
      handle:close()

      -- Move the contents from the top-level directory to the desired location and clean up
      if top_level_dir ~= "" then
        os.execute("mkdir -p ./test_artefacts/norns_test_artefact")
          os.execute(string.format("mv ./test_artefacts/temp_norns/%s/* ./test_artefacts/norns_test_artefact", top_level_dir))
          os.execute("rm -rf ./test_artefacts/temp_norns")
          print("norns has been successfully downloaded and extracted to './test_artefacts/norns_test_artefact'.")
      else
          print("Failed to identify the top-level directory within the zip archive.")
      end
  else
      -- Carrying on here leaves the artefact missing, and the suite then fails
      -- with "module 'util' not found", which says nothing about the cause.
      print("Failed to extract the download URL from the JSON response after 5 attempts.")
      print("Last response was: " .. last_response)
      os.exit(1)
  end
end

package.path = my_path .. package.path

util = require('util')
luaunit = require('test.luaunit')

-- global include function
function include(file)
  local dirs = {'../../../', './test_artefacts/norns_test_artefact/lua/extn/'}
  for _, dir in ipairs(dirs) do
    local p = dir..file..'.lua'
    if util.file_exists(p) then
      return dofile(p)
    end
  end

  -- didn't find anything
  print("### MISSING INCLUDE: "..file)
  error("MISSING INCLUDE: "..file,2)
end

function require_all_files_in_folder(folder)
  local command = string.format('ls %s/*.lua', folder)
  local handle = io.popen(command)
  local result = handle:read("*a")
  handle:close()

  -- Iterate through each line in the result
  for filename in string.gmatch(result, '[^\r\n]+') do
      -- Remove the directory path and extension from the filename to get the module name
      local module = filename:match("^.+/(.+).lua$")
      if module then
          local module_path = folder .. '.' .. module
          require(module_path:gsub('/', '.'))
      end
  end
end

function clear_require_cache(modules)
  if modules then
      for _, module_name in ipairs(modules) do
          package.loaded[module_name] = nil
      end
  else
      for module_name in pairs(package.loaded) do
          package.loaded[module_name] = nil
      end
  end
end

clear_require_cache()

fn = include("mosaic/lib/helpers/functions")
pages = include("mosaic/lib/pages/pages")
scheduler = include("mosaic/lib/tests/helpers/mocks/scheduler_mock")
program = include("mosaic/lib/models/program")
memory = include("mosaic/lib/memory")
include("mosaic/lib/tests/helpers/globals")

require_all_files_in_folder('./lib')
require_all_files_in_folder('./lib/integration_tests')

os.exit( luaunit.LuaUnit.run() )