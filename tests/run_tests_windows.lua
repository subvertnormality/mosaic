-- require('luacov')

-- Windows compatible function to check if the directory exists with extracted files
function directory_and_files_exist(path, sample_file_name)
  local check_command = string.format('powershell -Command "Get-ChildItem -Path \'%s\' -Recurse -Filter \'%s\'"', path, sample_file_name)
  local handle = io.popen(check_command)
  local result = handle:read("*a")
  handle:close()
  return result ~= ""
end

local expected_file_name = "norns.lua"

if directory_and_files_exist(".\\test_artefacts\\norns_test_artefact\\lua\\core", expected_file_name) then
  print("The '.\\test_artefacts\\norns_test_artefact\\lua\\core\\norns.lua' file already exists. Skipping download.")
else
  print("Fetching latest release of norns...")

  -- Ensure the test_artefacts directory exists
  os.execute("if not exist .\\test_artefacts mkdir .\\test_artefacts")

  -- Fetch the latest release data from GitHub and save it to a file within test_artefacts
  os.execute("powershell -Command \"Invoke-WebRequest -Uri https://api.github.com/repos/monome/norns/releases/latest -OutFile .\\test_artefacts\\latest_release.json\"")

  -- Read the file and extract the download URL
  local file = io.open(".\\test_artefacts\\latest_release.json", "r")
  local content = file:read("*all")
  file:close()

  -- Attempt to extract the zipball download URL using Lua pattern matching
  local download_url = content:match('"zipball_url":%s*"([^"]+)"')

  if download_url then
    -- Download the latest release zip file into test_artefacts
    os.execute(string.format("powershell -Command \"Invoke-WebRequest -Uri '%s' -OutFile .\\test_artefacts\\norns_latest.zip\"", download_url))

    -- Extract the zip file into a temporary directory within test_artefacts
    os.execute("powershell -Command \"Expand-Archive -Path .\\test_artefacts\\norns_latest.zip -DestinationPath .\\test_artefacts\\temp_norns\"")

    -- Determine the name of the top-level directory
    local top_level_dir_command = "powershell -Command \"Get-ChildItem -Path .\\test_artefacts\\temp_norns | Select-Object -First 1 -ExpandProperty Name\""
    local handle = io.popen(top_level_dir_command)
    local top_level_dir = handle:read("*a"):gsub("\r\n", "")
    handle:close()

    -- Move the contents from the top-level directory to the desired location and clean up
    if top_level_dir ~= "" then
      os.execute("if not exist .\\test_artefacts\\norns mkdir .\\test_artefacts\\norns")
      os.execute(string.format("powershell -Command \"Move-Item -Path .\\test_artefacts\\temp_norns\\%s\\* -Destination .\\test_artefacts\\norns_test_artefact\"", top_level_dir))
      os.execute("powershell -Command \"Remove-Item -Path .\\test_artefacts\\temp_norns -Recurse\"")
      print("norns has been successfully downloaded and extracted to '.\\test_artefacts\\norns_test_artefact'.")
    else
      print("Failed to identify the top-level directory within the zip archive.")
    end
  else
    print("Failed to extract the download URL from the JSON response.")
  end
end

local my_path = ".\\test_artefacts\\norns_test_artefact\\lua\\lib\\?.lua;"
package.path = my_path .. package.path

util = require('util')
luaunit = require('test.luaunit')

-- global include function
function include(file)
  local dirs = {'..\\..\\', '.\\test_artefacts\\norns_test_artefact\\lua\\extn\\'}
  for _, dir in ipairs(dirs) do
    local p = dir..file..'.lua'
    if util.file_exists(p) then
      -- print("including "..p)
      return dofile(p)
    end
  end

  -- didn't find anything
  print("### MISSING INCLUDE: "..file)
  error("MISSING INCLUDE: "..file,2)
end

function require_all_files_in_folder(folder)
  -- Adapted for Windows: Use PowerShell to list all Lua files in the folder
  local command = string.format('powershell -Command "Get-ChildItem -Path \'%s\' -Filter \'*.lua\' | ForEach-Object { echo $_.Name }"', folder)
  local handle = io.popen(command)
  local result = handle:read("*a")
  handle:close()

  -- Iterate through each line in the result to require the Lua files
  for filename in string.gmatch(result, '[^\r\n]+') do
      -- Adapt for Windows: Extract the module name from the filename
      local module = filename:match("^(.+).lua$")
      if module then
          local module_path = folder .. '\\' .. module
          require(module_path:gsub('\\', '.'))
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

fn = include("mosaic\\lib\\functions")
program = include("mosaic\\lib\\program")

include("mosaic\\tests\\helpers\\globals")

require_all_files_in_folder('.\\lib')
require_all_files_in_folder('.\\lib\\integration_tests')

os.exit(luaunit.LuaUnit.run())

