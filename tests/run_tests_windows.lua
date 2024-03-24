-- require('luacov')

-- Windows compatible function to check if the directory exists with extracted files
function directory_and_files_exist(path, sample_file_name)
  local check_command = string.format('powershell -Command "(Get-ChildItem -Path \'%s\' -Recurse -Filter \'%s\' -ErrorAction SilentlyContinue).FullName"', path, sample_file_name)
  local handle = io.popen(check_command)
  local result = handle:read("*a")
  handle:close()
  return result and result ~= ""
end



local expected_file_name = "norns.lua"

if directory_and_files_exist(".\\test_artefacts\\norns_test_artefact\\lua\\core", expected_file_name) then
  print("The '.\\test_artefacts\\norns_test_artefact\\lua\\core\\norns.lua' file already exists. Skipping download.")
else
  

  -- Ensure the test_artefacts directory exists
  os.execute("if not exist .\\test_artefacts mkdir .\\test_artefacts")

  if directory_and_files_exist(".\\test_artefacts\\", "norns_latest.zip") then
    print("The '.\\test_artefacts\\norns_test_artefact\\norns_latest.zip' file already exists. Skipping download.")
  else
    print("Fetching latest release of norns...")
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
    end
  end

  -- Step 1: Extract the archive to a temporary directory
  local extract_command = "powershell -Command \"Expand-Archive -Path .\\test_artefacts\\norns_latest.zip -DestinationPath .\\test_artefacts\\temp_norns\""
  os.execute(extract_command)

-- Move with overwrite
  local move_command = [[powershell -Command "$source = (Get-ChildItem -Path .\test_artefacts\temp_norns | Select-Object -First 1).FullName; Move-Item -Path $source\* -Destination .\test_artefacts\norns_test_artefact -Force"]]
  os.execute(move_command)

  -- Remove read-only attributes and then attempt removal
  local prepare_remove_command = [[powershell -Command "Get-ChildItem -Path .\test_artefacts\temp_norns -Recurse | ForEach-Object { $_.Attributes = 'Normal' }"]]
  os.execute(prepare_remove_command)

  local cleanup_command = "powershell -Command \"Remove-Item -Path .\\test_artefacts\\temp_norns -Recurse -Force\""
  os.execute(cleanup_command)


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

